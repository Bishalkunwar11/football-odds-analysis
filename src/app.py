"""Streamlit dashboard for the football odds analysis system."""

import logging
import sys
from datetime import datetime as _dt
from pathlib import Path

# Ensure the project root is on sys.path so that ``src`` is importable
# when Streamlit rewrites sys.path[0] to the script's directory.
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import pandas as pd
import plotly.express as px
import streamlit as st

from src.api_client import OddsAPIClient
from src.analyzer import OddsAnalyzer
from src.bet_calculator import BetCalculator
from src.config import (
    DEFAULT_EDGE_THRESHOLD,
    LEAGUES,
    METER_LIMIT_ARB_OPS,
    METER_LIMIT_MATCHES,
    METER_LIMIT_VALUE_BETS,
    ODDS_API_KEY,
    SHARP_BOOKMAKERS,
    STAKE_QUICK_ADD,
)
from src.db_manager import DBManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="ApexOdds Pro | Premium Analytics",
    page_icon="\u26bd",
    layout="wide",
)

# Load Google Fonts via <link> tags so they are not blocked by CSP or
# sandbox restrictions that prevent @import inside <style> blocks.
st.markdown(
    '<link href="https://fonts.googleapis.com/css2?family=Inter:'
    'wght@400;500;600;700;800;900&family=JetBrains+Mono:'
    'wght@500;700&display=swap" rel="stylesheet">'
    '<link href="https://fonts.googleapis.com/css2?family=Material+'
    'Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200"'
    ' rel="stylesheet">',
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# CSS loader – reads src/assets/styles.css once at startup
# ---------------------------------------------------------------------------
def _load_css() -> None:
    css_path = Path(__file__).parent / "assets" / "styles.css"
    st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)


_load_css()


