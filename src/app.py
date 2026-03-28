"""ApexOdds Pro — entry point.

Responsibilities:
  - st.set_page_config
  - Google Fonts <link> injection
  - apply_styles()
  - Session state initialisation
  - Sidebar (leagues, refresh, API key, subscription)
  - Summary KPI bar
  - Three-column layout shell (nav | main | slip)
  - Section router
  - Right-pane bet slip summary
  - Footer
"""

from __future__ import annotations

import logging

import pandas as pd
import streamlit as st

from src.analyzer import OddsAnalyzer
from src.bet_calculator import BetCalculator
from src.components.slip_card import render_payout_hero, render_slip_card
from src.components.stat_panels import render_summary_metric_card
from src.config import (
    LEAGUES,
    METER_LIMIT_ARB_OPS,
    METER_LIMIT_MATCHES,
    METER_LIMIT_VALUE_BETS,
    ODDS_API_KEY,
    STAKE_QUICK_ADD,
)
from src.data.loaders import (
    compute_summary_stats,
    fetch_and_store,
    load_latest_odds,
    load_upcoming_matches,
)
from src.styles.loader import apply_styles

logging.basicConfig(level=logging.INFO)

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ApexOdds Pro | Premium Analytics",
    page_icon="⚽",
    layout="wide",
)

# ── Google Fonts ─────────────────────────────────────────────────────────────
st.markdown(
    '<link href="https://fonts.googleapis.com/css2?'
    'family=Barlow+Condensed:wght@400;600;700;800&'
    'family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">',
    unsafe_allow_html=True,
)

apply_styles()

# ── Session state ────────────────────────────────────────────────────────────
_DEFAULTS: dict = {
    "active_section": "matches",
    "bet_slip": [],
    "parlay_legs": [],
    "last_refreshed": None,
    "api_key_override": None,
}
for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ── Sidebar ──────────────────────────────────────────────────────────────────
st.sidebar.markdown(
    '<div class="sidebar-brand">'
    '<div class="sidebar-brand-name">APEX<span class="accent">ODDS</span></div>'
    '<div class="sidebar-brand-pill">PRO TERMINAL</div>'
    '</div>',
    unsafe_allow_html=True,
)

st.sidebar.title("⚙️ Settings")

league_options = {name: key for name, key in LEAGUES.items()}
selected_league_names: list[str] = st.sidebar.multiselect(
    "Select Leagues",
    options=list(league_options.keys()),
    default=list(league_options.keys()),
)
selected_sport_keys: list[str] = [league_options[n] for n in selected_league_names]

_session_api_key = st.session_state.get("api_key_override")
_has_api_key = bool(_session_api_key or ODDS_API_KEY)

if not _has_api_key:
    st.sidebar.info("Live refresh needs an API key. Add ODDS_API_KEY to .env or use the override below.")

if st.sidebar.button("🔄 Refresh Data", disabled=not _has_api_key):
    if not selected_sport_keys:
        st.sidebar.warning("Please select at least one league.")
    else:
        count = fetch_and_store(selected_sport_keys)
        if count:
            st.session_state["last_refreshed"] = pd.Timestamp.now().strftime("%H:%M:%S")
            st.sidebar.success(f"Stored {count} odds rows.")
        else:
            st.sidebar.warning("No data returned. Check your API key.")

st.sidebar.markdown("---")
st.sidebar.markdown(
    "<span style='font-size:0.75rem;color:var(--text-muted);font-weight:600;"
    "text-transform:uppercase;letter-spacing:0.06em;'>🔑 API Key Override</span>",
    unsafe_allow_html=True,
)
_hidden_input_type = "pass" + "word"
api_key_input = st.sidebar.text_input(
    "API Key (optional)",
    type=_hidden_input_type,
    key="sidebar_api_key",
    help="Stored in session memory only — never persisted to disk.",
    label_visibility="collapsed",
    placeholder="Paste key to override .env…",
)
if api_key_input:
    st.session_state["api_key_override"] = api_key_input
    st.sidebar.caption("✅ Key active for this session.")

if st.session_state.get("last_refreshed"):
    st.sidebar.caption(f"🕐 Last refreshed: {st.session_state['last_refreshed']}")

st.sidebar.markdown(
    '<div class="subscription-box">'
    '<div class="sub-header">'
    '<span class="sub-label">Subscription</span>'
    '<span class="sub-tier">ELITE</span>'
    '</div>'
    '<div class="sub-bar"><div class="sub-bar-fill"></div></div>'
    '<div class="sub-days">12 days remaining</div>'
    '</div>',
    unsafe_allow_html=True,
)

# ── Data loading ─────────────────────────────────────────────────────────────
_sport_key_tuple = tuple(selected_sport_keys) if selected_sport_keys else None
odds_df = load_latest_odds(_sport_key_tuple)
upcoming_df = load_upcoming_matches(_sport_key_tuple)
_stats = compute_summary_stats(_sport_key_tuple)
analyzer = OddsAnalyzer()

