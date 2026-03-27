# src/sections/settings.py
"""Settings section — links to sidebar controls and displays subscription status."""

from __future__ import annotations

import streamlit as st

from src.components.common import render_section_banner


def render() -> None:
    """Render the Settings section."""
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
        '<span class="alert-teams">\u2699\ufe0f Application Settings</span>'
        '</div>'
        '<div class="alert-detail">'
        "Use the <strong>sidebar panel</strong> on the left to configure "
        "leagues, refresh data, and manage your API key override."
        '</div></div>',
        unsafe_allow_html=True,
    )

    st.markdown("##### League Selection")
    st.info(
        "Open the sidebar (\u2699\ufe0f Settings) to select which leagues to "
        "monitor and to refresh odds data."
    )

    st.markdown("##### API Key")
    st.info(
        "Your API key is session-scoped and stored in memory only. "
        "Paste it in the sidebar \U0001f511 **API Key Override** field. "
        "It is never written to disk or logs."
    )

    st.markdown("##### Subscription")
    st.markdown(
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