# ---------------------------------------------------------------------------
# HTML rendering helpers (moved to src/ui_components.py)
# ---------------------------------------------------------------------------
from src.ui_components import (
    _apply_dark_theme,
    render_arb_card,
    render_calculator_card,
    render_count_badge,
    render_csv_download,
    render_featured_live_card,
    render_match_card,
    render_parlay_leg,
    render_parlay_summary,
    render_payout_hero,
    render_section_banner,
    render_slip_card,
    render_stat_panel,
    render_summary_metric_card,
    render_value_card,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@st.cache_resource
def get_db() -> DBManager:
    """Return a cached database manager instance.

    On first run, if the database is empty the demo data seeder is invoked
    automatically so the dashboard has content to display without needing a
    live API key.
    """
    db = DBManager()
    # Auto-seed demo data when the database has no matches yet.
    if not db.get_latest_odds():
        try:
            from src.seed_demo_data import seed  # noqa: WPS433

            seed(db.db_path)
            logger.info("Auto-seeded demo data into %s", db.db_path)
        except Exception:  # noqa: BLE001
            logger.warning("Could not auto-seed demo data.", exc_info=True)
    return db


@st.cache_data(ttl=300)
def load_latest_odds(sport_keys: tuple[str, ...] | None = None) -> pd.DataFrame:
    """Load the latest odds from the database (cached 5 min)."""
    db = get_db()
    rows = db.get_latest_odds(sport_keys=sport_keys)
    return pd.DataFrame(rows) if rows else pd.DataFrame()


@st.cache_data(ttl=300)
def load_upcoming_matches(sport_keys: tuple[str, ...] | None = None) -> pd.DataFrame:
    """Load upcoming matches from the database (cached 5 min)."""
    db = get_db()
    rows = db.get_upcoming_matches(sport_keys=sport_keys)
    return pd.DataFrame(rows) if rows else pd.DataFrame()


@st.cache_data(ttl=300)
def compute_summary_stats(
    sport_keys: tuple[str, ...] | None = None,
) -> dict:
    """Compute dashboard KPIs cached for 5 minutes.

    Calculates the headline numbers shown in the summary metrics bar so
    they are not re-derived on every Streamlit re-run.

    Args:
        sport_keys: Optional tuple of sport-key strings to filter by.
            Pass ``None`` to include all leagues.

    Returns:
        Dict with keys ``num_matches``, ``num_value_bets``,
        ``num_arb_opps``.
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
    except Exception:
        num_value_bets = 0

    try:
        arb = _analyzer.find_arbitrage(df)
        num_arb_opps = len(arb) if not arb.empty else 0
    except Exception:
        num_arb_opps = 0

    return {
        "num_matches": num_matches,
        "num_value_bets": num_value_bets,
        "num_arb_opps": num_arb_opps,
    }


@st.cache_resource
def get_analyzer() -> OddsAnalyzer:
    """Return a cached analyzer instance used by KPI computations."""
    return OddsAnalyzer()


def fetch_and_store(selected_leagues: list[str]) -> int:
    """Fetch odds from the API and persist them.

    The API key is read from ``st.session_state["api_key_override"]`` first
    so that a user's browser-session key is used without leaking to other
    concurrent sessions via ``os.environ``.

    Args:
        selected_leagues: Display names of leagues to fetch.

    Returns:
        Number of odds rows stored.
    """
    # Use the per-session key override when available (OWASP A07).
    session_key = st.session_state.get("api_key_override") or None
    client = OddsAPIClient(api_key=session_key) if session_key else OddsAPIClient()
    db = get_db()
    all_rows: list[dict] = []
    failed_leagues: list[str] = []
    league_map = {v: k for k, v in LEAGUES.items()}

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
        # Clear caches so new data is reflected immediately
        load_latest_odds.clear()
        load_upcoming_matches.clear()
        compute_summary_stats.clear()

    return len(all_rows)


# ---------------------------------------------------------------------------
# Session state initialization
# ---------------------------------------------------------------------------
if "active_section" not in st.session_state:
    st.session_state["active_section"] = "matches"
if "bet_slip" not in st.session_state:
    st.session_state["bet_slip"] = []
if "parlay_legs" not in st.session_state:
    st.session_state["parlay_legs"] = []
if "last_refreshed" not in st.session_state:
    st.session_state["last_refreshed"] = None

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

st.sidebar.markdown(
    """
    <div style="
        position: relative;
        overflow: hidden;
        background: linear-gradient(135deg, rgba(20,24,255,0.18) 0%, rgba(0,30,57,0.88) 60%, rgba(0,43,82,0.72) 100%);
        border: 1px solid rgba(20,24,255,0.28);
        border-radius: 14px;
        padding: 1.3rem 1rem 1.1rem 1rem;
        margin-bottom: 1rem;
        text-align: center;
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        box-shadow: 0 8px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.08);
    ">
        <div style="
            position: absolute; top: 0; left: 0; right: 0; height: 2px;
            background: linear-gradient(90deg, #1418FF, #004797, #00C853);
        "></div>
        <div style="
            width:38px; height:38px;
            background: linear-gradient(135deg, #1418FF, #004797);
            border-radius: 10px;
            display: flex; align-items: center;
            justify-content: center; margin: 0 auto 0.55rem auto;
            box-shadow: 0 4px 16px rgba(20,24,255,0.4), inset 0 1px 0 rgba(255,255,255,0.15);
        "><svg width="20" height="20" viewBox="0 0 24 24" fill="none">
            <rect x="1" y="1" width="10" height="10" rx="2.5" fill="white"/>
            <rect x="13" y="1" width="10" height="10" rx="2.5" fill="white" opacity="0.85"/>
            <rect x="1" y="13" width="10" height="10" rx="2.5" fill="white" opacity="0.85"/>
            <rect x="13" y="13" width="10" height="10" rx="2.5" fill="white"/>
        </svg></div>
        <div style="
            font-size: 0.9rem;
            font-weight: 900;
            letter-spacing: 0.1em;
            color: #E7EEF7;
            text-transform: uppercase;
        ">APEX<span style="color:#8FB7FF;">ODDS</span></div>
        <div style="
            display: inline-block;
            margin-top: 0.3rem;
            font-size: 0.6rem;
            font-weight: 700;
            letter-spacing: 0.2em;
            color: #00C853;
            text-transform: uppercase;
            background: rgba(0,200,83,0.1);
            border: 1px solid rgba(0,200,83,0.22);
            padding: 0.15rem 0.6rem;
            border-radius: 20px;
        ">PRO TERMINAL</div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.sidebar.title("\u2699\ufe0f Settings")

league_options = {name: key for name, key in LEAGUES.items()}
selected_league_names: list[str] = st.sidebar.multiselect(
    "Select Leagues",
    options=list(league_options.keys()),
    default=list(league_options.keys()),
)
selected_sport_keys: list[str] = [
    league_options[n] for n in selected_league_names
]

# A fetch can use either a configured .env key or a session override.
_session_api_key = st.session_state.get("api_key_override")
_has_api_key = bool(_session_api_key or ODDS_API_KEY)

if not _has_api_key:
    st.sidebar.info(
        "Live refresh needs an API key. Add ODDS_API_KEY to .env "
        "or use API Key Override below."
    )

if st.sidebar.button("\U0001f504 Refresh Data", disabled=not _has_api_key):
    if not selected_sport_keys:
        st.sidebar.warning("Please select at least one league.")
    else:
        count = fetch_and_store(selected_sport_keys)
        if count:
            st.session_state["last_refreshed"] = pd.Timestamp.now().strftime(
                "%H:%M:%S"
            )
            st.sidebar.success(f"Stored {count} odds rows.")
        else:
            st.sidebar.warning("No data returned. Check your API key.")

# OWASP A07 – allow users to supply an API key override directly in the
# browser UI. The value is stored only in session_state (server RAM) and
# is never written to disk, logs, or the DB.
st.sidebar.markdown("---")
st.sidebar.markdown(
    "<span style='font-size:0.78rem;color:#8899AA;font-weight:600;"
    "text-transform:uppercase;letter-spacing:0.06em;'>"
    "🔑 API Key Override</span>",
    unsafe_allow_html=True,
)
api_key_override = st.sidebar.text_input(
    "API Key (optional)",
    type="password",
    key="sidebar_api_key",
    help=(
        "Enter your The-Odds-API key here to override the .env value. "
        "Stored in session memory only — never persisted to disk."
    ),
    label_visibility="collapsed",
    placeholder="Paste key to override .env…",
)
# Store the override in session_state only.  This is session-scoped and
# does NOT leak to other concurrent users (unlike os.environ).
# OWASP A07 – the key stays in RAM for this browser tab only.
if api_key_override:
    st.session_state["api_key_override"] = api_key_override
    st.sidebar.caption("✅ Key active for this session.")
elif "api_key_override" not in st.session_state:
    st.session_state["api_key_override"] = None

# Last-refresh indicator
if st.session_state.get("last_refreshed"):
    st.sidebar.caption(
        f"🕐 Last refreshed: {st.session_state['last_refreshed']}"
    )

# Subscription status panel – terminal design element
st.sidebar.markdown(
    """
    <div class="subscription-box">
        <div class="sub-header">
            <span class="sub-label">Subscription</span>
            <span class="sub-tier">ELITE</span>
        </div>
        <div class="sub-bar">
            <div class="sub-bar-fill"></div>
        </div>
        <div class="sub-days">12 days remaining</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Main content
# ---------------------------------------------------------------------------

st.markdown(
    """
    <div class="terminal-topbar">
        <div class="brand">
            <div class="brand-icon" style="
                background: linear-gradient(135deg, #1418FF, #004797);
                box-shadow: 0 0 16px rgba(20,24,255,0.45), inset 0 1px 0 rgba(255,255,255,0.15);
            ">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                    <rect x="1" y="1" width="10" height="10" rx="2" fill="white"/>
                    <rect x="13" y="1" width="10" height="10" rx="2" fill="white"/>
                    <rect x="1" y="13" width="10" height="10" rx="2" fill="white"/>
                    <rect x="13" y="13" width="10" height="10" rx="2" fill="white"/>
                </svg>
            </div>
            <div class="brand-text" style="font-size:1.2rem;">APEX<span class="accent">ODDS</span> <span style="color:#8FA8C8;font-weight:500;font-size:0.85rem;letter-spacing:0.04em;">PRO</span></div>
            <div class="top-nav" style="margin-left: 2rem;">
                <a href="#">Matches</a>
                <a class="active" href="#">Value Bets</a>
                <a href="#">Arbitrage</a>
                <a href="#">Calculators</a>
            </div>
        </div>
        <div class="top-right">
            <div class="search-wrapper">
                <svg class="search-icon" width="14" height="14" viewBox="0 0 24 24"
                     fill="none" stroke="#556677" stroke-width="2.5"
                     stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="11" cy="11" r="8"/>
                    <line x1="21" y1="21" x2="16.65" y2="16.65"/>
                </svg>
                <input class="search-input" placeholder="Search markets..." type="text" aria-label="Search markets" />
            </div>
            <div class="live-feed" style="gap:0.5rem;">
                <div class="live-dot"></div>
                <span class="live-text">Live Feed</span>
            </div>
            <div class="user-avatar" style="
                background: linear-gradient(135deg, #00C853, #1418FF);
                box-shadow: 0 0 12px rgba(0,200,83,0.3);
            ">
                <div class="user-avatar-inner">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
                         stroke="#E8EAED" stroke-width="2" stroke-linecap="round"
                         stroke-linejoin="round">
                        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                        <circle cx="12" cy="7" r="4"/>
                    </svg>
                </div>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero-header">
        <div style="
            position: absolute; top: -30%; right: -8%;
            width: 280px; height: 280px;
            background: radial-gradient(circle, rgba(20,24,255,0.12) 0%, transparent 70%);
            pointer-events: none;
        "></div>
        <div style="
            position: absolute; bottom: -20%; left: 30%;
            width: 200px; height: 200px;
            background: radial-gradient(circle, rgba(0,200,83,0.07) 0%, transparent 70%);
            pointer-events: none;
        "></div>
        <div class="hero-title">\u26bd ApexOdds <span class="accent">Pro</span></div>
        <div class="hero-sub">
            PREMIUM ANALYTICS
            <span class="dot"></span>
            REAL-TIME ODDS
            <span class="dot"></span>
            SMART CALCULATORS
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

analyzer = OddsAnalyzer()

# Filter at SQL layer — pass the selected-league tuple directly so the DB
# only returns the rows we need instead of loading the full table in Python.
_sport_key_tuple = tuple(selected_sport_keys) if selected_sport_keys else None
odds_df = load_latest_odds(_sport_key_tuple)
upcoming_df_base = load_upcoming_matches(_sport_key_tuple)

# ---------------------------------------------------------------------------
# SUMMARY METRICS BAR  (Performance skill – cached computation)
# Clickable cards jump to the corresponding analysis section.
# ---------------------------------------------------------------------------

_stats = compute_summary_stats(_sport_key_tuple)

bookmakers_count = (
    odds_df["bookmaker"].nunique() if not odds_df.empty else 0
)

sm_col1, sm_col2, sm_col3, sm_col4 = st.columns(4)
with sm_col1:
    st.markdown(
        render_summary_metric_card(
            label="Upcoming Matches",
            value=_stats["num_matches"],
            badge_text="Fixtures Loaded",
            color="green",
            meter_pct=min(_stats["num_matches"] / METER_LIMIT_MATCHES * 100, 100),
        ),
        unsafe_allow_html=True,
    )
    if st.button("→ View Matches", key="jump_matches", use_container_width=True):
        st.session_state["active_section"] = "matches"
        st.rerun()
with sm_col2:
    st.markdown(
        render_summary_metric_card(
            label="Value Bets",
            value=_stats["num_value_bets"],
            badge_text="≥5% Edge",
            color="red",
            meter_pct=min(_stats["num_value_bets"] / METER_LIMIT_VALUE_BETS * 100, 100),
        ),
        unsafe_allow_html=True,
    )
    if st.button("→ View Value Bets", key="jump_value", use_container_width=True):
        st.session_state["active_section"] = "value"
        st.rerun()
with sm_col3:
    st.markdown(
        render_summary_metric_card(
            label="Arb Opportunities",
            value=_stats["num_arb_opps"],
            badge_text="Risk-Free",
            color="gold",
            meter_pct=min(_stats["num_arb_opps"] / METER_LIMIT_ARB_OPS * 100, 100),
        ),
        unsafe_allow_html=True,
    )
    if st.button("→ View Arbitrage", key="jump_arb", use_container_width=True):
        st.session_state["active_section"] = "arb"
        st.rerun()
with sm_col4:
    st.markdown(
        render_summary_metric_card(
            label="Active Bookmakers",
            value=bookmakers_count,
            badge_text="Data Sources",
            color="blue",
            meter_pct=min(bookmakers_count / METER_LIMIT_VALUE_BETS * 100, 100),
        ),
        unsafe_allow_html=True,
    )
    if st.button("→ View Margins", key="jump_margins", use_container_width=True):
        st.session_state["active_section"] = "margins"
        st.rerun()

st.markdown("<hr style='margin: 0.4rem 0 0.8rem 0;'>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# THREE-PANE LAYOUT
# ---------------------------------------------------------------------------

NAV_SECTIONS = [
    ("matches", "\U0001f4c5 Matches"),
    ("value", "\U0001f4a1 Value Bets"),
    ("movement", "\U0001f4c8 Movement"),
    ("calc", "\U0001f9ee Bet Calculator"),
    ("arb", "\U0001f504 Arbitrage"),
    ("margins", "\U0001f4ca Margins"),
    ("parlay", "\U0001f3af Custom Parlay"),
    ("feedback", "\U0001f4ac Feedback"),
    ("settings", "\U00002699\U0000fe0f Settings"),
]

col_nav, col_main, col_slip = st.columns([2, 5, 3])

# ── Left Navigation Panel ──
with col_nav:
    st.markdown(
        '<div class="terminal-menu-heading">Terminal Menu</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="nav-panel">', unsafe_allow_html=True)
    for key, label in NAV_SECTIONS:
        is_active = st.session_state["active_section"] == key
        if st.button(label, key=f"nav_{key}", use_container_width=True,
                      type="primary" if is_active else "secondary"):
            st.session_state["active_section"] = key
    st.markdown('</div>', unsafe_allow_html=True)



def _render_matches(
    odds_df: "pd.DataFrame",
    upcoming_df_base: "pd.DataFrame",
    analyzer: "OddsAnalyzer",
) -> None:
    st.markdown(
        render_section_banner(
            "Live Dashboard",
            "Upcoming Matches",
            "Monitor fixtures and compare best available prices in one grid.",
        ),
        unsafe_allow_html=True,
    )
    upcoming_df = upcoming_df_base

    # Featured live match card (demo / static showcase)
    # Featured live match card — static demo showcase using the first
    # available match.  Real live-score data would require a dedicated
    # live-scores API endpoint (not available from The-Odds-API).
    if not upcoming_df.empty and len(upcoming_df) >= 2:
        first_row = upcoming_df.iloc[0]
        st.markdown(
            render_featured_live_card(
                home=first_row["home_team"],
                away=first_row["away_team"],
                home_score=2,
                away_score=1,
                minute="74'",
                league=first_row.get("league", "Premier League"),
            ),
            unsafe_allow_html=True,
        )

    if upcoming_df.empty:
        st.markdown(
            '<div class="empty-state">'
            '<div class="empty-icon">\U0001f4c5</div>'
            '<div class="empty-text">No upcoming matches in the database.<br>'
            'Use <b>Refresh Data</b> in the sidebar to fetch odds.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        # Real-time team search (performance: pure pandas, no extra DB hit)
        team_search = st.text_input(
            "🔍 Search teams…",
            key="match_search",
            placeholder="e.g. Arsenal, Real Madrid",
        )
        if team_search.strip():
            mask = (
                upcoming_df["home_team"].str.contains(
                    team_search, case=False, na=False
                )
                | upcoming_df["away_team"].str.contains(
                    team_search, case=False, na=False
                )
            )
            upcoming_df = upcoming_df[mask]

        if upcoming_df.empty:
            st.info(f'No matches found for "{team_search}".')
        else:
            st.markdown(render_count_badge(len(upcoming_df)) + " Matches", unsafe_allow_html=True)

            # Build best-odds lookup per match
            best_odds_map: dict[str, dict[str, float]] = {}
            if not odds_df.empty:
                h2h = odds_df[odds_df["market"] == "h2h"]
                if not h2h.empty:
                    best = (
                        h2h.groupby(["match_id", "outcome_name"])["outcome_price"]
                        .max()
                        .unstack("outcome_name")
                    )
                    for mid in best.index:
                        row_dict = best.loc[mid].dropna().to_dict()
                        if row_dict:
                            best_odds_map[mid] = row_dict

            # Build best edge per match for PRO EDGE badges
            best_edge_map: dict[str, float] = {}
            if not odds_df.empty:
                try:
                    _vb_for_map = analyzer.find_value_bets(
                        odds_df, sharp_bookmakers=SHARP_BOOKMAKERS, threshold=0.03
                    )
                    if not _vb_for_map.empty and "match_id" in _vb_for_map.columns:
                        for _mid, _grp in _vb_for_map.groupby("match_id"):
                            best_edge_map[str(_mid)] = float(_grp["edge"].max())
                except Exception:
                    pass

            # Render cards in a two-column grid
            cols = st.columns(2)
            for idx, (_, row) in enumerate(upcoming_df.iterrows()):
                m_id = row.get("match_id", "")
                odds_for_match = best_odds_map.get(m_id)
                card_html = render_match_card(
                    home=row["home_team"],
                    away=row["away_team"],
                    league=row.get("league", ""),
                    kickoff=str(row["commence_time"]),
                    odds=odds_for_match,
                    edge_pct=best_edge_map.get(m_id),
                )
                with cols[idx % 2]:
                    st.markdown(card_html, unsafe_allow_html=True)

# --- Value Bets ---


def _render_value_bets(
    odds_df: "pd.DataFrame",
    analyzer: "OddsAnalyzer",
) -> None:
    st.markdown(
        render_section_banner(
            "Edge Scanner",
            "Value Bets",
            "Track positive expected value opportunities against sharp lines.",
        ),
        unsafe_allow_html=True,
    )
    if odds_df.empty:
        st.markdown(
            '<div class="empty-state">'
            '<div class="empty-icon">\U0001f4a1</div>'
            '<div class="empty-text">No odds data available. Refresh data first.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        vb_filter = st.radio(
            "Filter",
            ["All Markets", "High Edge (>10%)", "New"],
            horizontal=True,
            key="vb_filter",
            label_visibility="collapsed",
        )
        threshold = st.slider(
            "Minimum edge threshold", 0.01, 0.20, DEFAULT_EDGE_THRESHOLD, 0.01,
            key="value_threshold",
        )
        value_df = analyzer.find_value_bets(
            odds_df, sharp_bookmakers=SHARP_BOOKMAKERS, threshold=threshold
        )
        # Apply filter
        if not value_df.empty:
            if vb_filter == "High Edge (>10%)":
                value_df = value_df[value_df["edge"] > 0.10]
            elif vb_filter == "New":
                value_df = value_df.head(5)
        if value_df.empty:
            st.success(
                "No value bets found at the current threshold. "
                "Try lowering the threshold or changing the filter."
            )
        else:
            # Header row: count badge + CSV export (Performance skill)
            badge_col, dl_col = st.columns([3, 1])
            with badge_col:
                st.markdown(render_count_badge(len(value_df)) + " Value Bets", unsafe_allow_html=True)
            with dl_col:
                render_csv_download(value_df, "value_bets.csv", "📥 Export CSV")

            # Edge distribution histogram (Performance skill – Plotly)
            fig_edge = px.histogram(
                value_df,
                x="edge",
                nbins=15,
                title="Edge Distribution",
                labels={"edge": "Edge (probability units)"},
                color_discrete_sequence=["#00C853"],
            )
            fig_edge.update_layout(bargap=0.08, showlegend=False)
            _apply_dark_theme(fig_edge)
            st.plotly_chart(fig_edge, use_container_width=True)

            # Single BetCalculator instance reused for all rows (Performance)
            _bet_calc_vb = BetCalculator()
            for _, vrow in value_df.iterrows():
                price = float(vrow.get("outcome_price", 0))
                # Safely convert to American odds for display alongside decimal
                try:
                    american = _bet_calc_vb.decimal_to_american(price)
                    american_str: str | None = f"{american:+d}"
                except (ValueError, ZeroDivisionError):
                    american_str = None

                card = render_value_card(
                    home=vrow.get("home_team", ""),
                    away=vrow.get("away_team", ""),
                    outcome=vrow.get("outcome_name", ""),
                    bookmaker=vrow.get("bookmaker", ""),
                    price=price,
                    edge=float(vrow.get("edge", 0)),
                    american_odds=american_str,
                )
                st.markdown(card, unsafe_allow_html=True)

# --- Arbitrage ---


def _render_arbitrage(
    odds_df: "pd.DataFrame",
    analyzer: "OddsAnalyzer",
) -> None:
    st.markdown(
        render_section_banner(
            "Risk-Free Engine",
            "Arbitrage Opportunities",
            "Identify cross-bookmaker pricing gaps with guaranteed upside.",
        ),
        unsafe_allow_html=True,
    )
    if odds_df.empty:
        st.markdown(
            '<div class="empty-state">'
            '<div class="empty-icon">\U0001f504</div>'
            '<div class="empty-text">No odds data available. Refresh data first.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        arb_df = analyzer.find_arbitrage(odds_df)
        if arb_df.empty:
            st.success("No arbitrage opportunities found in current data.")
        else:
            # Header row: count badge + CSV export
            arb_badge_col, arb_dl_col = st.columns([3, 1])
            with arb_badge_col:
                st.markdown(render_count_badge(len(arb_df)) + " Opportunities", unsafe_allow_html=True)
            with arb_dl_col:
                render_csv_download(
                    arb_df.drop(columns=["best_odds"], errors="ignore"),
                    "arbitrage.csv",
                    "📥 Export CSV",
                )
            for _, arow in arb_df.iterrows():
                card = render_arb_card(
                    home=arow["home_team"],
                    away=arow["away_team"],
                    market=arow["market"],
                    arb_pct=float(arow["arb_pct"]),
                    best_odds=arow["best_odds"],
                )
                st.markdown(card, unsafe_allow_html=True)

# --- Movement ---


def _render_movement(
    upcoming_df_base: "pd.DataFrame",
) -> None:
    st.markdown(
        render_section_banner(
            "Market Pulse",
            "Odds Movement",
            "Overlay historical price movement by bookmaker and outcome.",
        ),
        unsafe_allow_html=True,
    )
    upcoming_df2 = upcoming_df_base

    if upcoming_df2.empty:
        st.markdown(
            '<div class="empty-state">'
            '<div class="empty-icon">\U0001f4c8</div>'
            '<div class="empty-text">No matches in the database.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        match_labels = {
            f"{r['home_team']} vs {r['away_team']}": r["match_id"]
            for _, r in upcoming_df2.iterrows()
        }
        selected_match_label = st.selectbox(
            "Select Match", options=list(match_labels.keys())
        )
        selected_match_id = match_labels[selected_match_label]

        db2 = get_db()
        history = db2.get_odds_history(selected_match_id)
        hist_df = pd.DataFrame(history)

        if hist_df.empty:
            st.info("No historical odds for this match yet.")
        else:
            bookmakers = sorted(hist_df["bookmaker"].unique())
            # Multi-bookmaker comparison overlay (UX improvement)
            selected_books = st.multiselect(
                "Compare Bookmakers",
                options=bookmakers,
                default=bookmakers[:1],
                help=(
                    "Select one or more bookmakers to overlay their "
                    "price movements on the same chart."
                ),
            )

            if not selected_books:
                st.info("Select at least one bookmaker to display the chart.")
            else:
                filtered = hist_df[
                    (hist_df["bookmaker"].isin(selected_books))
                    & (hist_df["market"] == "h2h")
                ]

                if filtered.empty:
                    st.info("No h2h odds history for the selected bookmakers.")
                else:
                    # Avoid a full copy — assign the new column directly
                    filtered = filtered.assign(
                        series=(
                            filtered["bookmaker"]
                            + " – "
                            + filtered["outcome_name"]
                        )
                    )
                    fig = px.line(
                        filtered,
                        x="timestamp",
                        y="outcome_price",
                        color="series",
                        title=(
                            f"Odds Movement – "
                            f"{', '.join(selected_books)}"
                        ),
                        labels={
                            "timestamp": "Time",
                            "outcome_price": "Decimal Odds",
                            "series": "Bookmaker – Outcome",
                        },
                        markers=True,
                    )
                    _apply_dark_theme(fig)
                    st.plotly_chart(fig, use_container_width=True)

# --- Margins ---


def _render_margins(
    odds_df: "pd.DataFrame",
    analyzer: "OddsAnalyzer",
) -> None:
    st.markdown(
        render_section_banner(
            "Pricing Quality",
            "Bookmaker Margin Analysis",
            "Compare overround efficiency to find sharper books quickly.",
        ),
        unsafe_allow_html=True,
    )
    if odds_df.empty:
        st.markdown(
            '<div class="empty-state">'
            '<div class="empty-icon">\U0001f4ca</div>'
            '<div class="empty-text">No odds data available. Refresh data first.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        h2h_df = odds_df[odds_df["market"] == "h2h"]
        if h2h_df.empty:
            st.info("No 1X2 odds data available.")
        else:
            margins: list[dict] = []
            for (match_id, bookmaker), grp in h2h_df.groupby(
                ["match_id", "bookmaker"]
            ):
                prices = grp["outcome_price"].tolist()
                if len(prices) >= 2:  # noqa: PLR2004
                    try:
                        margin = analyzer.calculate_margin(prices)
                        margins.append(
                            {
                                "bookmaker": bookmaker,
                                "margin": margin * 100,
                            }
                        )
                    except ValueError:
                        continue

            if margins:
                margin_df = pd.DataFrame(margins)
                avg_margin = (
                    margin_df.groupby("bookmaker")["margin"]
                    .mean()
                    .reset_index()
                    .sort_values("margin")
                )

                fig_bar = px.bar(
                    avg_margin,
                    x="bookmaker",
                    y="margin",
                    title="Average Bookmaker Margin (%) \u2013 1X2 Markets",
                    labels={
                        "bookmaker": "Bookmaker",
                        "margin": "Avg Margin (%)",
                    },
                    color="margin",
                    color_continuous_scale="RdYlGn_r",
                )
                fig_bar.update_layout(showlegend=False)
                _apply_dark_theme(fig_bar)
                st.plotly_chart(fig_bar, use_container_width=True)

                # Sortable detail table (Performance skill – no recompute)
                st.markdown("##### Margin Detail Table")
                display_tbl = avg_margin.rename(
                    columns={"bookmaker": "Bookmaker", "margin": "Avg Margin (%)"}
                ).copy()
                display_tbl["Avg Margin (%)"] = display_tbl[
                    "Avg Margin (%)"
                ].round(3)
                st.dataframe(
                    display_tbl,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Avg Margin (%)": st.column_config.NumberColumn(
                            format="%.3f%%"
                        )
                    },
                )
            else:
                st.info("Insufficient data to compute margins.")

# --- Bet Calculator ---


def _render_calculator() -> None:
    st.markdown(
        render_section_banner(
            "Quant Tools",
            "Bet Calculator",
            "Run payout, Kelly, dutching, and conversion math with pro layouts.",
        ),
        unsafe_allow_html=True,
    )

    calc_mode = st.radio(
        "Mode",
        ["Calculator Tools", "Bet Builder"],
        horizontal=True,
        key="calc_mode",
    )

    if calc_mode == "Bet Builder":
        st.markdown(
            "Pick outcomes from available matches and build a single bet or "
            "accumulator with real odds."
        )

        bet_calc_builder = BetCalculator()

        if odds_df.empty:
            st.info(
                "No odds data available. Use **Refresh Data** in the sidebar "
                "to fetch odds first."
            )
        else:
            h2h_builder = odds_df[odds_df["market"] == "h2h"]
            if h2h_builder.empty:
                st.info("No 1X2 odds available to build bets from.")
            else:
                # Build match labels
                match_info = (
                    h2h_builder[["match_id", "home_team", "away_team", "league"]]
                    .drop_duplicates("match_id")
                    .reset_index(drop=True)
                )
                match_info["label"] = (
                    match_info["home_team"]
                    + " vs "
                    + match_info["away_team"]
                    + " ("
                    + match_info["league"]
                    + ")"
                )
                label_to_id = dict(
                    zip(match_info["label"], match_info["match_id"])
                )

                st.markdown("#### Add a Selection")
                col_m, col_o, col_b = st.columns([3, 2, 2])
                with col_m:
                    sel_match_label = st.selectbox(
                        "Match",
                        options=list(label_to_id.keys()),
                        key="builder_match",
                    )
                sel_match_id = label_to_id.get(sel_match_label, "")

                # Available outcomes for selected match
                match_h2h = h2h_builder[h2h_builder["match_id"] == sel_match_id]
                outcomes = sorted(match_h2h["outcome_name"].unique())
                bookmakers = sorted(match_h2h["bookmaker"].unique())

                with col_o:
                    sel_outcome = st.selectbox(
                        "Outcome", options=outcomes, key="builder_outcome"
                    )
                with col_b:
                    sel_bookmaker = st.selectbox(
                        "Bookmaker", options=bookmakers, key="builder_book"
                    )

                # Find the specific odds row
                specific = match_h2h[
                    (match_h2h["outcome_name"] == sel_outcome)
                    & (match_h2h["bookmaker"] == sel_bookmaker)
                ]
                if not specific.empty:
                    sel_odds = float(specific.iloc[0]["outcome_price"])
                    st.markdown(
                        f"**Selected odds:** `{sel_odds:.2f}` "
                        f"({sel_outcome} @ {sel_bookmaker})"
                    )
                else:
                    sel_odds = None
                    st.warning("No odds found for this combination.")

                if st.button("\u2795 Add to Bet Slip", key="btn_add_slip"):
                    if sel_odds is not None and sel_odds > 1.0:
                        st.session_state["bet_slip"].append(
                            {
                                "match": sel_match_label,
                                "outcome": sel_outcome,
                                "bookmaker": sel_bookmaker,
                                "decimal_odds": sel_odds,
                            }
                        )
                        st.success(
                            f"Added: {sel_outcome} ({sel_match_label}) "
                            f"@ {sel_odds:.2f}"
                        )
                    else:
                        st.error("Cannot add \u2014 no valid odds selected.")

        # --- Bet Slip Display (inline in calc pane) ---
        st.markdown("---")
        st.markdown("#### \U0001f5d2\ufe0f Your Bet Slip")
        slip = st.session_state["bet_slip"]

        if not slip:
            st.info("Your bet slip is empty. Add selections above.")
        else:
            for sel in slip:
                st.markdown(
                    render_slip_card(
                        match=sel.get("match", ""),
                        outcome=sel.get("outcome", ""),
                        odds=sel["decimal_odds"],
                    ),
                    unsafe_allow_html=True,
                )

            col_type, col_stake = st.columns(2)
            with col_type:
                builder_bet_type = st.radio(
                    "Bet Type",
                    ["Single (each selection)", "Accumulator (combined)"],
                    key="builder_bet_type",
                    horizontal=True,
                )
            with col_stake:
                builder_stake = st.number_input(
                    "Stake ($)", min_value=0.0, value=10.0, step=5.0,
                    key="builder_stake",
                )

            col_calc, col_clear = st.columns(2)
            with col_calc:
                if st.button("\U0001f4b0 Calculate Payout", key="btn_calc_slip"):
                    bt = (
                        "single"
                        if builder_bet_type.startswith("Single")
                        else "accumulator"
                    )
                    result = bet_calc_builder.build_bet_slip(
                        slip, builder_stake, bet_type=bt,
                    )
                    st.markdown("##### Results")
                    r1, r2, r3 = st.columns(3)
                    r1.metric("Combined Odds", f"{result['combined_odds']:.4f}")
                    r2.metric("Total Payout", f"${result['total_payout']:.2f}")
                    r3.metric("Total Profit", f"${result['total_profit']:.2f}")

                    if bt == "accumulator":
                        st.caption(
                            "Accumulator: all selections must win for a payout."
                        )
                    else:
                        st.caption(
                            "Single: stake is placed on each selection independently."
                        )
            with col_clear:
                if st.button("\U0001f5d1\ufe0f Clear Bet Slip", key="btn_clear_slip"):
                    st.session_state["bet_slip"] = []
                    st.rerun()

    else:  # Calculator Tools
        bet_calc = BetCalculator()

        tab_single, tab_acc, tab_conv, tab_kelly, tab_dutch = st.tabs([
            "💰 Single Bet",
            "📊 Accumulator",
            "🔄 Odds Converter",
            "🎓 Kelly",
            "⚖️ Dutching",
        ])

        # --- Single Bet ---
        with tab_single:
            st.caption("Calculate payout, profit, and implied probability for a single selection.")
            col1, col2 = st.columns(2)
            with col1:
                sb_stake = st.number_input(
                    "Stake ($)", min_value=0.0, value=100.0, step=10.0,
                    key="sb_stake",
                )
            with col2:
                sb_odds = st.number_input(
                    "Decimal Odds", min_value=1.01, value=2.50, step=0.05,
                    key="sb_odds",
                )

            if st.button("💸 Calculate Payout", key="btn_single", use_container_width=True):
                result = bet_calc.calculate_payout(sb_stake, sb_odds)
                st.markdown(
                    '<div class="calc-result-box">'
                    '<div class="calc-grid-3">'
                    f'<div><div class="calc-result-label">Payout</div><div class="calc-result-value">${result["payout"]:.2f}</div></div>'
                    f'<div><div class="calc-result-label">Profit</div><div class="calc-result-value">${result["profit"]:.2f}</div></div>'
                    f'<div><div class="calc-result-label">Implied Prob.</div><div class="calc-result-value">{result["implied_probability"]:.1%}</div></div>'
                    '</div>'
                    '</div>',
                    unsafe_allow_html=True,
                )

        # --- Accumulator / Parlay ---
        with tab_acc:
            st.caption("Combine multiple selections into a single bet with multiplied odds.")
            col_stake, col_legs = st.columns(2)
            with col_stake:
                acc_stake = st.number_input(
                    "Stake ($)", min_value=0.0, value=10.0, step=5.0,
                    key="acc_stake",
                )
            with col_legs:
                num_legs = st.number_input(
                    "Number of Legs", min_value=2, max_value=20, value=3, step=1,
                    key="acc_legs",
                )

            leg_odds: list[float] = []
            cols = st.columns(min(int(num_legs), 5))
            for i in range(int(num_legs)):
                with cols[i % len(cols)]:
                    val = st.number_input(
                        f"Leg {i + 1} Odds", min_value=1.01, value=2.0, step=0.05,
                        key=f"acc_leg_{i}",
                    )
                    leg_odds.append(val)

            if st.button("🎯 Calculate Accumulator", key="btn_acc", use_container_width=True):
                result = bet_calc.calculate_accumulator(acc_stake, leg_odds)
                st.markdown(
                    '<div class="calc-result-box">'
                    '<div class="calc-grid-3">'
                    f'<div><div class="calc-result-label">Combined Odds</div><div class="calc-result-value">{result["combined_odds"]:.2f}x</div></div>'
                    f'<div><div class="calc-result-label">Payout</div><div class="calc-result-value">${result["payout"]:.2f}</div></div>'
                    f'<div><div class="calc-result-label">Profit</div><div class="calc-result-value">${result["profit"]:.2f}</div></div>'
                    '</div>'
                    '<div style="margin-top: 0.6rem; font-size: 0.72rem; color: #8899AA; text-align: center;">'
                    '⚠️ All selections must win for a payout'
                    '</div>'
                    '</div>',
                    unsafe_allow_html=True,
                )

        # --- Odds Converter ---
        with tab_conv:
            st.caption("Convert between decimal, American, and fractional odds formats.")
            fmt = st.selectbox(
                "Input Format",
                ["Decimal", "American", "Fractional"],
                key="odds_fmt",
            )
            if fmt == "Decimal":
                dec = st.number_input(
                    "Decimal Odds", min_value=1.01, value=2.50, step=0.05,
                    key="conv_dec",
                )
                if st.button("⚡ Convert", key="btn_conv", use_container_width=True):
                    num, den = bet_calc.decimal_to_fractional(dec)
                    american = bet_calc.decimal_to_american(dec)
                    st.markdown(
                        '<div class="calc-result-box">'
                        '<div class="calc-grid-3">'
                        f'<div><div class="calc-result-label">Decimal</div><div class="calc-result-value">{dec:.2f}</div></div>'
                        f'<div><div class="calc-result-label">Fractional</div><div class="calc-result-value">{num}/{den}</div></div>'
                        f'<div><div class="calc-result-label">American</div><div class="calc-result-value">{american:+d}</div></div>'
                        '</div>'
                        '</div>',
                        unsafe_allow_html=True,
                    )
            elif fmt == "American":
                amer = st.number_input(
                    "American Odds", value=150, step=10, key="conv_amer",
                )
                if amer == 0:
                    st.warning("American odds cannot be zero.")
                elif st.button("⚡ Convert", key="btn_conv_a", use_container_width=True):
                    dec = bet_calc.american_to_decimal(int(amer))
                    num, den = bet_calc.decimal_to_fractional(dec)
                    st.markdown(
                        '<div class="calc-result-box">'
                        '<div class="calc-grid-3">'
                        f'<div><div class="calc-result-label">Decimal</div><div class="calc-result-value">{dec:.4f}</div></div>'
                        f'<div><div class="calc-result-label">Fractional</div><div class="calc-result-value">{num}/{den}</div></div>'
                        f'<div><div class="calc-result-label">American</div><div class="calc-result-value">{int(amer):+d}</div></div>'
                        '</div>'
                        '</div>',
                        unsafe_allow_html=True,
                    )
            else:  # Fractional
                fc1, fc2 = st.columns(2)
                with fc1:
                    fnum = st.number_input(
                        "Numerator", min_value=1, value=3, step=1,
                        key="conv_fnum",
                    )
                with fc2:
                    fden = st.number_input(
                        "Denominator", min_value=1, value=2, step=1,
                        key="conv_fden",
                    )
                if st.button("⚡ Convert", key="btn_conv_f", use_container_width=True):
                    dec = bet_calc.fractional_to_decimal(int(fnum), int(fden))
                    american = bet_calc.decimal_to_american(dec)
                    st.markdown(
                        '<div class="calc-result-box">'
                        '<div class="calc-grid-3">'
                        f'<div><div class="calc-result-label">Decimal</div><div class="calc-result-value">{dec:.4f}</div></div>'
                        f'<div><div class="calc-result-label">Fractional</div><div class="calc-result-value">{int(fnum)}/{int(fden)}</div></div>'
                        f'<div><div class="calc-result-label">American</div><div class="calc-result-value">{american:+d}</div></div>'
                        '</div>'
                        '</div>',
                        unsafe_allow_html=True,
                    )

        # --- Kelly Criterion ---
        with tab_kelly:
            st.caption("Calculate optimal stake size based on your edge and bankroll.")
            kc1, kc2 = st.columns(2)
            with kc1:
                kc_odds = st.number_input(
                    "Decimal Odds", min_value=1.01, value=2.50, step=0.05,
                    key="kc_odds",
                )
                kc_prob = st.slider(
                    "Estimated Win Probability",
                    0.01, 0.99, 0.50, 0.01,
                    key="kc_prob",
                )
            with kc2:
                kc_bankroll = st.number_input(
                    "Bankroll ($)", min_value=1.0, value=1000.0, step=50.0,
                    key="kc_bankroll",
                )
                kc_frac = st.slider(
                    "Kelly Fraction (1 = full Kelly)",
                    0.1, 1.0, 0.5, 0.1,
                    key="kc_frac",
                )

            if st.button("🧮 Calculate Kelly Stake", key="btn_kelly", use_container_width=True):
                result = bet_calc.kelly_criterion(
                    kc_odds, kc_prob, kc_bankroll, kc_frac
                )
                st.markdown(
                    '<div class="calc-result-box">'
                    '<div class="calc-grid-3">'
                    f'<div><div class="calc-result-label">Your Edge</div><div class="calc-result-value">{result["edge"]:.2%}</div></div>'
                    f'<div><div class="calc-result-label">Kelly %</div><div class="calc-result-value">{result["kelly_fraction"]:.2%}</div></div>'
                    f'<div><div class="calc-result-label">Stake</div><div class="calc-result-value">${result["recommended_stake"]:.2f}</div></div>'
                    '</div>'
                    '</div>',
                    unsafe_allow_html=True,
                )
                if result["edge"] <= 0:
                    st.markdown(
                        '<div style="margin-top: 0.6rem; font-size: 0.72rem; color: #FF6B6B; text-align: center;">'
                        '⚠️ No positive edge detected — Kelly recommends no bet'
                        '</div>',
                        unsafe_allow_html=True,
                    )

        # --- Dutching ---
        with tab_dutch:
            st.caption("Distribute stake across multiple outcomes for equal profit regardless of result.")
            col_dt_stake, col_dt_num = st.columns(2)
            with col_dt_stake:
                dt_stake = st.number_input(
                    "Total Stake ($)", min_value=1.0, value=100.0, step=10.0,
                    key="dt_stake",
                )
            with col_dt_num:
                dt_num = st.number_input(
                    "Number of Selections", min_value=2, max_value=10, value=3, step=1,
                    key="dt_num",
                )

            dt_odds: list[float] = []
            cols_dt = st.columns(min(int(dt_num), 5))
            for i in range(int(dt_num)):
                with cols_dt[i % len(cols_dt)]:
                    val = st.number_input(
                        f"Selection {i + 1} Odds",
                        min_value=1.01, value=3.00, step=0.10,
                        key=f"dt_odds_{i}",
                    )
                    dt_odds.append(val)

            if st.button("⚡ Calculate Dutching", key="btn_dutch", use_container_width=True):
                result = bet_calc.dutching_calculator(dt_stake, dt_odds)
                st.markdown(
                    '<div class="calc-result-box">'
                    '<div class="calc-grid-3">'
                    f'<div><div class="calc-result-label">Equal Payout</div><div class="calc-result-value">${result["equal_payout"]:.2f}</div></div>'
                    f'<div><div class="calc-result-label">Profit</div><div class="calc-result-value">${result["profit"]:.2f}</div></div>'
                    f'<div><div class="calc-result-label">Market Margin</div><div class="calc-result-value">{result["margin"]:.2%}</div></div>'
                    '</div>',
                    unsafe_allow_html=True,
                )
                st.markdown("**Individual Stakes:**")
                stake_cols = st.columns(min(int(dt_num), 3))
                for i, s in enumerate(result["stakes"]):
                    with stake_cols[i % len(stake_cols)]:
                        st.metric(
                            f"Selection {i + 1}",
                            f"${s:.2f}",
                            delta=f"@ {dt_odds[i]:.2f}",
                            delta_color="off",
                        )

# --- Custom Bet & Parlay Calculator ---


def _render_parlay() -> None:
    st.markdown(
        render_section_banner(
            "Builder",
            "Custom Parlay Builder",
            "Assemble multi-leg slips and inspect payout profiles in real time.",
        ),
        unsafe_allow_html=True,
    )

    parlay_calc = BetCalculator()
    legs = st.session_state["parlay_legs"]

    # --- Running Parlay Summary (always visible when legs exist) ---
    if legs:
        odds_list = [lg["decimal_odds"] for lg in legs]
        combined = 1.0
        for o in odds_list:
            combined *= o
        combined = round(combined, 4)
        summary_stake = st.session_state.get("parlay_stake", 10.0)
        st.markdown(
            render_parlay_summary(len(legs), combined, summary_stake),
            unsafe_allow_html=True,
        )

    # --- Display legs with remove buttons ---
    legs = st.session_state["parlay_legs"]

    if not legs:
        st.markdown(
            '<div class="empty-state">'
            '<div class="empty-icon">\U0001f3af</div>'
            '<div class="empty-text">No selections added yet.<br>'
            'Build your parlay by adding picks below.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<span style='font-size:0.78rem;color:#8899AA;"
            "font-weight:700;text-transform:uppercase;"
            "letter-spacing:0.15em;'>Selected Legs</span>",
            unsafe_allow_html=True,
        )

        # Render each leg with a remove button
        for i, lg in enumerate(legs):
            leg_col, rm_col = st.columns([8, 1])
            with leg_col:
                prob = 1.0 / lg["decimal_odds"]
                st.markdown(
                    render_parlay_leg(
                        i + 1,
                        lg["label"],
                        lg["decimal_odds"],
                        prob,
                    ),
                    unsafe_allow_html=True,
                )
            with rm_col:
                if st.button(
                    "\u2716",
                    key=f"rm_leg_{i}",
                    help=f"Remove {lg['label']}",
                ):
                    st.session_state["parlay_legs"].pop(i)
                    st.rerun()

        # --- Clear all button ---
        if st.button(
            "\U0001f5d1\ufe0f Clear All Picks",
            key="btn_clear_parlay",
        ):
            st.session_state["parlay_legs"] = []
            st.rerun()

    # --- Extend your parlay (Add a leg) ---
    st.markdown(
        render_calculator_card(
            "➕",
            "Add a Leg",
            "Extend your parlay by adding another selection"
        ),
        unsafe_allow_html=True,
    )
    pc1, pc2 = st.columns([3, 3])
    with pc1:
        parlay_label = st.text_input(
            "Selection (e.g. Arsenal ML, Over 2.5 Goals)",
            key="parlay_label",
            placeholder="Selection Name (e.g., Liverpool ML)",
        )
    with pc2:
        parlay_odds_fmt = st.selectbox(
            "Odds format",
            ["Decimal", "American", "Fractional"],
            key="parlay_odds_fmt",
        )

    if parlay_odds_fmt == "Decimal":
        parlay_dec = st.number_input(
            "Decimal Odds", min_value=1.01, value=2.00, step=0.05,
            key="parlay_dec",
        )
    elif parlay_odds_fmt == "American":
        parlay_amer = st.number_input(
            "American Odds", value=150, step=10,
            key="parlay_amer",
        )
        parlay_dec = (
            parlay_calc.american_to_decimal(int(parlay_amer))
            if parlay_amer != 0
            else 2.0
        )
    else:
        pf1, pf2 = st.columns(2)
        with pf1:
            parlay_num = st.number_input(
                "Numerator", min_value=1, value=3, step=1,
                key="parlay_fnum",
            )
        with pf2:
            parlay_den = st.number_input(
                "Denominator", min_value=1, value=2, step=1,
                key="parlay_fden",
            )
        parlay_dec = parlay_calc.fractional_to_decimal(
            int(parlay_num), int(parlay_den)
        )

    implied = 1.0 / parlay_dec if parlay_dec > 0 else 0
    st.markdown(
        f"**Odds:** `{parlay_dec:.4f}` · "
        f"**Implied probability:** `{implied:.1%}`"
    )

    if st.button("➕ Add Leg to Parlay", key="btn_add_parlay_leg", use_container_width=True):
        label = parlay_label.strip() or f"Leg {len(legs) + 1}"
        if parlay_dec > 1.0:
            st.session_state["parlay_legs"].append(
                {
                    "label": label,
                    "decimal_odds": round(parlay_dec, 4),
                }
            )
            st.success(f"Added: **{label}** @ {parlay_dec:.4f}")
        else:
            st.error("Odds must be greater than 1.0.")
    st.markdown('</div>', unsafe_allow_html=True)

    # --- Calculation options (only show when legs exist) ---
    if legs:
        st.markdown(
            render_calculator_card(
                "💰",
                "Calculate Payout",
                "Choose your bet type and calculate potential returns"
            ),
            unsafe_allow_html=True,
        )

        parlay_mode = st.radio(
            "Bet type",
            ["Straight Parlay", "Round-Robin", "Singles"],
            horizontal=True,
            key="parlay_mode",
        )

        parlay_stake = st.number_input(
            "Stake ($)", min_value=0.0, value=10.0, step=5.0,
            key="parlay_stake",
        )

        odds_list = [lg["decimal_odds"] for lg in legs]

        if parlay_mode == "Straight Parlay":
            if st.button("💸 Calculate Parlay", key="btn_calc_parlay", use_container_width=True):
                result = parlay_calc.calculate_accumulator(parlay_stake, odds_list)
                # Payout display box
                st.markdown(
                    '<div class="calc-result-box">'
                    '<div class="calc-grid-3">'
                    f'<div><div class="calc-result-label">Combined Odds</div><div class="calc-result-value">{result["combined_odds"]:.2f}x</div></div>'
                    f'<div><div class="calc-result-label">Total Payout</div><div class="calc-result-value">${result["payout"]:.2f}</div></div>'
                    f'<div><div class="calc-result-label">Profit</div><div class="calc-result-value">${result["profit"]:.2f}</div></div>'
                    '</div>'
                    '<div style="margin-top: 0.6rem; font-size: 0.72rem; color: #8899AA; text-align: center;">'
                    f'⚠️ All {len(legs)} legs must win for a payout · Implied probability: {result["implied_probability"]:.1%}'
                    '</div>'
                    '</div>',
                    unsafe_allow_html=True,
                )

        elif parlay_mode == "Round-Robin":
            max_combo = len(legs)
            combo_size = st.slider(
                "Legs per combo",
                min_value=2,
                max_value=max(max_combo, 2),
                value=min(2, max_combo),
                key="rr_combo_size",
            )
            if combo_size > len(legs):
                st.warning("Combo size cannot exceed the number of legs.")
            elif st.button("💸 Calculate Round-Robin", key="btn_calc_rr", use_container_width=True):
                result = parlay_calc.calculate_round_robin(
                    parlay_stake, odds_list, combo_size
                )
                # Payout display box
                st.markdown(
                    '<div class="calc-result-box">'
                    '<div class="calc-grid-3">'
                    f'<div><div class="calc-result-label">Parlays</div><div class="calc-result-value">{result["num_combos"]}</div></div>'
                    f'<div><div class="calc-result-label">Total Payout</div><div class="calc-result-value">${result["total_payout_all_win"]:.2f}</div></div>'
                    f'<div><div class="calc-result-label">Profit</div><div class="calc-result-value">${result["total_profit_all_win"]:.2f}</div></div>'
                    '</div>'
                    '<div style="margin-top: 0.6rem; font-size: 0.72rem; color: #8899AA; text-align: center;">'
                    f'Total Staked: ${result["total_staked"]:.2f} · {result["num_combos"]} parlays of {combo_size} legs each'
                    '</div>'
                    '</div>',
                    unsafe_allow_html=True,
                )

                st.markdown("**Individual Parlays:**")
                for idx, combo in enumerate(result["combos"], 1):
                    combo_labels = [legs[i]["label"] for i in combo["legs"]]
                    with st.expander(
                        f"Parlay {idx}: {' + '.join(combo_labels)}  "
                        f"— Odds {combo['combined_odds']:.4f}  "
                        f"→ ${combo['payout']:.2f}"
                    ):
                        for i in combo["legs"]:
                            st.markdown(
                                f"- **{legs[i]['label']}** @ {legs[i]['decimal_odds']:.2f}"
                            )

        else:  # Singles
            if st.button("💸 Calculate Singles", key="btn_calc_singles", use_container_width=True):
                st.markdown("**Single-Bet Payouts:**")
                total_payout = 0.0
                for i, lg in enumerate(legs):
                    res = parlay_calc.calculate_payout(parlay_stake, lg["decimal_odds"])
                    total_payout += res["payout"]
                    c1, c2, c3 = st.columns([3, 1, 1])
                    c1.markdown(f"**{lg['label']}** @ {lg['decimal_odds']:.2f}")
                    c2.metric("Payout", f"${res['payout']:.2f}")
                    c3.metric("Profit", f"${res['profit']:.2f}")
                total_staked = parlay_stake * len(legs)
                st.markdown(
                    '<div class="calc-result-box" style="margin-top: 1rem;">'
                    '<div class="calc-grid-2">'
                    f'<div><div class="calc-result-label">Total Staked</div><div class="calc-result-value">${total_staked:.2f}</div></div>'
                    f'<div><div class="calc-result-label">Total Payout (all win)</div><div class="calc-result-value">${total_payout:.2f}</div></div>'
                    '</div>'
                    '</div>',
                    unsafe_allow_html=True,
                )
        st.markdown('</div>', unsafe_allow_html=True)

# --- Feedback ---


def _render_feedback() -> None:
    st.markdown(
        render_section_banner(
            "Operator Feedback",
            "User Feedback",
            "Capture platform quality signals, issues, and feature requests.",
        ),
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="alert-card">'
        '<div class="alert-header">'
        '<span class="alert-teams">'
        "\U0001f4ac Share Your Feedback</span>"
        "</div>"
        '<div class="alert-detail">'
        "Help us improve ApexOdds Pro by sharing your thoughts, "
        "reporting bugs, or requesting new features."
        "</div></div>",
        unsafe_allow_html=True,
    )

    with st.form("feedback_form", clear_on_submit=True):
        fb_category = st.selectbox(
            "Feedback Type",
            [
                "General Feedback",
                "Bug Report",
                "Feature Request",
                "Performance Issue",
                "UI / UX",
            ],
            key="fb_category",
        )
        fb_rating = st.slider(
            "Overall Rating (1 = Poor, 5 = Excellent)",
            min_value=1,
            max_value=5,
            value=5,
            key="fb_rating",
        )
        fb_message = st.text_area(
            "Your Message",
            placeholder="Describe your feedback in detail…",
            height=140,
            key="fb_message",
        )
        submitted = st.form_submit_button(
            "\U0001f4e8 Submit Feedback",
            use_container_width=True,
            type="primary",
        )

    if submitted:
        msg = (fb_message or "").strip()
        if not msg:
            st.warning("\u26a0\ufe0f Please enter a message before submitting.")
        else:
            try:
                get_db().save_feedback(fb_category, fb_rating, msg)
                stars = "\u2605" * fb_rating + "\u2606" * (5 - fb_rating)
                st.success(
                    f"\u2705 Thank you for your feedback! "
                    f"({stars}  \u00b7  {fb_category})"
                )
            except Exception as exc:
                logger.error("Failed to save feedback: %s", exc)
                st.error("\u274c Could not save feedback. Please try again.")

    st.markdown("---")
    st.markdown("##### Recent Feedback")
    recent_feedback = get_db().get_feedback(limit=20)
    if not recent_feedback:
        st.markdown(
            '<div class="empty-state">'
            '<div class="empty-icon">\U0001f4ac</div>'
            '<div class="empty-text">No feedback submitted yet.<br>'
            "Be the first to share your thoughts!</div>"
            "</div>",
            unsafe_allow_html=True,
        )
    else:
        star_map = {
            1: "\u2605\u2606\u2606\u2606\u2606",
            2: "\u2605\u2605\u2606\u2606\u2606",
            3: "\u2605\u2605\u2605\u2606\u2606",
            4: "\u2605\u2605\u2605\u2605\u2606",
            5: "\u2605\u2605\u2605\u2605\u2605",
        }
        for entry in recent_feedback:
            rating_val = int(entry.get("rating", 1))
            stars_display = star_map.get(rating_val, "\u2605\u2606\u2606\u2606\u2606")
            raw_ts = entry.get("submitted_at") or ""
            try:
                submitted_at = _dt.fromisoformat(raw_ts).strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                submitted_at = raw_ts[:19].replace("T", " ") if raw_ts else "—"
            st.markdown(
                f'<div class="alert-card" style="margin-bottom:0.5rem;">'
                f'<div class="alert-header">'
                f'<span class="alert-teams">{entry["category"]}</span>'
                f'<span style="color:#FFD700;font-size:1rem;margin-left:0.5rem;">'
                f"{stars_display}</span>"
                f'<span style="color:#8899AA;font-size:0.75rem;margin-left:auto;">'
                f"{submitted_at} UTC</span>"
                f"</div>"
                f'<div class="alert-detail">{entry["message"]}</div>'
                f"</div>",
                unsafe_allow_html=True,
            )

# --- Settings ---


def _render_settings() -> None:
    st.markdown(
        render_section_banner(
            "Control Plane",
            "Settings",
            "Manage league filters, refresh flow, and API access controls.",
        ),
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="alert-card">'
        '<div class="alert-header">'
        '<span class="alert-teams">'
        "\u2699\ufe0f Application Settings</span>"
        "</div>"
        '<div class="alert-detail">'
        "Use the <strong>sidebar panel</strong> on the left "
        "to configure leagues, refresh data, and manage your "
        "API key override."
        "</div></div>",
        unsafe_allow_html=True,
    )

    st.markdown("##### League Selection")
    st.info(
        "Open the sidebar (**⚙️ Settings**) to select which "
        "leagues to monitor and to refresh odds data."
    )

    st.markdown("##### API Key")
    st.info(
        "Your API key is session-scoped and stored in memory "
        "only. Paste it in the sidebar **🔑 API Key Override** "
        "field. It is never written to disk or logs."
    )

    st.markdown("##### Subscription")
    st.markdown(
        '<div class="subscription-box">'
        '<div class="sub-header">'
        '<span class="sub-label">Subscription</span>'
        '<span class="sub-tier">ELITE</span>'
        "</div>"
        '<div class="sub-bar">'
        '<div class="sub-bar-fill"></div>'
        "</div>"
        '<div class="sub-days">12 days remaining</div>'
        "</div>",
        unsafe_allow_html=True,
    )



# ── Center Main Pane ──
with col_main:
    active = st.session_state["active_section"]
    if active == "matches":
        _render_matches(odds_df, upcoming_df_base, analyzer)
    elif active == "value":
        _render_value_bets(odds_df, analyzer)
    elif active == "arb":
        _render_arbitrage(odds_df, analyzer)
    elif active == "movement":
        _render_movement(upcoming_df_base)
    elif active == "margins":
        _render_margins(odds_df, analyzer)
    elif active == "calc":
        _render_calculator()
    elif active == "parlay":
        _render_parlay()
    elif active == "feedback":
        _render_feedback()
    elif active == "settings":
        _render_settings()

# ── Right Pane: Persistent Bet Slip ──
with col_slip:
    st.markdown(
        "<span style='font-size:0.7rem;color:#8899AA;"
        "font-weight:700;text-transform:uppercase;"
        "letter-spacing:0.15em;'>Bet Slip Summary</span>",
        unsafe_allow_html=True,
    )

    slip = st.session_state["bet_slip"]
    parlay_legs_list = st.session_state["parlay_legs"]

    has_items = bool(slip) or bool(parlay_legs_list)

    if slip:
        st.markdown("**Bet Builder Selections**")
        for sel in slip:
            st.markdown(
                render_slip_card(
                    match=sel.get("match", ""),
                    outcome=sel.get("outcome", ""),
                    odds=sel["decimal_odds"],
                ),
                unsafe_allow_html=True,
            )

    if parlay_legs_list:
        st.markdown("**Custom Parlay Legs**")
        for lg in parlay_legs_list:
            st.markdown(
                render_slip_card(
                    match="Custom Selection",
                    outcome=lg["label"],
                    odds=lg["decimal_odds"],
                ),
                unsafe_allow_html=True,
            )

    if not has_items:
        st.markdown(
            '<div class="empty-state">'
            '<div class="empty-icon">\U0001f3ab</div>'
            '<div class="empty-text">Your bet slip is empty.<br>'
            'Add selections from Bet Builder or Custom Parlay.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        all_odds = [s["decimal_odds"] for s in slip] + [
            lg["decimal_odds"] for lg in parlay_legs_list
        ]

        # --- Payout hero display ---
        _live_calc = BetCalculator()
        slip_stake = st.session_state.get("slip_pane_stake", 100.0)
        if len(all_odds) == 1:
            _res = _live_calc.calculate_payout(slip_stake, all_odds[0])
        elif len(all_odds) > 1:
            _res = _live_calc.calculate_accumulator(
                slip_stake, all_odds,
            )
        else:
            _res = {"payout": 0.0, "profit": 0.0}

        st.markdown(
            render_payout_hero(_res["payout"], slip_stake),
            unsafe_allow_html=True,
        )

        # --- Stake input ---
        st.markdown(
            "<span style='font-size:0.82rem;font-weight:700;"
            "color:#E8EAED;'>Enter Stake</span>",
            unsafe_allow_html=True,
        )
        slip_stake = st.number_input(
            "Stake ($)",
            min_value=0.0,
            value=100.0,
            step=5.0,
            key="slip_pane_stake",
            label_visibility="collapsed",
        )

        # Quick-add stake buttons (functional Streamlit buttons)
        qs_cols = st.columns(4)
        _quick_keys = ["qs_10", "qs_50", "qs_100", "qs_max"]
        for _col, _amt, _key in zip(qs_cols[:3], STAKE_QUICK_ADD[:3], _quick_keys[:3]):
            with _col:
                if st.button(f"+{_amt}", key=_key, use_container_width=True):
                    st.session_state["slip_pane_stake"] = slip_stake + _amt
                    st.rerun()
        with qs_cols[3]:
            if st.button("MAX", key="qs_max", use_container_width=True):
                st.session_state["slip_pane_stake"] = float(STAKE_QUICK_ADD[-1])
                st.rerun()

        # --- Odds alert (informational) ---
        if parlay_legs_list:
            st.markdown(
                '<div class="odds-alert-box">'
                '<span class="oa-icon">\u26a0\ufe0f</span>'
                '<div class="oa-text">'
                '<span class="oa-label">Odds Alert:</span> '
                "Markets may shift while you are building. "
                "Review odds before placing."
                "</div>"
                "</div>",
                unsafe_allow_html=True,
            )

        # --- Live payout metrics ---
        if len(all_odds) == 1:
            st.metric("Payout", f"${_res['payout']:.2f}")
            st.metric("Profit", f"${_res['profit']:.2f}")
        elif len(all_odds) > 1:
            st.metric(
                "Combined Odds",
                f"{_res['combined_odds']:.4f}",
                help="Product of all selected decimal odds.",
            )
            st.metric("Total Profit", f"${_res['profit']:.2f}")
            st.caption(
                f"{len(all_odds)} selections \u00b7 "
                f"Implied prob: "
                f"{_res['implied_probability']:.2%}"
            )

        # --- Place Parlay / Save to Favorites actions ---
        if st.button(
            "\u26a1 Place Parlay",
            key="btn_place_parlay",
            use_container_width=True,
            type="primary",
        ):
            st.success(
                "\u2705 Parlay placed! (demo mode — no real wager)"
            )
        if st.button(
            "Save to Favorites",
            key="btn_save_fav",
            use_container_width=True,
        ):
            st.info(
                "\u2b50 Parlay saved to favorites! (demo mode)"
            )

        st.markdown("")  # spacer

        if st.button(
            "\U0001f5d1\ufe0f Clear All",
            key="btn_slip_pane_clear",
        ):
            st.session_state["bet_slip"] = []
            st.session_state["parlay_legs"] = []
            st.rerun()

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="app-footer">
        \u26bd ApexOdds Pro \u00b7 Built with
        <span class="footer-accent">Streamlit</span> \u00b7
        Premium Sports Analytics
    </div>
    """,
    unsafe_allow_html=True,
)
