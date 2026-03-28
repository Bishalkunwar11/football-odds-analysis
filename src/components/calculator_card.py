# src/components/calculator_card.py
"""Renders calculator section card headers."""

from __future__ import annotations


def render_calculator_card(icon: str, title: str, subtitle: str) -> str:
    """Return opening HTML for a calculator card.

    The returned HTML opens a ``<div class="calculator-card">`` which must be
    closed by the caller with ``</div>`` after appending Streamlit widgets.

    Args:
        icon:     Emoji icon character.
        title:    Card title text.
        subtitle: Brief description displayed below the title.

    Returns:
        Opening HTML string for ``st.markdown(..., unsafe_allow_html=True)``.
    """
    return (
        f'<div class="calculator-card">'
        f'<div class="calc-card-header">'
        f'<div class="calc-card-icon">{icon}</div>'
        f'<div>'
        f'<div class="calc-card-title">{title}</div>'
        f'<div class="calc-card-subtitle">{subtitle}</div>'
        f'</div>'
        f'</div>'
    )
