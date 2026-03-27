# src/sections/value_bets.py
"""Value Bets section — edge scanner with histogram and card list."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from src.analyzer import OddsAnalyzer
from src.bet_calculator import BetCalculator
from src.components.alert_cards import render_value_card
from src.components.common import (
    _apply_dark_theme,
    render_count_badge,
    render_csv_download,
    render_section_banner,
)
from src.config import DEFAULT_EDGE_THRESHOLD, SHARP_BOOKMAKERS

# ---------------------------------------------------------------------------
# Hot Bets feed
# ---------------------------------------------------------------------------

def _render_hot_bets(value_df: pd.DataFrame) -> None:
    """Render the top-5 value bets as a horizontal pill strip."""
    top5 = value_df.nlargest(5, "edge")
    if top5.empty:
        return

    pills_html = ""
    for _, row in top5.iterrows():
        team = row.get("home_team", "") or row.get("away_team", "")
        outcome = row.get("outcome_name", "")
        edge_pct = float(row.get("edge", 0)) * 100
        price = float(row.get("outcome_price", 0))
        pills_html += (
            f'<div style="'
            f'background:var(--bg-raised);'
            f'border-left:3px solid var(--accent-green);'
            f'border-radius:8px;'
            f'padding:0.4rem 0.8rem;'
            f'white-space:nowrap;'
            f'font-size:0.74rem;'
            f'font-family:\'DM Sans\',sans-serif;'
            f'">'
            f'<span style="color:var(--text-secondary);font-weight:600;">{team}</span>'
            f'<span style="color:var(--text-muted);margin:0 0.3rem;">·</span>'
            f'<span style="color:var(--text-primary);">{outcome}</span>'
            f'<span style="color:var(--text-muted);margin:0 0.3rem;">·</span>'
            f'<span style="color:var(--accent-green);font-weight:700;">{edge_pct:.1f}%</span>'
            f'<span style="color:var(--text-muted);margin:0 0.3rem;">·</span>'
            f'<span style="color:var(--accent-gold);font-family:\'Barlow Condensed\',sans-serif;'
            f'font-size:0.9rem;font-weight:700;">{price:.2f}</span>'
            f'</div>'
        )

    st.markdown(
        '<span style="font-size:0.69rem;color:var(--text-muted);font-weight:700;'
        'text-transform:uppercase;letter-spacing:0.12em;">🔥 Hot Bets Right Now</span>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div style="display:flex;gap:0.5rem;overflow-x:auto;'
        f'padding-bottom:0.4rem;margin-bottom:0.8rem;">'
        f'{pills_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Section entry point
# ---------------------------------------------------------------------------

def render(
    *,
    odds_df: pd.DataFrame,
    analyzer: OddsAnalyzer,
) -> None:
    """Render the Value Bets section.

    Args:
        odds_df:  Latest odds DataFrame.
        analyzer: :class:`OddsAnalyzer` instance.
    """
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
        return

    vb_filter = st.radio(
        "Filter",
        ["All Markets", "High Edge (>10%)", "New"],
        horizontal=True,
        key="vb_filter",
        label_visibility="collapsed",
    )
    threshold = st.slider(
        "Minimum edge threshold",
        0.01, 0.20, DEFAULT_EDGE_THRESHOLD, 0.01,
        key="value_threshold",
    )
    value_df = analyzer.find_value_bets(
        odds_df, sharp_bookmakers=SHARP_BOOKMAKERS, threshold=threshold
    )

    # Apply quick filter
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
        return

    # ── Hot Bets pill strip ───────────────────────────────────────────────
    _render_hot_bets(value_df)

    # Header row: count badge + CSV export
    badge_col, dl_col = st.columns([3, 1])
    with badge_col:
        st.markdown(
            render_count_badge(len(value_df)) + " Value Bets",
            unsafe_allow_html=True,
        )
    with dl_col:
        render_csv_download(value_df, "value_bets.csv", "\U0001f4e5 Export CSV")

    # Edge distribution histogram
    fig_edge = px.histogram(
        value_df,
        x="edge",
        nbins=10,
        title="Edge Distribution",
        labels={"edge": "Edge (probability units)"},
        color_discrete_sequence=["#00D68F"],
    )
    fig_edge.update_layout(bargap=0.08, showlegend=False, height=300)
    _apply_dark_theme(fig_edge)
    st.plotly_chart(fig_edge, use_container_width=True, config={"displayModeBar": False})

    # Value bet cards — single BetCalculator instance reused for all rows
    _bet_calc = BetCalculator()
    for _, vrow in value_df.iterrows():
        price = float(vrow.get("outcome_price", 0))
        try:
            american = _bet_calc.decimal_to_american(price)
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