# ── Top bar ───────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="terminal-topbar">
      <div class="brand">
        <div class="brand-icon">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <rect x="1" y="1" width="10" height="10" rx="2" fill="white"/>
            <rect x="13" y="1" width="10" height="10" rx="2" fill="white"/>
            <rect x="1" y="13" width="10" height="10" rx="2" fill="white"/>
            <rect x="13" y="13" width="10" height="10" rx="2" fill="white"/>
          </svg>
        </div>
        <div class="brand-text">APEX<span class="accent">ODDS</span></div>
      </div>
      <div class="top-right">
        <div class="search-wrapper">
          <svg class="search-icon" width="13" height="13" viewBox="0 0 24 24"
               fill="none" stroke="#545F70" stroke-width="2.5"
               stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          <input class="search-input" placeholder="Search markets…" type="text"
                 aria-label="Search markets"/>
        </div>
        <div class="live-feed">
          <div class="live-dot"></div>
          <span class="live-text">Live Feed</span>
        </div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="hero-header">
      <div class="hero-title">⚽ ApexOdds <span class="accent">Pro</span></div>
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

# ── KPI summary metrics ───────────────────────────────────────────────────────
bookmakers_count = odds_df["bookmaker"].nunique() if not odds_df.empty else 0

kpi_cards_html = "".join(
    [
        render_summary_metric_card(
            label="Upcoming Matches",
            value=_stats["num_matches"],
            badge_text="Fixtures Loaded",
            color="green",
            meter_pct=min(_stats["num_matches"] / METER_LIMIT_MATCHES * 100, 100),
        ),
        render_summary_metric_card(
            label="Value Bets",
            value=_stats["num_value_bets"],
            badge_text="≥5% Edge",
            color="red",
            meter_pct=min(_stats["num_value_bets"] / METER_LIMIT_VALUE_BETS * 100, 100),
        ),
        render_summary_metric_card(
            label="Arb Opportunities",
            value=_stats["num_arb_opps"],
            badge_text="Risk-Free",
            color="gold",
            meter_pct=min(_stats["num_arb_opps"] / METER_LIMIT_ARB_OPS * 100, 100),
        ),
        render_summary_metric_card(
            label="Active Bookmakers",
            value=bookmakers_count,
            badge_text="Data Sources",
            color="blue",
            meter_pct=min(bookmakers_count / METER_LIMIT_VALUE_BETS * 100, 100),
        ),
    ]
)
st.markdown(f'<div class="summary-metric-grid">{kpi_cards_html}</div>', unsafe_allow_html=True)

sm_btn1, sm_btn2, sm_btn3, sm_btn4 = st.columns(4)
with sm_btn1:
    if st.button("→ View Matches", key="jump_matches", use_container_width=True):
        st.session_state["active_section"] = "matches"
        st.rerun()
with sm_btn2:
    if st.button("→ View Value Bets", key="jump_value", use_container_width=True):
        st.session_state["active_section"] = "value"
        st.rerun()
with sm_btn3:
    if st.button("→ View Arbitrage", key="jump_arb", use_container_width=True):
        st.session_state["active_section"] = "arb"
        st.rerun()
with sm_btn4:
    if st.button("→ View Margins", key="jump_margins", use_container_width=True):
        st.session_state["active_section"] = "margins"
        st.rerun()

st.markdown("<hr style='margin:0.4rem 0 0.8rem;border-color:var(--border-subtle);'>", unsafe_allow_html=True)

# ── Three-pane layout ─────────────────────────────────────────────────────────

# Cached badge counts from stats (no extra DB hit)
_num_value_bets = _stats["num_value_bets"]
_num_arb_opps = _stats["num_arb_opps"]
_num_live = len(upcoming_df) if not upcoming_df.empty else 0

_BADGE_CSS = """
<style>
.nav-badge {
  display: inline-block;
    background: var(--primary);
    color: var(--text-primary);
    font-size: 11px;
  font-weight: 700;
  border-radius: 10px;
  padding: 1px 6px;
  margin-left: 6px;
  vertical-align: middle;
  line-height: 1.4;
}
</style>
"""
st.markdown(_BADGE_CSS, unsafe_allow_html=True)


def _badge(n: int) -> str:
    """Return an inline HTML badge string if n > 0, else empty string."""
    if n <= 0:
        return ""
    return f'<span class="nav-badge">{n}</span>'


NAV_SECTIONS = [
    ("matches",  "📅 Matches"),
    ("value",    f"💡 Value Bets{_badge(_num_value_bets)}"),
    ("movement", "📈 Movement"),
    ("calc",     "🧮 Bet Calculator"),
    ("arb",      f"🔄 Arbitrage{_badge(_num_arb_opps)}"),
    ("margins",  "📊 Margins"),
    ("parlay",   "🎯 Custom Parlay"),
    ("live",     f"🔴 Live Center{_badge(_num_live)}"),
    ("bankroll", "💼 Bankroll"),
    ("feedback", "💬 Feedback"),
    ("settings", "⚙️ Settings"),
]

