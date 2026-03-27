# src/sections/movement.py
"""Odds Movement section — multi-bookmaker price history overlay."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from src.components.common import _apply_dark_theme, render_section_banner
from src.data.loaders import get_db


def render(*, upcoming_df: pd.DataFrame) -> None:
    """Render the Odds Movement section.

    Args:
        upcoming_df: Upcoming matches DataFrame (used to populate the selectbox).
    """
    st.markdown(
        render_section_banner(
            "Market Pulse",
            "Odds Movement",
            "Overlay historical price movement by bookmaker and outcome.",
        ),
        unsafe_allow_html=True,
    )

    if upcoming_df.empty:
        st.markdown(
            '<div class="empty-state">'
            '<div class="empty-icon">\U0001f4c8</div>'
            '<div class="empty-text">No matches in the database.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    match_labels = {
        f"{r['home_team']} vs {r['away_team']}": r["match_id"]
        for _, r in upcoming_df.iterrows()
    }
    selected_label = st.selectbox(
        "Select Match", options=list(match_labels.keys())
    )
    selected_id = match_labels[selected_label]

    db = get_db()
    history = db.get_odds_history(selected_id)
    hist_df = pd.DataFrame(history)

    if hist_df.empty:
        st.info("No historical odds for this match yet.")
        return

    bookmakers = sorted(hist_df["bookmaker"].unique())
    selected_books = st.multiselect(
        "Compare Bookmakers",
        options=bookmakers,
        default=bookmakers[:1],
        help="Select one or more bookmakers to overlay their price movements.",
    )

    if not selected_books:
        st.info("Select at least one bookmaker to display the chart.")
        return

    filtered = hist_df[
        (hist_df["bookmaker"].isin(selected_books)) & (hist_df["market"] == "h2h")
    ]

    if filtered.empty:
        st.info("No h2h odds history for the selected bookmakers.")
        return

    filtered = filtered.assign(
        series=filtered["bookmaker"] + " \u2013 " + filtered["outcome_name"]
    )

    fig = px.line(
        filtered,
        x="timestamp",
        y="outcome_price",
        color="series",
        title=f"Odds Movement \u2013 {', '.join(selected_books)}",
        labels={
            "timestamp": "Time",
            "outcome_price": "Decimal Odds",
            "series": "Bookmaker \u2013 Outcome",
        },
        markers=True,
    )
    fig.update_layout(height=400)
    _apply_dark_theme(fig)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": True})
