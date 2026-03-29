"""Database manager for storing and retrieving football odds (SQLite)."""

import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = str(
    Path(__file__).resolve().parent.parent / "data" / "football_odds.db"
)

# Bump this when adding new tables or columns.
SCHEMA_VERSION = 2


class DBManager:
    """Manages all SQLite operations for the football odds analysis system."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH) -> None:
        """Initialise the manager, create tables, and run any pending migrations.

        Args:
            db_path: Path to the SQLite database file.
                     Use ``":memory:"`` for in-memory databases.
        """
        self.db_path = db_path
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.init_db()
        self.migrate()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def init_db(self) -> None:
        """Create all tables and indexes if they do not already exist."""
        cursor = self.conn.cursor()
        cursor.executescript(
            """
            -- Version tracking
            CREATE TABLE IF NOT EXISTS schema_version (
                version  INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL
            );

            -- Core tables (v1)
            CREATE TABLE IF NOT EXISTS matches (
                match_id      TEXT PRIMARY KEY,
                sport_key     TEXT NOT NULL,
                league        TEXT NOT NULL,
                home_team     TEXT NOT NULL,
                away_team     TEXT NOT NULL,
                commence_time TEXT NOT NULL,
                created_at    TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS odds (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id       TEXT NOT NULL,
                bookmaker      TEXT NOT NULL,
                market         TEXT NOT NULL,
                outcome_name   TEXT NOT NULL,
                outcome_price  REAL NOT NULL,
                point          REAL,
                timestamp      TEXT NOT NULL,
                FOREIGN KEY (match_id) REFERENCES matches(match_id)
            );

            CREATE TABLE IF NOT EXISTS feedback (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                category     TEXT NOT NULL,
                rating       INTEGER NOT NULL,
                message      TEXT NOT NULL,
                submitted_at TEXT NOT NULL
            );

            -- New tables (v2)
            CREATE TABLE IF NOT EXISTS alerts (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_type   TEXT NOT NULL,
                match_id     TEXT,
                title        TEXT NOT NULL,
                detail       TEXT NOT NULL,
                value        REAL,
                is_read      INTEGER NOT NULL DEFAULT 0,
                created_at   TEXT NOT NULL,
                FOREIGN KEY (match_id) REFERENCES matches(match_id)
            );

            CREATE TABLE IF NOT EXISTS user_bets (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                match_label    TEXT NOT NULL,
                outcome        TEXT NOT NULL,
                bookmaker      TEXT,
                decimal_odds   REAL NOT NULL,
                stake          REAL NOT NULL,
                result         TEXT,
                pnl            REAL,
                settled_at     TEXT,
                placed_at      TEXT NOT NULL,
                notes          TEXT
            );

            -- Indexes
            CREATE INDEX IF NOT EXISTS idx_matches_sport_key
                ON matches(sport_key);
            CREATE INDEX IF NOT EXISTS idx_matches_commence_time
                ON matches(commence_time);
            CREATE INDEX IF NOT EXISTS idx_odds_lookup
                ON odds(match_id, bookmaker, market, outcome_name);
            CREATE INDEX IF NOT EXISTS idx_odds_timestamp
                ON odds(timestamp);
            CREATE INDEX IF NOT EXISTS idx_feedback_submitted_at
                ON feedback(submitted_at);
            CREATE INDEX IF NOT EXISTS idx_alerts_is_read
                ON alerts(is_read, created_at);
            CREATE INDEX IF NOT EXISTS idx_user_bets_placed_at
                ON user_bets(placed_at);
            """
        )
        self.conn.commit()
        logger.debug("Database initialised at %s", self.db_path)

    def migrate(self) -> None:
        """Apply any pending schema migrations in order.

        Each migration is idempotent — safe to run multiple times.
        The current schema version is tracked in the ``schema_version`` table.
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT MAX(version) FROM schema_version")
        row = cursor.fetchone()
        current = row[0] if row[0] is not None else 0

        if current < 2:
            self._migrate_v2(cursor)

        self.conn.commit()

    def _migrate_v2(self, cursor: sqlite3.Cursor) -> None:
        """v2: Add price_direction and previous_price columns to odds table."""
        # Add columns if they don't exist (ALTER TABLE IF NOT EXISTS col not supported in old SQLite)
        existing = {r[1] for r in cursor.execute("PRAGMA table_info(odds)")}
        if "previous_price" not in existing:
            cursor.execute("ALTER TABLE odds ADD COLUMN previous_price REAL")
        if "price_direction" not in existing:
            cursor.execute(
                "ALTER TABLE odds ADD COLUMN price_direction TEXT "
                "CHECK(price_direction IN ('up','down','stable'))"
            )

        now = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            "INSERT OR IGNORE INTO schema_version (version, applied_at) VALUES (2, ?)",
            (now,),
        )
        logger.info("DB migration v2 applied: price_direction columns added.")

    # ------------------------------------------------------------------
    # Write — Odds
    # ------------------------------------------------------------------

    def store_odds(self, matches_data: list[dict[str, Any]]) -> None:
        """Upsert matches and insert odds rows with price direction tracking.

        Computes ``previous_price`` and ``price_direction`` by looking up the
        most recent stored price for each (match_id, bookmaker, market, outcome)
        before inserting the new snapshot.

        Args:
            matches_data: List of flat odds rows as returned by
                          :meth:`OddsAPIClient._parse_response`.
        """
        if not matches_data:
            logger.warning("store_odds called with empty data.")
            return

        now = datetime.now(timezone.utc).isoformat()
        cursor = self.conn.cursor()

        # Batch upsert matches
        seen_match_ids: set[str] = set()
        match_params = []
        for row in matches_data:
            mid = row["match_id"]
            if mid not in seen_match_ids:
                seen_match_ids.add(mid)
                match_params.append((
                    mid,
                    row["sport_key"],
                    row["league"],
                    row["home_team"],
                    row["away_team"],
                    row["commence_time"],
                    now,
                ))
        cursor.executemany(
            """
            INSERT INTO matches
                (match_id, sport_key, league, home_team, away_team,
                 commence_time, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(match_id) DO UPDATE SET
                league        = excluded.league,
                home_team     = excluded.home_team,
                away_team     = excluded.away_team,
                commence_time = excluded.commence_time
            """,
            match_params,
        )

        # Build previous-price lookup for direction computation
        prev_price_map: dict[tuple[str, str, str, str], float] = {}
        if seen_match_ids:
            placeholders = ",".join("?" * len(seen_match_ids))
            cursor.execute(
                f"""
                WITH latest AS (
                    SELECT match_id, bookmaker, market, outcome_name, outcome_price,
                           ROW_NUMBER() OVER (
                               PARTITION BY match_id, bookmaker, market, outcome_name
                               ORDER BY id DESC
                           ) AS rn
                    FROM odds
                    WHERE match_id IN ({placeholders})
                )
                SELECT match_id, bookmaker, market, outcome_name, outcome_price
                FROM latest WHERE rn = 1
                """,
                tuple(seen_match_ids),
            )
            for r in cursor.fetchall():
                key = (r["match_id"], r["bookmaker"], r["market"], r["outcome_name"])
                prev_price_map[key] = float(r["outcome_price"])

        # Insert odds with price direction
        odds_params = []
        for row in matches_data:
            key = (row["match_id"], row["bookmaker"], row["market"], row["outcome_name"])
            new_price = float(row["outcome_price"])
            prev = prev_price_map.get(key)

            if prev is None:
                direction = "stable"
            elif new_price > prev:
                direction = "up"
            elif new_price < prev:
                direction = "down"
            else:
                direction = "stable"

            odds_params.append((
                row["match_id"],
                row["bookmaker"],
                row["market"],
                row["outcome_name"],
                new_price,
                row.get("point"),
                now,
                prev,
                direction,
            ))

        cursor.executemany(
            """
            INSERT INTO odds
                (match_id, bookmaker, market, outcome_name,
                 outcome_price, point, timestamp, previous_price, price_direction)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            odds_params,
        )

        self.conn.commit()
        logger.info("Stored %d odds rows.", len(matches_data))

    # ------------------------------------------------------------------
    # Read — Odds
    # ------------------------------------------------------------------

    def get_latest_odds(
        self,
        sport_key: str | None = None,
        sport_keys: tuple[str, ...] | None = None,
    ) -> list[dict[str, Any]]:
        """Return the most recent odds for each match/bookmaker/market/outcome.

        Args:
            sport_key:  Optional filter by a single sport key.
            sport_keys: Optional filter by multiple sport keys.

        Returns:
            List of row dicts including ``price_direction`` and ``previous_price``.
        """
        query = """
            WITH latest AS (
                SELECT *,
                       ROW_NUMBER() OVER (
                           PARTITION BY match_id, bookmaker, market, outcome_name
                           ORDER BY id DESC
                       ) AS rn
                FROM odds
            )
            SELECT m.match_id, m.sport_key, m.league,
                   m.home_team, m.away_team, m.commence_time,
                   o.bookmaker, o.market, o.outcome_name,
                   o.outcome_price, o.point, o.timestamp,
                   o.previous_price, o.price_direction
            FROM latest o
            JOIN matches m ON o.match_id = m.match_id
            WHERE o.rn = 1
        """
        params: tuple = ()
        if sport_keys and len(sport_keys) > 1:
            placeholders = ",".join("?" * len(sport_keys))
            query += f" AND m.sport_key IN ({placeholders})"
            params = sport_keys
        elif sport_keys and len(sport_keys) == 1:
            query += " AND m.sport_key = ?"
            params = (sport_keys[0],)
        elif sport_key:
            query += " AND m.sport_key = ?"
            params = (sport_key,)

        query += " ORDER BY m.commence_time, m.match_id, o.bookmaker"
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return [dict(r) for r in cursor.fetchall()]

    def get_odds_history(
        self, match_id: str, bookmaker: str | None = None
    ) -> list[dict[str, Any]]:
        """Return all historical odds snapshots for a match.

        Args:
            match_id:   The unique match identifier.
            bookmaker:  Optional filter by bookmaker name.

        Returns:
            List of row dicts ordered by timestamp.
        """
        query = """
            SELECT id, match_id, bookmaker, market, outcome_name,
                   outcome_price, previous_price, price_direction, point, timestamp
            FROM odds WHERE match_id = ?
        """
        params: list[Any] = [match_id]
        if bookmaker:
            query += " AND bookmaker = ?"
            params.append(bookmaker)
        query += " ORDER BY timestamp"
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return [dict(r) for r in cursor.fetchall()]

    def get_price_movements(self, match_id: str) -> list[dict[str, Any]]:
        """Return latest price with direction for every outcome of a match.

        Args:
            match_id: The unique match identifier.

        Returns:
            List of dicts with bookmaker, market, outcome_name,
            outcome_price, previous_price, price_direction.
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            WITH latest AS (
                SELECT bookmaker, market, outcome_name,
                       outcome_price, previous_price, price_direction,
                       ROW_NUMBER() OVER (
                           PARTITION BY bookmaker, market, outcome_name
                           ORDER BY id DESC
                       ) AS rn
                FROM odds WHERE match_id = ?
            )
            SELECT bookmaker, market, outcome_name,
                   outcome_price, previous_price, price_direction
            FROM latest WHERE rn = 1
            ORDER BY bookmaker, market, outcome_name
            """,
            (match_id,),
        )
        return [dict(r) for r in cursor.fetchall()]

    def get_upcoming_matches(
        self,
        sport_key: str | None = None,
        sport_keys: tuple[str, ...] | None = None,
    ) -> list[dict[str, Any]]:
        """Return all upcoming matches (commence_time in the future).

        Args:
            sport_key:  Optional filter by a single sport key.
            sport_keys: Optional filter by multiple sport keys.

        Returns:
            List of match row dicts.
        """
        now = datetime.now(timezone.utc).isoformat()
        query = "SELECT * FROM matches WHERE commence_time >= ?"
        params: list[Any] = [now]
        if sport_keys and len(sport_keys) > 1:
            placeholders = ",".join("?" * len(sport_keys))
            query += f" AND sport_key IN ({placeholders})"
            params.extend(sport_keys)
        elif sport_keys and len(sport_keys) == 1:
            query += " AND sport_key = ?"
            params.append(sport_keys[0])
        elif sport_key:
            query += " AND sport_key = ?"
            params.append(sport_key)
        query += " ORDER BY commence_time"
        cursor = self.conn.cursor()
        cursor.execute(query, tuple(params))
        return [dict(r) for r in cursor.fetchall()]

    # ------------------------------------------------------------------
    # Alerts
    # ------------------------------------------------------------------

    def save_alert(
        self,
        alert_type: str,
        title: str,
        detail: str,
        match_id: str | None = None,
        value: float | None = None,
    ) -> int:
        """Insert an alert record.

        Args:
            alert_type: One of ``"value_bet"``, ``"arbitrage"``, ``"price_move"``,
                        ``"sharp_move"``.
            title:      Short headline shown in the alert feed.
            detail:     Longer description text.
            match_id:   Optional related match identifier.
            value:      Optional numeric value (edge %, profit %, price change).

        Returns:
            The auto-incremented id of the inserted row.
        """
        now = datetime.now(timezone.utc).isoformat()
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO alerts (alert_type, match_id, title, detail, value, is_read, created_at)
            VALUES (?, ?, ?, ?, ?, 0, ?)
            """,
            (alert_type, match_id, title, detail, value, now),
        )
        self.conn.commit()
        return cursor.lastrowid  # type: ignore[return-value]

    def get_alerts(
        self,
        alert_type: str | None = None,
        unread_only: bool = False,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Return alerts, newest first.

        Args:
            alert_type:  Optional filter by type.
            unread_only: If True only return alerts with ``is_read = 0``.
            limit:       Maximum rows to return.

        Returns:
            List of alert dicts.
        """
        query = "SELECT * FROM alerts WHERE 1=1"
        params: list[Any] = []
        if alert_type:
            query += " AND alert_type = ?"
            params.append(alert_type)
        if unread_only:
            query += " AND is_read = 0"
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return [dict(r) for r in cursor.fetchall()]

    def get_unread_alert_count(self) -> int:
        """Return number of unread alerts."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM alerts WHERE is_read = 0")
        return cursor.fetchone()[0]

    def mark_alert_read(self, alert_id: int) -> None:
        """Mark a single alert as read."""
        self.conn.execute(
            "UPDATE alerts SET is_read = 1 WHERE id = ?", (alert_id,)
        )
        self.conn.commit()

    def mark_all_alerts_read(self) -> None:
        """Mark all alerts as read."""
        self.conn.execute("UPDATE alerts SET is_read = 1")
        self.conn.commit()

    # ------------------------------------------------------------------
    # User bets (bankroll)
    # ------------------------------------------------------------------

    def add_bet(
        self,
        match_label: str,
        outcome: str,
        decimal_odds: float,
        stake: float,
        bookmaker: str | None = None,
        notes: str | None = None,
    ) -> int:
        """Record a new bet placement.

        Args:
            match_label:  Human-readable match label (e.g. "Arsenal vs Chelsea").
            outcome:      Outcome description (e.g. "Arsenal Win").
            decimal_odds: Decimal odds at time of bet.
            stake:        Amount staked.
            bookmaker:    Optional bookmaker name.
            notes:        Optional free-text notes.

        Returns:
            The auto-incremented id of the inserted row.
        """
        now = datetime.now(timezone.utc).isoformat()
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO user_bets
                (match_label, outcome, bookmaker, decimal_odds, stake,
                 result, pnl, settled_at, placed_at, notes)
            VALUES (?, ?, ?, ?, ?, NULL, NULL, NULL, ?, ?)
            """,
            (match_label, outcome, bookmaker, decimal_odds, stake, now, notes),
        )
        self.conn.commit()
        return cursor.lastrowid  # type: ignore[return-value]

    def settle_bet(self, bet_id: int, result: str) -> float:
        """Settle a bet and compute P&L.

        Args:
            bet_id: The bet row id.
            result: One of ``"W"`` (win), ``"L"`` (loss), ``"V"`` (void).

        Returns:
            The P&L amount.

        Raises:
            ValueError: If bet_id does not exist or result is invalid.
        """
        if result not in ("W", "L", "V"):
            raise ValueError(f"result must be 'W', 'L', or 'V', got {result!r}")

        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT stake, decimal_odds FROM user_bets WHERE id = ?", (bet_id,)
        )
        row = cursor.fetchone()
        if row is None:
            raise ValueError(f"No bet found with id={bet_id}")

        stake, decimal_odds = row["stake"], row["decimal_odds"]
        if result == "W":
            pnl = round(stake * decimal_odds - stake, 2)
        elif result == "L":
            pnl = round(-stake, 2)
        else:
            pnl = 0.0

        now = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            "UPDATE user_bets SET result = ?, pnl = ?, settled_at = ? WHERE id = ?",
            (result, pnl, now, bet_id),
        )
        self.conn.commit()
        return pnl

    def get_bets(
        self, settled_only: bool = False, limit: int = 200
    ) -> list[dict[str, Any]]:
        """Return bets, newest first.

        Args:
            settled_only: If True only return settled bets.
            limit:        Maximum rows to return.

        Returns:
            List of bet dicts.
        """
        query = "SELECT * FROM user_bets"
        params: list[Any] = []
        if settled_only:
            query += " WHERE result IS NOT NULL"
        query += " ORDER BY placed_at DESC LIMIT ?"
        params.append(limit)
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return [dict(r) for r in cursor.fetchall()]

    def get_bankroll_stats(self) -> dict[str, Any]:
        """Compute aggregate bankroll statistics.

        Returns:
            Dict with keys: ``total_bets``, ``settled_bets``, ``wins``,
            ``losses``, ``voids``, ``total_wagered``, ``total_pnl``,
            ``roi_pct``, ``win_rate``.
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT
                COUNT(*)                                   AS total_bets,
                COUNT(CASE WHEN result IS NOT NULL THEN 1 END) AS settled_bets,
                COUNT(CASE WHEN result = 'W' THEN 1 END)  AS wins,
                COUNT(CASE WHEN result = 'L' THEN 1 END)  AS losses,
                COUNT(CASE WHEN result = 'V' THEN 1 END)  AS voids,
                COALESCE(SUM(stake), 0)                    AS total_wagered,
                COALESCE(SUM(CASE WHEN pnl IS NOT NULL THEN pnl ELSE 0 END), 0) AS total_pnl
            FROM user_bets
            """
        )
        row = dict(cursor.fetchone())
        wagered = row["total_wagered"]
        settled = row["settled_bets"]
        wins = row["wins"]
        row["roi_pct"] = round(row["total_pnl"] / wagered * 100, 2) if wagered else 0.0
        row["win_rate"] = round(wins / settled * 100, 1) if settled else 0.0
        return row

    def get_pnl_timeseries(self, days: int = 30) -> list[dict[str, Any]]:
        """Return daily cumulative P&L for the last N days.

        Args:
            days: Number of days to include.

        Returns:
            List of dicts with keys ``date`` and ``cumulative_pnl``.
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT DATE(settled_at) AS date,
                   SUM(pnl)         AS daily_pnl
            FROM user_bets
            WHERE result IS NOT NULL
              AND settled_at >= datetime('now', ? || ' days')
            GROUP BY DATE(settled_at)
            ORDER BY date
            """,
            (f"-{days}",),
        )
        rows = [dict(r) for r in cursor.fetchall()]

        # Build cumulative series
        cumulative = 0.0
        result = []
        for row in rows:
            cumulative += row["daily_pnl"] or 0.0
            result.append({"date": row["date"], "cumulative_pnl": round(cumulative, 2)})
        return result

    # ------------------------------------------------------------------
    # Feedback
    # ------------------------------------------------------------------

    def save_feedback(self, category: str, rating: int, message: str) -> int:
        """Insert a user feedback record and return the new row id."""
        if rating < 1 or rating > 5:
            raise ValueError(f"rating must be between 1 and 5, got {rating}")
        submitted_at = datetime.now(timezone.utc).isoformat()
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO feedback (category, rating, message, submitted_at) VALUES (?, ?, ?, ?)",
            (category, rating, message, submitted_at),
        )
        self.conn.commit()
        row_id = cursor.lastrowid
        logger.info("Feedback saved (id=%s, category=%s)", row_id, category)
        return row_id  # type: ignore[return-value]

    def get_feedback(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return the most recent feedback entries, newest first."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id, category, rating, message, submitted_at FROM feedback "
            "ORDER BY submitted_at DESC LIMIT ?",
            (limit,),
        )
        return [dict(r) for r in cursor.fetchall()]

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def prune_old_odds(self, keep_latest_n: int = 3, before_days: int = 30) -> int:
        """Delete stale odds rows to keep the database compact.

        Keeps the ``keep_latest_n`` most recent snapshots per
        (match_id, bookmaker, market, outcome_name) partition for rows
        older than ``before_days`` days.

        Args:
            keep_latest_n: Snapshots per partition to retain.
            before_days:   Age threshold in days.

        Returns:
            Number of rows deleted.
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            DELETE FROM odds
            WHERE id NOT IN (
                SELECT id FROM (
                    SELECT id,
                           ROW_NUMBER() OVER (
                               PARTITION BY match_id, bookmaker, market, outcome_name
                               ORDER BY id DESC
                           ) AS rn
                    FROM odds
                ) ranked
                WHERE rn <= ?
            )
            AND timestamp < datetime('now', ? || ' days')
            """,
            (keep_latest_n, f"-{before_days}"),
        )
        deleted = cursor.rowcount
        self.conn.commit()
        logger.info("prune_old_odds: deleted %d rows.", deleted)
        return deleted

    def close(self) -> None:
        """Close the underlying database connection."""
        self.conn.close()