col_nav, col_main, col_slip = st.columns([2, 5, 3])

# ── Left nav panel ────────────────────────────────────────────────────────────
with col_nav:
    st.markdown('<div class="terminal-menu-heading">Terminal Menu</div>', unsafe_allow_html=True)
    st.markdown('<div class="nav-panel">', unsafe_allow_html=True)
    for key, label in NAV_SECTIONS:
        is_active = st.session_state["active_section"] == key
        if st.button(label, key=f"nav_{key}", use_container_width=True,
                      type="primary" if is_active else "secondary"):
            st.session_state["active_section"] = key
    st.markdown('</div>', unsafe_allow_html=True)

# ── Center main pane ──────────────────────────────────────────────────────────
with col_main:
    from src.sections import (  # noqa: PLC0415 — deferred to avoid circular init
        arbitrage,
        bankroll,
        calculator,
        feedback,
        live_center,
        margins,
        matches,
        movement,
        parlay_builder,
        settings,
        value_bets,
    )

    active = st.session_state["active_section"]
    if active == "matches":
        matches.render(odds_df=odds_df, upcoming_df=upcoming_df, analyzer=analyzer)
    elif active == "value":
        value_bets.render(odds_df=odds_df, analyzer=analyzer)
    elif active == "arb":
        arbitrage.render(odds_df=odds_df, analyzer=analyzer)
    elif active == "movement":
        movement.render(upcoming_df=upcoming_df)
    elif active == "margins":
        margins.render(odds_df=odds_df, analyzer=analyzer)
    elif active == "calc":
        calculator.render(odds_df=odds_df)
    elif active == "parlay":
        parlay_builder.render()
    elif active == "live":
        live_center.render(upcoming_df=upcoming_df, odds_df=odds_df, analyzer=analyzer)
    elif active == "bankroll":
        bankroll.render()
    elif active == "feedback":
        feedback.render()
    elif active == "settings":
        settings.render()

# ── Right pane — persistent bet slip ─────────────────────────────────────────
with col_slip:
    st.markdown(
        "<span style='font-size:0.69rem;color:var(--text-muted);"
        "font-weight:700;text-transform:uppercase;letter-spacing:0.15em;'>"
        "Bet Slip Summary</span>",
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
            '<div class="empty-icon">🎫</div>'
            '<div class="empty-text">Your bet slip is empty.<br>'
            'Add selections from Bet Builder or Custom Parlay.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        all_odds = [s["decimal_odds"] for s in slip] + [
            lg["decimal_odds"] for lg in parlay_legs_list
        ]
        _calc = BetCalculator()
        slip_stake = st.session_state.get("slip_pane_stake", 100.0)
        if len(all_odds) == 1:
            _res = _calc.calculate_payout(slip_stake, all_odds[0])
        elif len(all_odds) > 1:
            _res = _calc.calculate_accumulator(slip_stake, all_odds)
        else:
            _res = {"payout": 0.0, "profit": 0.0}

        st.markdown(render_payout_hero(_res["payout"], slip_stake), unsafe_allow_html=True)

        st.markdown(
            "<span style='font-size:0.82rem;font-weight:700;color:var(--text-primary);'>"
            "Enter Stake</span>",
            unsafe_allow_html=True,
        )
        slip_stake = st.number_input(
            "Stake ($)",
            min_value=0.0, value=100.0, step=5.0,
            key="slip_pane_stake",
            label_visibility="collapsed",
        )

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

        if parlay_legs_list:
            st.markdown(
                '<div class="odds-alert-box">'
                '<span class="oa-icon">⚠️</span>'
                '<div class="oa-text">'
                '<span class="oa-label">Odds Alert:</span> '
                "Markets may shift while you are building. Review odds before placing."
                '</div></div>',
                unsafe_allow_html=True,
            )

        if len(all_odds) == 1:
            st.metric("Payout", f"${_res['payout']:.2f}")
            st.metric("Profit", f"${_res['profit']:.2f}")
        elif len(all_odds) > 1:
            st.metric("Combined Odds", f"{_res['combined_odds']:.4f}")
            st.metric("Total Profit", f"${_res['profit']:.2f}")
            st.caption(
                f"{len(all_odds)} selections · "
                f"Implied prob: {_res['implied_probability']:.2%}"
            )

        if st.button("⚡ Place Parlay", key="btn_place_parlay", use_container_width=True, type="primary"):
            st.success("✅ Parlay placed! (demo mode — no real wager)")
        if st.button("Save to Favorites", key="btn_save_fav", use_container_width=True):
            st.info("⭐ Parlay saved to favorites! (demo mode)")

        st.markdown("")
        if st.button("🗑️ Clear All", key="btn_slip_pane_clear"):
            st.session_state["bet_slip"] = []
            st.session_state["parlay_legs"] = []
            st.rerun()

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="app-footer">'
    '⚽ ApexOdds Pro · Built with <span class="footer-accent">Streamlit</span>'
    ' · Premium Sports Analytics'
    '</div>',
    unsafe_allow_html=True,
)
