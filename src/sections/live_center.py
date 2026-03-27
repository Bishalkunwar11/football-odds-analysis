# src/sections/live_center.py
"""Live Center section — scrolling ticker, live match grid, and full table.

NOTE: Live scores are SIMULATED from upcoming fixture data.
Real live scores require a dedicated live-scores API endpoint
(not provided by The-Odds-API odds feed used by this app).
"""

from __future__ import annotations

import hashlib

import pandas as pd
import streamlit as st

from src.analyzer import OddsAnalyzer
from src.components.common import render_section_banner
from src.components.live_ticker import render_live_ticker
from src.components.match_card import render_featured_live_card

# ---------------------------------------------------------------------------
# Simulation helpers
# ---------------------------------------------------------------------------

def _sim_live(row: pd.Series, idx: int) -> dict:
    """Deterministically generate simulated live state for a match row.

    Uses an MD5 hash of the match_id so values are stable across reruns
    without requiring an actual random seed.

    Returns dict with keys: home, away, league, home_score, away_score,
    minute, is_live, status_label, match_id.
    """
    h = int(
        hashlib.md5(str(row.get("match_id", idx)).encode()).hexdigest()[:6], 16
    )
    home_score = h % 4
    away_score = (h >> 2) % 4
    minute_raw = 1 + (h % 90)
    is_live = (idx % 3) != 0          # ~2/3 of matches shown as live
    status = f"{minute_raw}'" if is_live else "FT"
    status_label = "LIVE" if is_live else "FT"

    return {
        "match_id":   str(row.get("match_id", "")),
        "home":       str(row.get("home_team", "")),
        "away":       str(row.get("away_team", "")),
        "league":     str(row.get("league", "")),
        "home_score": home_score,
        "away_score": away_score,
        "minute":     status,
        "is_live":    is_live,
        "status_label": status_label,
    }


# ---------------------------------------------------------------------------
# Section entry point
# ---------------------------------------------------------------------------

def render(
    *,
    upcoming_df: pd.DataFrame,
    odds_df: pd.DataFrame,
    analyzer: OddsAnalyzer,
) -> None:
    """Render the Live Center section.

    Args:
        upcoming_df: Upcoming matches DataFrame (source for simulated data).
        odds_df:     Latest odds DataFrame (used for live odds display).
        analyzer:    :class:`OddsAnalyzer` instance (reserved for future use).
    """
    st.markdown(
        render_section_banner(
            "Live Center",
            "\U0001f534 Live Matches",
            "Real-time scores & odds — currently showing simulated data.",
        ),
        unsafe_allow_html=True,
    )

    # Simulated-data disclaimer
    st.markdown(
        '<div style="background:rgba(245,166,35,0.07);border:0.5px solid '
        'rgba(245,166,35,0.30);border-radius:8px;padding:0.6rem 0.85rem;'
        'font-size:0.74rem;color:var(--text-secondary);margin-bottom:0.9rem;">'
        '\u26a0\ufe0f <strong style="color:var(--accent-gold);">Simulated data</strong> '
        '\u2014 Live scores are generated from upcoming fixture data. '
        'Real live scores require a dedicated live-scores API endpoint.'
        '</div>',
        unsafe_allow_html=True,
    )

    if upcoming_df.empty:
        st.markdown(
            '<div class="empty-state">'
            '<div class="empty-icon">\U0001f534</div>'
            '<div class="empty-text">No fixture data available.<br>'
            'Use <b>Refresh Data</b> in the sidebar to fetch matches.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    # Build simulated live records
    live_records: list[dict] = [
        _sim_live(row, idx)
        for idx, (_, row) in enumerate(upcoming_df.iterrows())
    ]

    # ── Scrolling ticker ────────────────────────────────────────────────────
    st.markdown(render_live_ticker(live_records), unsafe_allow_html=True)

    # ── Featured live cards (2-column grid) ─────────────────────────────────
    live_only = [m for m in live_records if m["is_live"]]
    featured = live_only[:6] if live_only else live_records[:6]

    if featured:
        st.markdown(
            "<span style='font-size:0.69rem;color:var(--text-muted);"
            "font-weight:700;text-transform:uppercase;letter-spacing:0.15em;'>"
            "Featured Live</span>",
            unsafe_allow_html=True,
        )
        cols = st.columns(2)
        for idx, m in enumerate(featured):
            with cols[idx % 2]:
                # Live card HTML
                st.markdown(
                    render_featured_live_card(
                        home=m["home"],
                        away=m["away"],
                        home_score=m["home_score"],
                        away_score=m["away_score"],
                        minute=m["minute"],
                        league=m["league"],
                    ),
                    unsafe_allow_html=True,
                )

                # Live odds (best h2h prices for this match)
                live_odds_html = _best_odds_strip(m["match_id"], odds_df)
                if live_odds_html:
                    st.markdown(live_odds_html, unsafe_allow_html=True)

                # BET NOW button
                if st.button(
                    "\u26a1 BET NOW",
                    key=f"live_bet_{m['match_id']}_{idx}",
                    use_container_width=True,
                ):
                    st.success(
                        f"Bet slip opened for {m['home']} vs {m['away']} (demo mode)"
                    )

    # ── View All Live expander ───────────────────────────────────────────────
    with st.expander("\U0001f4cb View All Live Matches"):
        table_data = [
            {
                "Match":   f"{m['home']} vs {m['away']}",
                "League":  m["league"],
                "Score":   f"{m['home_score']} \u2013 {m['away_score']}",
                "Minute":  m["minute"],
                "Status":  m["status_label"],
            }
            for m in live_records
        ]
        table_df = pd.DataFrame(table_data)
        st.dataframe(
            table_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Status": st.column_config.TextColumn("Status"),
            },
        )


# ---------------------------------------------------------------------------
# Helper — best odds strip for a single match
# ---------------------------------------------------------------------------

def _best_odds_strip(match_id: str, odds_df: pd.DataFrame) -> str:
    """Return a compact HTML odds strip for the given match, or empty string."""
    if odds_df.empty or not match_id:
        return ""

    h2h = odds_df[
        (odds_df["match_id"] == match_id) & (odds_df["market"] == "h2h")
    ]
    if h2h.empty:
        return ""

    best = (
        h2h.groupby("outcome_name")["outcome_price"]
        .max()
        .to_dict()
    )
    if not best:
        return ""

    btns = "".join(
        f'<div style="flex:1;background:var(--bg-raised);'
        f'border:0.5px solid var(--border-subtle);border-radius:6px;'
        f'padding:0.3rem 0.2rem;text-align:center;">'
        f'<div style="font-size:0.69rem;color:var(--text-muted);'
        f'text-transform:uppercase;letter-spacing:0.06em;">{label}</div>'
        f'<div style="font-family:\'Barlow Condensed\',sans-serif;'
        f'font-size:0.95rem;font-weight:700;color:var(--accent-gold);">'
        f'{price:.2f}</div>'
        f'</div>'
        for label, price in best.items()
    )
    return (
        f'<div style="display:flex;gap:0.35rem;margin-top:0.4rem;'
        f'margin-bottom:0.3rem;">{btns}</div>'
    )
