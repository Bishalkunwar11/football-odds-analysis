"""Focused unit tests for DBManager using a temp sqlite file."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.db_manager import DBManager


def _sample_rows() -> list[dict]:
    return [
        {
            "match_id": "m1",
            "sport_key": "soccer_epl",
            "league": "EPL",
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "commence_time": "2030-01-01T12:00:00Z",
            "bookmaker": "Pinnacle",
            "market": "h2h",
            "outcome_name": "Home",
            "outcome_price": 2.1,
            "point": None,
        },
        {
            "match_id": "m1",
            "sport_key": "soccer_epl",
            "league": "EPL",
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "commence_time": "2030-01-01T12:00:00Z",
            "bookmaker": "Pinnacle",
            "market": "h2h",
            "outcome_name": "Away",
            "outcome_price": 3.4,
            "point": None,
        },
        {
            "match_id": "m1",
            "sport_key": "soccer_epl",
            "league": "EPL",
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "commence_time": "2030-01-01T12:00:00Z",
            "bookmaker": "Pinnacle",
            "market": "h2h",
            "outcome_name": "Draw",
            "outcome_price": 3.2,
            "point": None,
        },
    ]


def test_store_odds_and_get_latest_odds(tmp_path) -> None:
    db_path = tmp_path / "test_odds.db"
    db = DBManager(str(db_path))
    db.store_odds(_sample_rows())

    latest = db.get_latest_odds()
    assert len(latest) == 3
    assert {row["outcome_name"] for row in latest} == {"Home", "Away", "Draw"}

    db.close()


def test_get_latest_odds_filters_by_sport_key(tmp_path) -> None:
    db_path = tmp_path / "test_filter.db"
    db = DBManager(str(db_path))

    rows = _sample_rows()
    rows.append(
        {
            "match_id": "m2",
            "sport_key": "soccer_spain_la_liga",
            "league": "La Liga",
            "home_team": "Real Madrid",
            "away_team": "Barcelona",
            "commence_time": "2030-01-02T12:00:00Z",
            "bookmaker": "Pinnacle",
            "market": "h2h",
            "outcome_name": "Home",
            "outcome_price": 2.0,
            "point": None,
        }
    )
    db.store_odds(rows)

    latest = db.get_latest_odds(sport_key="soccer_epl")
    assert latest
    assert all(row["sport_key"] == "soccer_epl" for row in latest)

    db.close()


def test_get_upcoming_matches_returns_only_future(tmp_path) -> None:
    db_path = tmp_path / "test_upcoming.db"
    db = DBManager(str(db_path))

    now = datetime.now(timezone.utc)
    past = (now - timedelta(days=1)).isoformat()
    future = (now + timedelta(days=1)).isoformat()

    cursor = db.conn.cursor()
    cursor.execute(
        """
        INSERT INTO matches (match_id, sport_key, league, home_team, away_team, commence_time, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        ("past_m", "soccer_epl", "EPL", "A", "B", past, now.isoformat()),
    )
    cursor.execute(
        """
        INSERT INTO matches (match_id, sport_key, league, home_team, away_team, commence_time, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        ("future_m", "soccer_epl", "EPL", "C", "D", future, now.isoformat()),
    )
    db.conn.commit()

    upcoming = db.get_upcoming_matches()
    ids = {row["match_id"] for row in upcoming}
    assert "future_m" in ids
    assert "past_m" not in ids

    db.close()


def test_get_odds_history_returns_timestamp_sorted_rows(tmp_path) -> None:
    db_path = tmp_path / "test_history.db"
    db = DBManager(str(db_path))

    now = datetime.now(timezone.utc)
    db.conn.execute(
        """
        INSERT INTO matches (match_id, sport_key, league, home_team, away_team, commence_time, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        ("m_hist", "soccer_epl", "EPL", "A", "B", "2030-01-01T12:00:00Z", now.isoformat()),
    )

    ts_values = [
        (now - timedelta(hours=2)).isoformat(),
        (now - timedelta(hours=1)).isoformat(),
        now.isoformat(),
    ]
    for price, ts in zip([2.0, 2.1, 2.2], ts_values):
        db.conn.execute(
            """
            INSERT INTO odds (match_id, bookmaker, market, outcome_name, outcome_price, point, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("m_hist", "Pinnacle", "h2h", "Home", price, None, ts),
        )
    db.conn.commit()

    history = db.get_odds_history("m_hist")
    ordered_ts = [row["timestamp"] for row in history]
    assert ordered_ts == sorted(ordered_ts)

    db.close()


def test_prune_old_odds_removes_rows_outside_retention_window(tmp_path) -> None:
    db_path = tmp_path / "test_prune.db"
    db = DBManager(str(db_path))

    now = datetime.now(timezone.utc)
    old_ts = (now - timedelta(days=45)).isoformat()
    db.conn.execute(
        """
        INSERT INTO matches (match_id, sport_key, league, home_team, away_team, commence_time, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        ("m_old", "soccer_epl", "EPL", "A", "B", "2030-01-01T12:00:00Z", now.isoformat()),
    )

    for _ in range(5):
        db.conn.execute(
            """
            INSERT INTO odds (match_id, bookmaker, market, outcome_name, outcome_price, point, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("m_old", "Pinnacle", "h2h", "Home", 2.0, None, old_ts),
        )
    db.conn.commit()

    deleted = db.prune_old_odds()
    assert deleted >= 2

    remaining = db.get_odds_history("m_old")
    assert len(remaining) <= 3

    db.close()
