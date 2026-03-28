# src/components/slip_card.py
"""Renders bet-slip selection cards and the payout hero widget."""

from __future__ import annotations


def render_slip_card(match: str, outcome: str, odds: float) -> str:
    """Return HTML for a single bet-slip selection card.

    Args:
        match:   Match label shown in small muted text above the outcome.
        outcome: Outcome string displayed prominently.
        odds:    Decimal odds shown in the gold badge on the right.

    Returns:
        HTML string for ``st.markdown(..., unsafe_allow_html=True)``.
    """
    return (
        f'<div class="slip-card" role="button" tabindex="0">'
        f'<div class="slip-info">'
        f'<div class="slip-match">{match}</div>'
        f'<div class="slip-outcome">{outcome}</div>'
        f'</div>'
        f'<div class="slip-odds">{odds:.2f}</div>'
        f'</div>'
    )


def render_payout_hero(payout: float, stake: float) -> str:
    """Return HTML for a large potential-payout display widget.

    Args:
        payout: Total potential payout in dollars (includes stake).
        stake:  Original stake amount.

    Returns:
        HTML string for ``st.markdown(..., unsafe_allow_html=True)``.
    """
    return (
        f'<div class="payout-hero">'
        f'<div class="ph-label">Potential Payout</div>'
        f'<div class="ph-value">${payout:,.2f}</div>'
        f'<div class="ph-note">'
        f'\u2139\ufe0f Includes your ${stake:,.2f} stake'
        f'</div>'
        f'</div>'
    )
