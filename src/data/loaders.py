# src/data/loaders.py
"""All cached data-loading functions and the live fetch-and-store helper.

Every ``@st.cache_data`` and ``@st.cache_resource`` decorated function lives
here so they are defined in a single module and never duplicated.
"""

from __future__ import annotations

import logging

import pandas as pd
import streamlit as st

from src.analyzer import OddsAnalyzer
from src.api_client import OddsAPIClient
from src.config import (
    DEFAULT_EDGE_THRESHOLD,
    LEAGUES,
    SHARP_BOOKMAKERS,
)
from src.db_manager import DBManager

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Cached resource singletons
# ---------------------------------------------------------------------------


@st.cache_resource
def get_db() -> DBManager:
    """Return a cached :class:`DBManager` instance.

    On first call, if the database has no data the demo seeder is invoked
    automatically so the dashboard has content without a live API key.
    """
    db = DBManager()
    if not db.get_latest_odds():
        try:
            from src.seed_demo_data import seed  # noqa: PLC0415

            seed(db.db_path)
            logger.info("Auto-seeded demo data into %s", db.db_path)
        except Exception:  # noqa: BLE001
            logger.warning("Could not auto-seed demo data.", exc_info=True)
    return db


@st.cache_resource
def get_analyzer() -> OddsAnalyzer:
    """Return a cached :class:`OddsAnalyzer` instance."""
    return OddsAnalyzer()


# ---------------------------------------------------------------------------
# Cached data queries (TTL = 5 min)
# ---------------------------------------------------------------------------


@st.cache_data(ttl=300)
def load_latest_odds(sport_keys: tuple[str, ...] | None = None) -> pd.DataFrame:
    """Load the latest odds from the DB (cached 5 min).

    Args:
        sport_keys: Optional tuple of sport-key strings to filter by.

    Returns:
        DataFrame of odds rows; empty DataFrame when no data exists.
    """
    db = get_db()
    rows = db.get_latest_odds(sport_keys=sport_keys)
    return pd.DataFrame(rows) if rows else pd.DataFrame()


@st.cache_data(ttl=300)
def load_upcoming_matches(sport_keys: tuple[str, ...] | None = None) -> pd.DataFrame:
    """Load upcoming matches from the DB (cached 5 min).

    Args:
        sport_keys: Optional tuple of sport-key strings to filter by.

    Returns:
        DataFrame of upcoming match rows; empty DataFrame when no data exists.
    """
    db = get_db()
    rows = db.get_upcoming_matches(sport_keys=sport_keys)
    return pd.DataFrame(rows) if rows else pd.DataFrame()


@st.cache_data(ttl=300)
def compute_summary_stats(
    sport_keys: tuple[str, ...] | None = None,
) -> dict:
    """Compute dashboard KPIs (cached 5 min).

    Args:
        sport_keys: Optional tuple of sport-key strings to filter by.

    Returns:
        Dict with keys ``num_matches``, ``num_value_bets``, ``num_arb_opps``.
    """
    db = get_db()
    rows = db.get_latest_odds(sport_keys=sport_keys)
    if not rows:
        return {"num_matches": 0, "num_value_bets": 0, "num_arb_opps": 0}

    df = pd.DataFrame(rows)
    num_matches = df["match_id"].nunique() if not df.empty else 0

    _analyzer = get_analyzer()
    try:
        vb = _analyzer.find_value_bets(
            df, sharp_bookmakers=SHARP_BOOKMAKERS, threshold=DEFAULT_EDGE_THRESHOLD
        )
        num_value_bets = len(vb) if not vb.empty else 0
    except Exception:  # noqa: BLE001
        num_value_bets = 0

    try:
        arb = _analyzer.find_arbitrage(df)
        num_arb_opps = len(arb) if not arb.empty else 0
    except Exception:  # noqa: BLE001
        num_arb_opps = 0

    return {
        "num_matches": num_matches,
        "num_value_bets": num_value_bets,
        "num_arb_opps": num_arb_opps,
    }


@st.cache_data(ttl=300)
def compute_best_edge_map(
    sport_keys: tuple[str, ...] | None = None,
    threshold: float = 0.03,
) -> dict[str, float]:
    """Return best value-bet edge per match id (cached 5 min).

    Args:
        sport_keys: Optional tuple of sport-key strings to filter by.
        threshold: Minimum edge threshold used by the value-bet scanner.

    Returns:
        Dict mapping ``match_id`` -> maximum edge value.
    """
    db = get_db()
    rows = db.get_latest_odds(sport_keys=sport_keys)
    if not rows:
        return {}

    df = pd.DataFrame(rows)
    if df.empty:
        return {}

    _analyzer = get_analyzer()
    try:
        value_df = _analyzer.find_value_bets(
            df,
            sharp_bookmakers=SHARP_BOOKMAKERS,
            threshold=threshold,
        )
    except Exception:  # noqa: BLE001
        return {}

    if value_df.empty or "match_id" not in value_df.columns:
        return {}

    edge_map: dict[str, float] = {}
    for mid, grp in value_df.groupby("match_id"):
        edge_map[str(mid)] = float(grp["edge"].max())

    return edge_map


# ---------------------------------------------------------------------------
# Live fetch helper (not cached — triggers an API call)
# ---------------------------------------------------------------------------


def fetch_and_store(selected_leagues: list[str]) -> int:
    """Fetch odds from the API and persist them to the DB.

    The API key is read from ``st.session_state["api_key_override"]`` first
    so that a user's browser-session key is used without leaking to other
    concurrent sessions via ``os.environ``.

    Args:
        selected_leagues: List of sport-key strings to fetch.

    Returns:
        Number of odds rows stored.
    """
    session_key = st.session_state.get("api_key_override") or None
    client = OddsAPIClient(api_key=session_key) if session_key else OddsAPIClient()
    db = get_db()

    league_map = {v: k for k, v in LEAGUES.items()}
    all_rows: list[dict] = []
    failed_leagues: list[str] = []

    for sport_key in selected_leagues:
        league_name = league_map.get(sport_key, sport_key)
        with st.spinner(f"Fetching {league_name}\u2026"):
            rows = client.fetch_odds(sport_key)
            if not rows:
                failed_leagues.append(league_name)
            all_rows.extend(rows)

    if failed_leagues:
        st.sidebar.warning(
            f"\u26a0\ufe0f No data for: {', '.join(failed_leagues)}. "
            "Check your API key or network connection."
        )

    if all_rows:
        db.store_odds(all_rows)
        db.prune_old_odds()
        # Clear caches so the fresh data is reflected immediately.
        load_latest_odds.clear()
        load_upcoming_matches.clear()
        compute_summary_stats.clear()
        compute_best_edge_map.clear()

    return len(all_rows)
