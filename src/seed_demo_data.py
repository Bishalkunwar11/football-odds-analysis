"""Seed the SQLite database with realistic demo data for the dashboard.

Run with:
    python -m src.seed_demo_data

This populates the database with sample matches and odds across multiple
bookmakers and leagues so every dashboard tab has content to display.
"""

import random
from datetime import datetime, timedelta, timezone

from src.db_manager import DBManager

# ---------------------------------------------------------------------------
# Sample fixtures
# ---------------------------------------------------------------------------

FIXTURES = [
    # (home, away, sport_key, league)
    ("Arsenal", "Chelsea", "soccer_epl", "EPL"),
    ("Manchester City", "Liverpool", "soccer_epl", "EPL"),
    ("Manchester United", "Tottenham Hotspur", "soccer_epl", "EPL"),
    ("Newcastle United", "Aston Villa", "soccer_epl", "EPL"),
    ("Real Madrid", "Barcelona", "soccer_spain_la_liga", "La Liga"),
    ("Atletico Madrid", "Sevilla", "soccer_spain_la_liga", "La Liga"),
    ("Juventus", "AC Milan", "soccer_italy_serie_a", "Serie A"),
    ("Inter Milan", "Napoli", "soccer_italy_serie_a", "Serie A"),
    ("Bayern Munich", "Borussia Dortmund", "soccer_germany_bundesliga", "Bundesliga"),
    ("RB Leipzig", "Bayer Leverkusen", "soccer_germany_bundesliga", "Bundesliga"),
    ("Paris Saint-Germain", "Marseille", "soccer_france_ligue_one", "Ligue 1"),
    ("Lyon", "Monaco", "soccer_france_ligue_one", "Ligue 1"),
]

BOOKMAKERS = [
    "Pinnacle",
    "Bet365",
    "DraftKings",
    "FanDuel",
    "William Hill",
    "Betfair",
    "Unibet",
]


def _jitter(base: float, pct: float = 0.06) -> float:
    """Apply a small random jitter to a decimal odds value.

    Args:
        base: The base decimal odds to jitter.
        pct: Maximum fractional deviation in either direction (default 6%).

    Returns:
        Jittered decimal odds rounded to two decimal places.
    """
    return round(base * random.uniform(1 - pct, 1 + pct), 2)


def _make_h2h_odds(
    home_fair: float, draw_fair: float, away_fair: float
) -> list[dict]:
    """Generate h2h odds across all bookmakers with margin and jitter.

    Each bookmaker applies a random margin between 2–7% to the fair odds,
    then a small random jitter is added to simulate real-world variation.

    Args:
        home_fair: Fair (no-margin) decimal odds for the home outcome.
        draw_fair: Fair decimal odds for the draw outcome.
        away_fair: Fair decimal odds for the away outcome.

    Returns:
        List of odds row dicts, three per bookmaker (Home / Draw / Away),
        each containing ``bookmaker``, ``market``, ``outcome_name``,
        ``outcome_price``, and ``point``.
    """
    rows = []
    for book in BOOKMAKERS:
        # Each bookmaker applies a slightly different margin
        margin = random.uniform(1.02, 1.07)
        rows.append(
            {
                "bookmaker": book,
                "market": "h2h",
                "outcome_name": "Home",
                "outcome_price": max(1.01, _jitter(home_fair / margin)),
                "point": None,
            }
        )
        rows.append(
            {
                "bookmaker": book,
                "market": "h2h",
                "outcome_name": "Draw",
                "outcome_price": max(1.01, _jitter(draw_fair / margin)),
                "point": None,
            }
        )
        rows.append(
            {
                "bookmaker": book,
                "market": "h2h",
                "outcome_name": "Away",
                "outcome_price": max(1.01, _jitter(away_fair / margin)),
                "point": None,
            }
        )
    return rows


