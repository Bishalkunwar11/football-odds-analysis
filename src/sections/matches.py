# src/sections/matches.py
"""Matches section — upcoming fixtures grid with odds comparison."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.analyzer import OddsAnalyzer
from src.components.common import _apply_dark_theme, render_count_badge, render_section_banner
from src.components.match_card import render_featured_live_card, render_match_card
from src.components.odds_ladder import render_odds_ladder
from src.data.loaders import compute_best_edge_map, get_db


def render(
    *,
    odds_df: pd.DataFrame,
    upcoming_df: pd.DataFrame,
    analyzer: OddsAnalyzer,
) -> None:
    """Render the Matches section.

    Args:
        odds_df:    Latest odds DataFrame (all bookmakers, all markets).
        upcoming_df: Upcoming matches DataFrame.
        analyzer:   :class:`OddsAnalyzer` instance for edge computation.
    """
    st.markdown(
        render_section_banner(
            "Live Dashboard",
            "Upcoming Matches",
            "Monitor fixtures and compare best available prices in one grid.",
        ),
        unsafe_allow_html=True,
    )

    # Featured live card — demo showcase using the first available match.
    # Real live-score data requires a dedicated live-scores API endpoint.
    if not upcoming_df.empty and len(upcoming_df) >= 2:
        first = upcoming_df.iloc[0]
        st.markdown(
            render_featured_live_card(
                home=first["home_team"],
                away=first["away_team"],
                home_score=2,
                away_score=1,
                minute="74'",
                league=first.get("league", "Premier League"),
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
        return

    # Team search filter
    team_search = st.text_input(
        "\U0001f50d Search teams\u2026",
        key="match_search",
        placeholder="e.g. Arsenal, Real Madrid",
    )
    filtered_df = upcoming_df
    if team_search.strip():
        mask = (
            upcoming_df["home_team"].str.contains(team_search, case=False, na=False)
            | upcoming_df["away_team"].str.contains(team_search, case=False, na=False)
        )
        filtered_df = upcoming_df[mask]

    if filtered_df.empty:
        st.info(f'No matches found for "{team_search}".')
        return

    st.markdown(
        render_count_badge(len(filtered_df)) + " Matches",
        unsafe_allow_html=True,
    )

    # Build best-odds lookup per match (h2h market only)
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
    selected_keys = tuple(sorted(set(filtered_df.get("sport_key", pd.Series(dtype=str)).tolist())))
    best_edge_map = compute_best_edge_map(selected_keys or None)

    st.markdown('<div class="match-grid">', unsafe_allow_html=True)
    for idx, (_, row) in enumerate(filtered_df.iterrows()):
        m_id = str(row.get("match_id", ""))
        card_html = render_match_card(
            home=row["home_team"],
            away=row["away_team"],
            league=row.get("league", ""),
            kickoff=str(row["commence_time"]),
            odds=best_odds_map.get(m_id),
            edge_pct=best_edge_map.get(m_id),
        )
        st.markdown(f'<div class="match-grid-item">{card_html}</div>', unsafe_allow_html=True)

        # ── Odds Ladder expander ─────────────────────────────────────
        with st.expander("📊 Odds Ladder"):
            st.markdown(
                render_odds_ladder(m_id, odds_df),
                unsafe_allow_html=True,
            )

        # ── Odds Timeline sparkline expander ─────────────────────────
        with st.expander("⏱ Odds Timeline"):
            _render_odds_timeline(m_id)
    st.markdown('</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Odds Timeline sparkline helper
# ---------------------------------------------------------------------------

def _render_odds_timeline(match_id: str) -> None:
    """Render a compact Plotly sparkline of home-win price history."""
    try:
        db = get_db()
        history = db.get_odds_history(match_id)
    except Exception:  # noqa: BLE001
        history = []

    # Filter to h2h home-win rows from a consistent bookmaker
    points: list[tuple[str, float]] = []
    for rec in history:
        if rec.get("market") != "h2h":
            continue
        outcome = str(rec.get("outcome_name", "")).lower()
        # Accept home-team outcomes (not draw, not away)
        if outcome in ("home", "1") or (
            outcome not in ("draw", "x", "tie", "away", "2")
            and history.index(rec) == 0
        ):
            ts = rec.get("fetched_at") or rec.get("timestamp") or ""
            price = float(rec.get("outcome_price", 0) or 0)
            if price > 1.0 and ts:
                points.append((str(ts), price))

    # Deduplicate and sort by timestamp
    seen: set[str] = set()
    unique: list[tuple[str, float]] = []
    for ts, price in points:
        if ts not in seen:
            seen.add(ts)
            unique.append((ts, price))
    unique.sort(key=lambda t: t[0])

    if len(unique) < 2:
        st.caption("Collecting data… (need ≥ 2 snapshots)")
        return

    x_vals = [t[0] for t in unique]
    y_vals = [t[1] for t in unique]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x_vals,
        y=y_vals,
        fill="tozeroy",
        fillcolor="rgba(26,111,255,0.20)",
        line=dict(color="#1A6FFF", width=1.5),
        mode="lines",
        hovertemplate="%{x}<br>%{y:.2f}<extra></extra>",
    ))
    fig.update_layout(
        height=300,
        margin=dict(l=0, r=0, t=4, b=0),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    _apply_dark_theme(fig)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
