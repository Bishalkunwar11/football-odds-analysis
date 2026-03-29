# src/sections/matches.py
"""Matches section — upcoming fixtures grid with odds comparison."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.analyzer import OddsAnalyzer
from src.components.common import _apply_dark_theme, render_count_badge, render_section_banner
from src.components.match_card import render_featured_live_card, render_match_card_header, render_odds_button_label
from src.components.odds_ladder import render_odds_ladder
from src.data.loaders import compute_best_edge_map, get_db


# ---------------------------------------------------------------------------
# Bet slip helpers
# ---------------------------------------------------------------------------

def _add_to_slip(match: str, outcome: str, decimal_odds: float) -> None:
    """Add an odds selection to the bet slip and open the drawer."""
    slip: list[dict] = st.session_state.setdefault("bet_slip", [])
    # Avoid exact duplicates
    for existing in slip:
        if existing.get("match") == match and existing.get("outcome") == outcome:
            return
    slip.append({"match": match, "outcome": outcome, "decimal_odds": decimal_odds})
    st.session_state["slip_visible"] = True


# ---------------------------------------------------------------------------
# Main render
# ---------------------------------------------------------------------------

def render(
    *,
    odds_df: pd.DataFrame,
    upcoming_df: pd.DataFrame,
    analyzer: OddsAnalyzer,
) -> None:
    st.markdown(
        render_section_banner(
            "Live Dashboard",
            "Upcoming Fixtures",
            "Monitor fixtures and compare best available prices in one grid.",
        ),
        unsafe_allow_html=True,
    )

    # Featured live card
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
            '<div class="empty-icon">📅</div>'
            '<div class="empty-text">No upcoming matches in the database.<br>'
            'Use <b>Refresh Data</b> in the sidebar to fetch odds.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    # Search filter
    team_search = st.text_input(
        "🔍 Search teams…",
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

    # Build best-odds + price_direction lookup per match (h2h market)
    best_odds_map: dict[str, dict[str, float]] = {}
    direction_map: dict[str, dict[str, str]] = {}  # match_id → outcome → direction

    if not odds_df.empty:
        h2h = odds_df[odds_df["market"] == "h2h"].copy()
        if not h2h.empty:
            # Best price per (match_id, outcome)
            best = (
                h2h.groupby(["match_id", "outcome_name"])["outcome_price"]
                .max()
                .unstack("outcome_name")
            )
            for mid in best.index:
                row_dict = best.loc[mid].dropna().to_dict()
                if row_dict:
                    best_odds_map[mid] = row_dict

            # Direction: use the direction of the row with the highest price per match+outcome
            if "price_direction" in h2h.columns:
                idx_best = h2h.groupby(["match_id", "outcome_name"])["outcome_price"].idxmax()
                best_rows = h2h.loc[idx_best.dropna()]
                for _, r in best_rows.iterrows():
                    mid = str(r["match_id"])
                    out = str(r["outcome_name"])
                    direction_map.setdefault(mid, {})[out] = str(r.get("price_direction") or "stable")

    # PRO EDGE per match
    selected_keys = tuple(sorted(set(filtered_df.get("sport_key", pd.Series(dtype=str)).tolist())))
    best_edge_map = compute_best_edge_map(selected_keys or None)

    # Render each match card
    for _, row in filtered_df.iterrows():
        m_id    = str(row.get("match_id", ""))
        home    = str(row["home_team"])
        away    = str(row["away_team"])
        league  = str(row.get("league", ""))
        kickoff = str(row["commence_time"])
        edge    = best_edge_map.get(m_id)
        odds    = best_odds_map.get(m_id)
        dirs    = direction_map.get(m_id, {})

        # Card header (HTML)
        st.markdown(
            render_match_card_header(home, away, league, kickoff, edge),
            unsafe_allow_html=True,
        )

        # Odds buttons row — interactive Streamlit buttons
        if odds:
            n = len(odds)
            cols = st.columns(n)
            for col, (outcome, price) in zip(cols, odds.items()):
                direction = dirs.get(outcome, "stable")
                implied   = 1 / price if price > 0 else 0
                btn_label = render_odds_button_label(outcome, price, direction)
                with col:
                    if st.button(
                        btn_label,
                        key=f"odds_{m_id}_{outcome}",
                        use_container_width=True,
                        on_click=_add_to_slip,
                        args=(f"{home} vs {away}", outcome, price),
                    ):
                        pass  # on_click handles state; rerun triggered automatically
                    st.caption(f"Implied: {implied:.0%}")
        else:
            st.caption("No odds available yet.")

        st.markdown("<hr style='margin:0.3rem 0 0.5rem;border-color:var(--border-subtle);'>", unsafe_allow_html=True)

        # Expandable details
        with st.expander("📊 Odds Ladder"):
            st.markdown(render_odds_ladder(m_id, odds_df), unsafe_allow_html=True)

        with st.expander("⏱ Odds Timeline"):
            _render_odds_timeline(m_id)


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

    points: list[tuple[str, float]] = []
    for rec in history:
        if rec.get("market") != "h2h":
            continue
        outcome = str(rec.get("outcome_name", "")).lower()
        if outcome in ("home", "1") or (
            outcome not in ("draw", "x", "tie", "away", "2")
            and history.index(rec) == 0
        ):
            ts    = rec.get("fetched_at") or rec.get("timestamp") or ""
            price = float(rec.get("outcome_price", 0) or 0)
            if price > 1.0 and ts:
                points.append((str(ts), price))

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

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[t[0] for t in unique],
        y=[t[1] for t in unique],
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
