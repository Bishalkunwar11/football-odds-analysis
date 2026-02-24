"""Database manager for storing and retrieving football odds (SQLite)."""

import logging
import sqlite3
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# Default database path
DEFAULT_DB_PATH = "data/football_odds.db"


class DBManager:
    """Manages all SQLite operations for the football odds analysis system."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH) -> None:
        """Initialise the manager and create tables if needed.

        Args:
            db_path: Path to the SQLite database file.
                     Use ``":memory:"`` for in-memory databases.
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.init_db()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def init_db(self) -> None:
        """Create database tables if they do not already exist."""
        cursor = self.conn.cursor()
        cursor.executescript(
            """
            CREATE TABLE IF NOT EXISTS matches (
                match_id     TEXT PRIMARY KEY,
                sport_key    TEXT NOT NULL,
                league       TEXT NOT NULL,
                home_team    TEXT NOT NULL,
                away_team    TEXT NOT NULL,
                commence_time TEXT NOT NULL,
                created_at   TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS odds (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id      TEXT NOT NULL,
                bookmaker     TEXT NOT NULL,
                market        TEXT NOT NULL,
                outcome_name  TEXT NOT NULL,
                outcome_price REAL NOT NULL,
                point         REAL,
                timestamp     TEXT NOT NULL,
                FOREIGN KEY (match_id) REFERENCES matches(match_id)
            );
            """
        )
        self.conn.commit()
        logger.debug("Database initialised at %s", self.db_path)

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def store_odds(self, matches_data: list[dict[str, Any]]) -> None:
        """Upsert matches and insert odds rows with timestamps.

        Args:
            matches_data: List of flat odds rows as returned by
                          :meth:`OddsAPIClient._parse_response`.
        """
        if not matches_data:
            logger.warning("store_odds called with empty data.")
            return

        now = datetime.now(timezone.utc).isoformat()
        cursor = self.conn.cursor()

        for row in matches_data:
            # Upsert the match record
            cursor.execute(
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
                (
                    row["match_id"],
                    row["sport_key"],
                    row["league"],
                    row["home_team"],
                    row["away_team"],
                    row["commence_time"],
                    now,
                ),
            )

            # Insert odds snapshot
            cursor.execute(
                """
                INSERT INTO odds
                    (match_id, bookmaker, market, outcome_name,
                     outcome_price, point, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["match_id"],
                    row["bookmaker"],
                    row["market"],
                    row["outcome_name"],
                    row["outcome_price"],
                    row.get("point"),
                    now,
                ),
            )

        self.conn.commit()
        logger.info("Stored %d odds rows.", len(matches_data))

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_latest_odds(
        self, sport_key: str | None = None
    ) -> list[dict[str, Any]]:
        """Return the most recent odds for each match/bookmaker/market/outcome.

        Args:
            sport_key: Optional filter by sport key.

        Returns:
            List of row dicts.
        """
        query = """
            SELECT m.match_id, m.sport_key, m.league,
                   m.home_team, m.away_team, m.commence_time,
                   o.bookmaker, o.market, o.outcome_name,
                   o.outcome_price, o.point, o.timestamp
            FROM odds o
            JOIN matches m ON o.match_id = m.match_id
            WHERE o.id IN (
                SELECT MAX(id)
                FROM odds
                GROUP BY match_id, bookmaker, market, outcome_name
            )
        """
        params: tuple = ()
        if sport_key:
            query += " AND m.sport_key = ?"
            params = (sport_key,)

        query += " ORDER BY m.commence_time, m.match_id, o.bookmaker"

        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return [dict(r) for r in cursor.fetchall()]

    def get_odds_history(
        self, match_id: str, bookmaker: str | None = None
    ) -> list[dict[str, Any]]:
        """Return historical odds for a match (all snapshots).

        Args:
            match_id: The unique match identifier.
            bookmaker: Optional filter by bookmaker name.

        Returns:
            List of row dicts ordered by timestamp.
        """
        query = """
            SELECT o.id, o.match_id, o.bookmaker, o.market,
                   o.outcome_name, o.outcome_price, o.point, o.timestamp
            FROM odds o
            WHERE o.match_id = ?
        """
        params: list[Any] = [match_id]
        if bookmaker:
            query += " AND o.bookmaker = ?"
            params.append(bookmaker)

        query += " ORDER BY o.timestamp"

        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return [dict(r) for r in cursor.fetchall()]

    def get_upcoming_matches(
        self, sport_key: str | None = None
    ) -> list[dict[str, Any]]:
        """Return all upcoming matches (commence_time in the future).

        Args:
            sport_key: Optional filter by sport key.

        Returns:
            List of match row dicts.
        """
        now = datetime.now(timezone.utc).isoformat()
        query = "SELECT * FROM matches WHERE commence_time >= ?"
        params: list[Any] = [now]
        if sport_key:
            query += " AND sport_key = ?"
            params.append(sport_key)

        query += " ORDER BY commence_time"

        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return [dict(r) for r in cursor.fetchall()]

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the underlying database connection."""
        self.conn.close()
