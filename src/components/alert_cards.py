# src/components/alert_cards.py
"""Renders value-bet and arbitrage alert cards."""

from __future__ import annotations


def render_value_card(
    home: str,
    away: str,
    outcome: str,
    bookmaker: str,
    price: float,
    edge: float,
    american_odds: str | None = None,
) -> str:
    """Return HTML for a value-bet alert card.

    Args:
        home:          Home team name.
        away:          Away team name.
        outcome:       Outcome being bet (e.g. ``"Home"``, ``"Over 2.5"``).
        bookmaker:     Name of the bookmaker offering the value price.
        price:         Decimal odds offered by the bookmaker.
        edge:          Calculated edge over the consensus probability (0–1).
        american_odds: Optional pre-formatted American odds string.

    Returns:
        HTML string for ``st.markdown(..., unsafe_allow_html=True)``.
    """
    american_html = (
        f' <span style="font-size:0.7rem;color:var(--primary);">'
        f"({american_odds})</span>"
        if american_odds
        else ""
    )
    implied_prob = 1.0 / price if price > 0 else 0.0
    edge_meter_pct = min(edge / 0.15, 1.0) * 100

    return (
        f'<div class="alert-card">'
        f'<div class="alert-header">'
        f'<span class="alert-teams">\u26bd {home} vs {away}</span>'
        f'<span class="alert-badge badge-value">+{edge:.1%} EDGE</span>'
        f'</div>'
        f'<div class="alert-detail">'
        f'<strong>{outcome}</strong> @ <strong>{price:.2f}</strong>'
        f'{american_html} via {bookmaker}'
        f'</div>'
        f'<div class="vcard-stats">'
        f'<div class="vcard-stat">'
        f'<div class="vcard-stat-label">Bookie Odds</div>'
        f'<div class="vcard-stat-value">{price:.2f}</div>'
        f'</div>'
        f'<div class="vcard-stat">'
        f'<div class="vcard-stat-label">Implied Prob.</div>'
        f'<div class="vcard-stat-value vcard-accent">{implied_prob:.1%}</div>'
        f'</div>'
        f'<div class="vcard-stat">'
        f'<div class="vcard-stat-label">Edge</div>'
        f'<div class="vcard-stat-value vcard-accent">+{edge:.1%}</div>'
        f'</div>'
        f'</div>'
        f'<div class="edge-meter-wrap">'
        f'<div class="edge-meter-label-row">'
        f'<span>Edge Meter</span><span>{edge:.1%} / 15.0%</span>'
        f'</div>'
        f'<div class="edge-meter-track">'
        f'<div class="edge-meter-fill" style="transform:scaleX({edge_meter_pct / 100:.3f});"></div>'
        f'</div>'
        f'</div>'
        f'</div>'
    )


def render_arb_card(
    home: str,
    away: str,
    market: str,
    arb_pct: float,
    best_odds: dict,
) -> str:
    """Return HTML for an arbitrage alert card.

    Args:
        home:     Home team name.
        away:     Away team name.
        market:   Market key (e.g. ``"h2h"``).
        arb_pct:  Guaranteed profit percentage (e.g. ``1.23`` for 1.23 %).
        best_odds: Mapping of outcome label → best available decimal price.

    Returns:
        HTML string for ``st.markdown(..., unsafe_allow_html=True)``.
    """
    odds_parts = " \u00b7 ".join(
        f"{k}: <strong>{v:.2f}</strong>" for k, v in best_odds.items()
    )
    return (
        f'<div class="alert-card arb-card">'
        f'<div class="alert-header">'
        f'<span class="alert-teams">\U0001f504 {home} vs {away}</span>'
        f'<span class="alert-badge badge-arb">\U0001f4b0 {arb_pct:.3f}% PROFIT</span>'
        f'</div>'
        f'<div class="alert-detail">'
        f'Market: <strong>{market}</strong><br>{odds_parts}'
        f'</div>'
        f'</div>'
    )