def _make_totals_odds(
    over_fair: float, under_fair: float, point: float = 2.5
) -> list[dict]:
    """Generate Over/Under totals odds across all bookmakers.

    Each bookmaker applies a random margin between 2–6% to the fair odds,
    then a small random jitter is added.

    Args:
        over_fair: Fair decimal odds for the Over outcome.
        under_fair: Fair decimal odds for the Under outcome.
        point: The goals line (e.g. 2.5). Defaults to 2.5.

    Returns:
        List of odds row dicts, two per bookmaker (Over / Under), each
        containing ``bookmaker``, ``market``, ``outcome_name``,
        ``outcome_price``, and ``point``.
    """
    rows = []
    for book in BOOKMAKERS:
        margin = random.uniform(1.02, 1.06)
        rows.append(
            {
                "bookmaker": book,
                "market": "totals",
                "outcome_name": "Over",
                "outcome_price": max(1.01, _jitter(over_fair / margin)),
                "point": point,
            }
        )
        rows.append(
            {
                "bookmaker": book,
                "market": "totals",
                "outcome_name": "Under",
                "outcome_price": max(1.01, _jitter(under_fair / margin)),
                "point": point,
            }
        )
    return rows


def seed(db_path: str = "data/football_odds.db") -> None:
    """Populate the database with demo fixtures and three odds snapshots.

    Generates realistic h2h and totals odds for every fixture in
    ``FIXTURES`` across all bookmakers in ``BOOKMAKERS``, then stores
    three successive snapshots with small price movements to support
    the Odds Movement dashboard tab.

    Args:
        db_path: File-system path to the SQLite database. Defaults to
            ``"data/football_odds.db"``. Use ``":memory:"`` for tests.
    """
    random.seed(42)
    db = DBManager(db_path)
    now = datetime.now(timezone.utc)

    all_rows: list[dict] = []

    for idx, (home, away, sport_key, league) in enumerate(FIXTURES):
        match_id = f"demo_{sport_key}_{idx:03d}"
        # Kick-off 1–7 days in the future
        commence = now + timedelta(days=random.randint(1, 7), hours=random.randint(12, 20))

        base = {
            "match_id": match_id,
            "sport_key": sport_key,
            "league": league,
            "home_team": home,
            "away_team": away,
            "commence_time": commence.isoformat(),
        }

        # Random fair odds (probabilities that sum to 1)
        home_prob = random.uniform(0.30, 0.55)
        draw_prob = random.uniform(0.20, 0.30)
        away_prob = 1.0 - home_prob - draw_prob
        if away_prob < 0.10:
            away_prob = 0.15
            draw_prob = max(0.15, 1.0 - home_prob - away_prob)

        home_fair = round(1.0 / home_prob, 2)
        draw_fair = round(1.0 / draw_prob, 2)
        away_fair = round(1.0 / away_prob, 2)

        h2h_rows = _make_h2h_odds(home_fair, draw_fair, away_fair)
        totals_rows = _make_totals_odds(
            over_fair=round(1.0 / random.uniform(0.45, 0.55), 2),
            under_fair=round(1.0 / random.uniform(0.45, 0.55), 2),
        )

        for odds_row in h2h_rows + totals_rows:
            all_rows.append({**base, **odds_row})

    # Store the first snapshot
    db.store_odds(all_rows)

    # Create a second snapshot with slightly moved odds (for movement charts)
    moved_rows: list[dict] = []
    for row in all_rows:
        moved = dict(row)
        moved["outcome_price"] = max(
            1.01, round(row["outcome_price"] * random.uniform(0.97, 1.03), 2)
        )
        moved_rows.append(moved)
    db.store_odds(moved_rows)

    # Create a third snapshot
    moved_rows2: list[dict] = []
    for row in moved_rows:
        moved = dict(row)
        moved["outcome_price"] = max(
            1.01, round(row["outcome_price"] * random.uniform(0.96, 1.04), 2)
        )
        moved_rows2.append(moved)
    db.store_odds(moved_rows2)

    db.close()
    print(f"Seeded {len(all_rows)} odds rows × 3 snapshots = {len(all_rows) * 3} total rows.")


if __name__ == "__main__":
    seed()
