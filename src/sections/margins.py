# src/sections/margins.py
"""Margins section — bookmaker overround efficiency analysis."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from src.analyzer import OddsAnalyzer
from src.components.common import _apply_dark_theme, render_section_banner


def render(
    *,
    odds_df: pd.DataFrame,
    analyzer: OddsAnalyzer,
) -> None:
    """Render the Bookmaker Margin Analysis section.

    Args:
        odds_df:  Latest odds DataFrame.
        analyzer: :class:`OddsAnalyzer` instance.
    """
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
        return

    h2h_df = odds_df[odds_df["market"] == "h2h"]
    if h2h_df.empty:
        st.info("No 1X2 odds data available.")
        return

    margins: list[dict] = []
    for (_, bookmaker), grp in h2h_df.groupby(["match_id", "bookmaker"]):
        prices = grp["outcome_price"].tolist()
        if len(prices) >= 2:  # noqa: PLR2004
            try:
                margin = analyzer.calculate_margin(prices)
                margins.append({"bookmaker": bookmaker, "margin": margin * 100})
            except ValueError:
                continue

    if not margins:
        st.info("Insufficient data to compute margins.")
        return

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
        labels={"bookmaker": "Bookmaker", "margin": "Avg Margin (%)"},
        color="margin",
        color_continuous_scale="RdYlGn_r",
    )
    fig_bar.update_layout(showlegend=False, height=300)
    _apply_dark_theme(fig_bar)
    st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})

    st.markdown("##### Margin Detail Table")
    display_tbl = avg_margin.rename(
        columns={"bookmaker": "Bookmaker", "margin": "Avg Margin (%)"}
    ).copy()
    display_tbl["Avg Margin (%)"] = display_tbl["Avg Margin (%)"].round(3)
    st.dataframe(
        display_tbl,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Avg Margin (%)": st.column_config.NumberColumn(format="%.3f%%")
        },
    )
