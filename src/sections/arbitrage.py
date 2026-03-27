# src/sections/arbitrage.py
"""Arbitrage section — cross-bookmaker risk-free opportunity scanner."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.analyzer import OddsAnalyzer
from src.components.alert_cards import render_arb_card
from src.components.common import (
    render_count_badge,
    render_csv_download,
    render_section_banner,
)


def render(
    *,
    odds_df: pd.DataFrame,
    analyzer: OddsAnalyzer,
) -> None:
    """Render the Arbitrage section.

    Args:
        odds_df:  Latest odds DataFrame.
        analyzer: :class:`OddsAnalyzer` instance.
    """
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
        return

    arb_df = analyzer.find_arbitrage(odds_df)

    if arb_df.empty:
        st.success("No arbitrage opportunities found in current data.")
        return

    arb_badge_col, arb_dl_col = st.columns([3, 1])
    with arb_badge_col:
        st.markdown(
            render_count_badge(len(arb_df)) + " Opportunities",
            unsafe_allow_html=True,
        )
    with arb_dl_col:
        render_csv_download(
            arb_df.drop(columns=["best_odds"], errors="ignore"),
            "arbitrage.csv",
            "\U0001f4e5 Export CSV",
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
