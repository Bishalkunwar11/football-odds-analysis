# src/components/parlay.py
"""Renders parlay leg cards and the running parlay summary banner."""

from __future__ import annotations


def render_parlay_leg(
    index: int,
    label: str,
    odds: float,
    implied_prob: float,
    meta: str = "",
) -> str:
    """Return HTML for an enhanced parlay leg card with probability bar.

    Args:
        index:        1-based leg number shown in the numbered badge.
        label:        Human-readable selection label (e.g. ``"Arsenal ML"``).
        odds:         Decimal odds for this leg.
        implied_prob: Implied win probability (0–1 scale).
        meta:         Optional metadata string shown below the label.

    Returns:
        HTML string for ``st.markdown(..., unsafe_allow_html=True)``.
    """
    pct = max(0, min(100, round(implied_prob * 100)))
    meta_html = f'<div class="leg-meta">{meta}</div>' if meta else ""

    return (
        f'<div class="parlay-leg-v2" role="button" tabindex="0">'
        f'<div class="leg-left">'
        f'<div class="leg-num-box">#{index}</div>'
        f'<div class="leg-text">'
        f'<div class="leg-name">{label}</div>'
        f'{meta_html}'
        f'</div>'
        f'</div>'
        f'<div class="leg-right">'
        f'<div class="prob-section">'
        f'<div class="prob-label">Implied Prob.</div>'
        f'<div class="prob-value">{implied_prob:.1%}</div>'
        f'<div class="prob-bar">'
        f'<div class="prob-fill" style="width:{pct}%"></div>'
        f'</div>'
        f'</div>'
        f'<div class="odds-badge">{odds:.2f}</div>'
        f'</div>'
        f'</div>'
    )


def render_parlay_summary(
    num_legs: int,
    combined_odds: float,
    stake: float,
) -> str:
    """Return HTML for a running parlay summary banner.

    Args:
        num_legs:      Total number of legs currently in the parlay.
        combined_odds: Product of all leg odds (pre-computed by caller).
        stake:         Stake amount in dollars used to estimate payout.

    Returns:
        HTML string for ``st.markdown(..., unsafe_allow_html=True)``.
    """
    payout = stake * combined_odds if combined_odds > 0 else 0.0
    profit = payout - stake

    return (
        f'<div class="parlay-summary-v2">'
        f'<div class="ps2-tag">Live Summary</div>'
        f'<div class="ps2-title">\u2b50 Pro Parlay Builder</div>'
        f'<div class="ps2-stats">'
        f'<div class="ps2-stat">'
        f'<div class="ps2-label">Legs</div>'
        f'<div class="ps2-value">{num_legs}</div>'
        f'</div>'
        f'<div class="ps2-stat">'
        f'<div class="ps2-label">Combined Odds</div>'
        f'<div class="ps2-value gold">{combined_odds:.2f}x</div>'
        f'</div>'
        f'<div class="ps2-stat">'
        f'<div class="ps2-label">Total Payout</div>'
        f'<div class="ps2-value green">${payout:,.2f}</div>'
        f'</div>'
        f'<div class="ps2-stat">'
        f'<div class="ps2-label">Net Profit</div>'
        f'<div class="ps2-value">${profit:,.2f}</div>'
        f'</div>'
        f'</div>'
        f'</div>'
    )
