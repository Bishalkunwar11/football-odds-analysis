"""Unit tests for DBManager using an in-memory SQLite database."""

import pytest

from src.db_manager import DBManager


SAMPLE_ROWS = [
    {
        "match_id": "m001",
        "sport_key": "soccer_epl",
        "league": "English Premier League",
        "home_team": "Arsenal",
        "away_team": "Chelsea",
        "commence_time": "2030-01-10T15:00:00Z",
        "bookmaker": "Pinnacle",
        "market": "h2h",
        "outcome_name": "Arsenal",
        "outcome_price": 2.10,
        "point": None,
    },
    {
        "match_id": "m001",
        "sport_key": "soccer_epl",
        "league": "English Premier League",
        "home_team": "Arsenal",
        "away_team": "Chelsea",
        "commence_time": "2030-01-10T15:00:00Z",
        "bookmaker": "Pinnacle",
        "market": "h2h",
        "outcome_name": "Chelsea",
        "outcome_price": 3.50,
        "point": None,
    },
    {
        "match_id": "m001",
        "sport_key": "soccer_epl",
        "league": "English Premier League",
        "home_team": "Arsenal",
        "away_team": "Chelsea",
        "commence_time": "2030-01-10T15:00:00Z",
        "bookmaker": "Bet365",
        "market": "totals",
        "outcome_name": "Over",
        "outcome_price": 1.90,
        "point": 2.5,
    },
    {
        "match_id": "m002",
        "sport_key": "soccer_spain_la_liga",
        "league": "La Liga",
        "home_team": "Real Madrid",
        "away_team": "Barcelona",
        "commence_time": "2030-01-11T17:00:00Z",
        "bookmaker": "Pinnacle",
        "market": "h2h",
        "outcome_name": "Real Madrid",
        "outcome_price": 2.30,
        "point": None,
    },
]


@pytest.fixture()
def db() -> DBManager:
    """Return an in-memory DBManager instance."""
    manager = DBManager(db_path=":memory:")
    return manager


class TestInitDb:
    def test_tables_created(self, db: DBManager) -> None:
        cursor = db.conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = {row[0] for row in cursor.fetchall()}
        assert "matches" in tables
        assert "odds" in tables


class TestStoreOdds:
    def test_store_inserts_matches(self, db: DBManager) -> None:
        db.store_odds(SAMPLE_ROWS)
        cursor = db.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM matches")
        count = cursor.fetchone()[0]
        assert count == 2  # m001, m002

    def test_store_inserts_odds(self, db: DBManager) -> None:
        db.store_odds(SAMPLE_ROWS)
        cursor = db.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM odds")
        count = cursor.fetchone()[0]
        assert count == len(SAMPLE_ROWS)

    def test_store_empty_list(self, db: DBManager) -> None:
        db.store_odds([])  # should not raise
        cursor = db.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM matches")
        assert cursor.fetchone()[0] == 0

    def test_upsert_match_on_duplicate(self, db: DBManager) -> None:
        db.store_odds(SAMPLE_ROWS)
        # Store again – match count should stay the same
        db.store_odds(SAMPLE_ROWS)
        cursor = db.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM matches")
        assert cursor.fetchone()[0] == 2

    def test_odds_accumulate_on_duplicate(self, db: DBManager) -> None:
        db.store_odds(SAMPLE_ROWS)
        db.store_odds(SAMPLE_ROWS)
        cursor = db.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM odds")
        # Each call inserts fresh snapshot rows
        assert cursor.fetchone()[0] == 2 * len(SAMPLE_ROWS)


class TestGetLatestOdds:
    def test_returns_latest_per_outcome(self, db: DBManager) -> None:
        db.store_odds(SAMPLE_ROWS)
        rows = db.get_latest_odds()
        # Should have one row per outcome (latest snapshot)
        assert len(rows) == len(SAMPLE_ROWS)

    def test_filter_by_sport_key(self, db: DBManager) -> None:
        db.store_odds(SAMPLE_ROWS)
        rows = db.get_latest_odds(sport_key="soccer_spain_la_liga")
        assert len(rows) == 1
        assert rows[0]["sport_key"] == "soccer_spain_la_liga"

    def test_empty_db_returns_empty(self, db: DBManager) -> None:
        rows = db.get_latest_odds()
        assert rows == []


