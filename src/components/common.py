# src/components/common.py
"""Shared render helpers: section banner, count badge, CSV download, Plotly theme."""

from __future__ import annotations

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Plotly dark theme — updated to match new design tokens
# ---------------------------------------------------------------------------

DARK_THEME: dict = {
    "paper_bgcolor": "#0D1117",
    "plot_bgcolor":  "#0D1117",
    "font_color":    "#8B95A6",
    "gridcolor":     "rgba(255,255,255,0.05)",
    "colorway": [
        "#1A6FFF",
        "#00D68F",
        "#FF3B5C",
        "#F5A623",
        "#7DD3FC",
    ],
}


def _apply_dark_theme(fig) -> None:
    """Apply the sportsbook dark theme to a Plotly figure in-place."""
    fig.update_layout(
        paper_bgcolor=DARK_THEME["paper_bgcolor"],
        plot_bgcolor=DARK_THEME["plot_bgcolor"],
        font_color=DARK_THEME["font_color"],
        font_family="DM Sans, sans-serif",
        colorway=DARK_THEME["colorway"],
        title_font_size=13,
        title_font_color="#EAEDF3",
        legend_bgcolor="rgba(0,0,0,0)",
        legend_font_color="#8B95A6",
    )
    fig.update_xaxes(
        gridcolor=DARK_THEME["gridcolor"],
        zerolinecolor=DARK_THEME["gridcolor"],
        title_font_color="#8B95A6",
        tickfont_color="#8B95A6",
    )
    fig.update_yaxes(
        gridcolor=DARK_THEME["gridcolor"],
        zerolinecolor=DARK_THEME["gridcolor"],
        title_font_color="#8B95A6",
        tickfont_color="#8B95A6",
    )


# ---------------------------------------------------------------------------
# Section banner
# ---------------------------------------------------------------------------


def render_section_banner(kicker: str, title: str, subtitle: str) -> str:
    """Return HTML for a left-bordered section header banner.

    Args:
        kicker:   Small uppercase category label.
        title:    Primary section title (rendered in Barlow Condensed).
        subtitle: Supporting description line.

    Returns:
        HTML string for ``st.markdown(..., unsafe_allow_html=True)``.
    """
    return (
        '<div class="section-banner">'
        f'<div class="section-kicker">{kicker}</div>'
        f'<h3 class="section-title">{title}</h3>'
        f'<div class="section-subtitle">{subtitle}</div>'
        '</div>'
    )


# ---------------------------------------------------------------------------
# Count badge
# ---------------------------------------------------------------------------


def render_count_badge(count: int) -> str:
    """Return HTML for a small filled count badge pill.

    Args:
        count: Integer to display inside the badge.

    Returns:
        Inline HTML ``<span>`` string.
    """
    return f'<span class="count-badge">{count}</span>'


# ---------------------------------------------------------------------------
# CSV download
# ---------------------------------------------------------------------------


def render_csv_download(
    df: pd.DataFrame,
    filename: str,
    label: str = "Export CSV",
) -> None:
    """Render a Streamlit CSV download button for *df*.

    Args:
        df:       DataFrame to export.
        filename: Suggested download file name.
        label:    Button label text.
    """
    st.download_button(label, df.to_csv(index=False), filename, "text/csv")