class TestGetOddsHistory:
    def test_returns_history_for_match(self, db: DBManager) -> None:
        db.store_odds(SAMPLE_ROWS)
        db.store_odds(SAMPLE_ROWS)  # second snapshot
        rows = db.get_odds_history("m001")
        # m001 has 3 rows per snapshot × 2 snapshots = 6
        assert len(rows) == 6

    def test_filter_by_bookmaker(self, db: DBManager) -> None:
        db.store_odds(SAMPLE_ROWS)
        rows = db.get_odds_history("m001", bookmaker="Pinnacle")
        assert all(r["bookmaker"] == "Pinnacle" for r in rows)

    def test_unknown_match_returns_empty(self, db: DBManager) -> None:
        db.store_odds(SAMPLE_ROWS)
        rows = db.get_odds_history("nonexistent")
        assert rows == []


class TestGetUpcomingMatches:
    def test_returns_future_matches(self, db: DBManager) -> None:
        db.store_odds(SAMPLE_ROWS)
        rows = db.get_upcoming_matches()
        # Both matches are in 2030, so both should be upcoming
        assert len(rows) == 2

    def test_filter_by_sport_key(self, db: DBManager) -> None:
        db.store_odds(SAMPLE_ROWS)
        rows = db.get_upcoming_matches(sport_key="soccer_epl")
        assert len(rows) == 1
        assert rows[0]["sport_key"] == "soccer_epl"

    def test_empty_db_returns_empty(self, db: DBManager) -> None:
        rows = db.get_upcoming_matches()
        assert rows == []


class TestFeedback:
    def test_save_feedback_returns_id(self, db: DBManager) -> None:
        row_id = db.save_feedback("Bug Report", 4, "Found a glitch on mobile.")
        assert isinstance(row_id, int)
        assert row_id >= 1

    def test_save_feedback_increments_id(self, db: DBManager) -> None:
        id1 = db.save_feedback("General Feedback", 5, "Excellent app!")
        id2 = db.save_feedback("Feature Request", 3, "Add dark mode please.")
        assert id2 > id1

    def test_get_feedback_returns_submitted_entries(self, db: DBManager) -> None:
        db.save_feedback("General Feedback", 5, "Love it!")
        db.save_feedback("Bug Report", 2, "Crash on startup.")
        rows = db.get_feedback()
        assert len(rows) == 2

    def test_get_feedback_newest_first(self, db: DBManager) -> None:
        db.save_feedback("General Feedback", 5, "First entry.")
        db.save_feedback("Feature Request", 4, "Second entry.")
        rows = db.get_feedback()
        # Newest first: second entry's submitted_at >= first entry's
        assert rows[0]["submitted_at"] >= rows[1]["submitted_at"]

    def test_get_feedback_respects_limit(self, db: DBManager) -> None:
        for i in range(10):
            db.save_feedback("General Feedback", 3, f"Entry {i}")
        rows = db.get_feedback(limit=5)
        assert len(rows) == 5

    def test_get_feedback_empty_db(self, db: DBManager) -> None:
        rows = db.get_feedback()
        assert rows == []

    def test_get_feedback_row_shape(self, db: DBManager) -> None:
        db.save_feedback("UI / UX", 4, "Clean interface.")
        rows = db.get_feedback()
        assert len(rows) == 1
        row = rows[0]
        assert set(row.keys()) == {"id", "category", "rating", "message", "submitted_at"}
        assert row["category"] == "UI / UX"
        assert row["rating"] == 4
        assert row["message"] == "Clean interface."

    def test_save_feedback_invalid_rating_low(self, db: DBManager) -> None:
        with pytest.raises(ValueError, match="rating must be between 1 and 5 \\(inclusive\\)"):
            db.save_feedback("General Feedback", 0, "Bad rating.")

    def test_save_feedback_invalid_rating_high(self, db: DBManager) -> None:
        with pytest.raises(ValueError, match="rating must be between 1 and 5 \\(inclusive\\)"):
            db.save_feedback("General Feedback", 6, "Bad rating.")

    def test_feedback_table_created(self, db: DBManager) -> None:
        cursor = db.conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = {row[0] for row in cursor.fetchall()}
        assert "feedback" in tables
