"""HTML rendering helpers and Plotly theme utilities for the Streamlit dashboard."""

from __future__ import annotations

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Plotly dark-theme configuration
# ---------------------------------------------------------------------------

_EDGE_METER_MAX: float = 0.15

DARK_THEME: dict = {
    "paper_bgcolor": "#000B14",
    "plot_bgcolor": "#000B14",
    "font_color": "#E7EEF7",
    "gridcolor": "rgba(20, 24, 255, 0.24)",
    "colorway": [
        "#1418FF",
        "#00D68F",
        "#004797",
        "#00F2FF",
        "#FF3B5C",
        "#7DD3FC",
    ],
}


# ---------------------------------------------------------------------------
# Match / odds cards
# ---------------------------------------------------------------------------


def render_match_card(
    home: str,
    away: str,
    league: str,
    kickoff: str,
    odds: dict[str, float] | None = None,
    edge_pct: float | None = None,
) -> str:
    """Return HTML for a single sportsbook-style match card.

    Args:
        home: Home team name.
        away: Away team name.
        league: League / competition label shown in the badge.
        kickoff: ISO kick-off time string displayed on the card.
        odds: Optional mapping of outcome label → best decimal price.
            When provided, an odds-button row is appended below the
            match header. A triangular up/down indicator is shown when
            the price is unusually high or low.
        edge_pct: Optional best edge percentage for this match (0–1 scale).
            When positive, a PRO EDGE badge is shown in the card header.

    Returns:
        An HTML string ready for ``st.markdown(…, unsafe_allow_html=True)``.
    """
    odds_html = ""
    if odds:
        btns = []
        for label, price in odds.items():
            # Odds movement indicator
            movement = ""
            if price > 2.0:
                movement = ' <span class="odds-up">\u25b2</span>'
            elif price < 1.8:
                movement = ' <span class="odds-down">\u25bc</span>'
            btns.append(
                f'<div class="odds-btn">'
                f'<div class="outcome-label">{label}</div>'
                f'<div class="odds-value">{price:.2f}{movement}</div>'
                f'</div>'
            )
        odds_html = f'<div class="odds-row">{"".join(btns)}</div>'
    edge_badge_html = ""
    if edge_pct is not None and edge_pct > 0:
        edge_badge_html = (
            f'<span class="pro-edge-badge">PRO EDGE +{edge_pct:.1%}</span>'
        )
    return (
        f'<div class="match-card">'
        f'<div class="card-top">'
        f'<span class="league-badge">\u26bd {league}</span>'
        f'{edge_badge_html}'
        f'<div class="teams">'
        f'<span class="team-name">{home}</span>'
        f'<span class="vs-badge">VS</span>'
        f'<span class="team-name away">{away}</span>'
        f'</div>'
        f'<div class="kickoff">\U0001f550 {kickoff}</div>'
        f'</div>'
        f'{odds_html}'
        f'</div>'
    )


def render_stat_panel(label: str, value: str) -> str:
    """Return HTML for a small glassmorphism stat panel.

    Args:
        label: Short uppercase label displayed above the value.
        value: Formatted value string (e.g. ``"42"`` or ``"5.3%"``).

    Returns:
        An HTML string ready for ``st.markdown(…, unsafe_allow_html=True)``.
    """
    return (
        f'<div class="stat-panel">'
        f'<div class="stat-label">{label}</div>'
        f'<div class="stat-value">{value}</div>'
        f'</div>'
    )


def render_summary_metric_card(
    label: str,
    value: str | int,
    badge_text: str,
    color: str,
    meter_pct: float,
) -> str:
    """Return HTML for a styled KPI summary card.

    Args:
        label: Short uppercase label displayed above the value.
        value: Primary metric value (e.g. ``42`` or ``"5.3%"``).
        badge_text: Small text shown in a pill badge below the value.
        color: Accent color key — one of ``"green"``, ``"red"``,
            ``"gold"``, or ``"blue"``.
        meter_pct: Progress meter fill 0–100.

    Returns:
        An HTML string ready for ``st.markdown(…, unsafe_allow_html=True)``.
    """
    meter_pct = max(0.0, min(100.0, meter_pct))
    return (
        f'<div class="summary-metric-card smc-{color}">'
        f'<div class="smc-label">{label}</div>'
        f'<div class="smc-value">{value}</div>'
        f'<span class="smc-badge smc-{color}">{badge_text}</span>'
        f'<div class="smc-meter">'
        f'<div class="smc-meter-fill smc-{color}" style="width:{meter_pct:.1f}%"></div>'
        f'</div>'
        f'</div>'
    )


# ---------------------------------------------------------------------------
# Bet slip
# ---------------------------------------------------------------------------


def render_slip_card(match: str, outcome: str, odds: float) -> str:
    """Return HTML for a single bet-slip selection card.

    Args:
        match: Match label shown in small muted text above the outcome.
        outcome: Outcome string displayed prominently (e.g. ``"Arsenal"``,
            ``"Over 2.5"``).
        odds: Decimal odds shown in the gold badge on the right.

    Returns:
        An HTML string ready for ``st.markdown(…, unsafe_allow_html=True)``.
    """
    return (
        f'<div class="slip-card">'
        f'<div class="slip-info">'
        f'<div class="slip-match">{match}</div>'
        f'<div class="slip-outcome">{outcome}</div>'
        f'</div>'
        f'<div class="slip-odds">{odds:.2f}</div>'
        f'</div>'
    )


def render_payout_hero(
    payout: float,
    stake: float,
) -> str:
    """Return HTML for a large payout display widget.

    Shows the potential payout prominently with a note that
    the displayed amount includes the original stake.

    Args:
        payout: Total potential payout in dollars.
        stake: Original stake amount included in the payout.

    Returns:
        An HTML string ready for
        ``st.markdown(…, unsafe_allow_html=True)``.
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


# ---------------------------------------------------------------------------
# Value bets / arbitrage
# ---------------------------------------------------------------------------


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
        home: Home team name.
        away: Away team name.
        outcome: Outcome being bet (e.g. ``"Home"``, ``"Over 2.5"``).
        bookmaker: Name of the bookmaker offering the value price.
        price: Decimal odds offered by the bookmaker.
        edge: Calculated edge over the consensus probability (0–1 scale).
        american_odds: Optional pre-formatted American odds string
            (e.g. ``"+150"`` or ``"-200"``). When provided, it is shown
            in blue beside the decimal price.

    Returns:
        An HTML string ready for ``st.markdown(…, unsafe_allow_html=True)``.
    """
    american_html = (
        f' <span style="font-size:0.7rem;color:#40C4FF;">'
        f"({american_odds})</span>"
        if american_odds
        else ""
    )
    implied_prob = 1.0 / price if price > 0 else 0.0
    edge_meter_pct = min(edge / _EDGE_METER_MAX, 1.0) * 100
    return (
        f'<div class="alert-card">'
        f'<div class="alert-header">'
        f'<span class="alert-teams">\u26bd {home} vs {away}</span>'
        f'<span class="alert-badge badge-value">+{edge:.1%} EDGE</span>'
        f'</div>'
        f'<div class="alert-detail">'
        f'<strong>{outcome}</strong> @ <strong>{price:.2f}</strong>'
        f'{american_html} '
        f'via {bookmaker}'
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
        f'<div class="vcard-stat-value" style="color:var(--accent-green);">+{edge:.1%}</div>'
        f'<div class="vcard-stat-value vcard-positive">+{edge:.1%}</div>'
        f'</div>'
        f'</div>'
        f'<div class="edge-meter-wrap">'
        f'<div class="edge-meter-label-row">'
        f'<span>Edge Meter</span>'
        f'<span>{edge:.1%} / {_EDGE_METER_MAX:.0%}</span>'
        f'</div>'
        f'<div class="edge-meter-track">'
        f'<div class="edge-meter-fill" style="width:{edge_meter_pct:.1f}%"></div>'
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
        home: Home team name.
        away: Away team name.
        market: Market key (e.g. ``"h2h"``, ``"totals"``).
        arb_pct: Guaranteed profit percentage (e.g. ``1.23`` for 1.23%).
        best_odds: Mapping of outcome label → best available decimal price.

    Returns:
        An HTML string ready for ``st.markdown(…, unsafe_allow_html=True)``.
    """
    odds_parts = " \u00b7 ".join(f"{k}: <strong>{v:.2f}</strong>" for k, v in best_odds.items())
    return (
        f'<div class="alert-card">'
        f'<div class="alert-header">'
        f'<span class="alert-teams">\U0001f504 {home} vs {away}</span>'
        f'<span class="alert-badge badge-arb">\U0001f4b0 {arb_pct:.3f}% PROFIT</span>'
        f'</div>'
        f'<div class="alert-detail">'
        f'Market: <strong>{market}</strong><br>'
        f'{odds_parts}'
        f'</div>'
        f'</div>'
    )


# ---------------------------------------------------------------------------
# Live match
# ---------------------------------------------------------------------------


def render_featured_live_card(
    home: str,
    away: str,
    home_score: int,
    away_score: int,
    minute: str,
    league: str,
) -> str:
    """Return HTML for a featured live match card.

    Renders a gradient-styled card highlighting a live match with
    the current score and minute indicator.

    Args:
        home: Home team name.
        away: Away team name.
        home_score: Current score for the home team.
        away_score: Current score for the away team.
        minute: Match minute string (e.g. ``"74'"``).
        league: League / competition label.

    Returns:
        An HTML string ready for
        ``st.markdown(…, unsafe_allow_html=True)``.
    """
    return (
        f'<div class="featured-live">'
        f'<span class="fl-badge">Live Now</span>'
        f'<span class="fl-time">{minute} - {league}</span>'
        f'<div class="fl-teams">'
        f'<div class="fl-team">'
        f'<div class="fl-team-icon">\U0001f6e1\ufe0f</div>'
        f'<div class="fl-team-name">{home}</div>'
        f'</div>'
        f'<div style="text-align:center;">'
        f'<div class="fl-score">'
        f'{home_score} - {away_score}</div>'
        f'<div class="fl-score-label">Score</div>'
        f'</div>'
        f'<div class="fl-team">'
        f'<div class="fl-team-icon">\U0001f6e1\ufe0f</div>'
        f'<div class="fl-team-name">{away}</div>'
        f'</div>'
        f'</div>'
        f'</div>'
    )


# ---------------------------------------------------------------------------
# Parlay builder
# ---------------------------------------------------------------------------


def render_parlay_leg(
    index: int,
    label: str,
    odds: float,
    implied_prob: float,
    meta: str = "",
) -> str:
    """Return HTML for an enhanced parlay leg card with probability bar.

    Args:
        index: 1-based leg number shown in the numbered badge.
        label: Human-readable selection label (e.g. ``"Arsenal ML"``).
        odds: Decimal odds for this leg.
        implied_prob: Implied win probability (0–1 scale).
        meta: Optional metadata string shown below the label
            (e.g. ``"Premier League • Today 20:00"``).

    Returns:
        An HTML string ready for
        ``st.markdown(…, unsafe_allow_html=True)``.
    """
    pct = max(0, min(100, round(implied_prob * 100)))
    meta_html = (
        f'<div class="leg-meta">{meta}</div>'
        if meta
        else ""
    )
    return (
        f'<div class="parlay-leg-v2">'
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

    Displays a live summary with a gold accent bar, showing
    the number of legs, combined odds, potential payout,
    and net profit at a glance.

    Args:
        num_legs: Total number of legs currently in the parlay.
        combined_odds: Product of all leg odds (already computed
            upstream).
        stake: Stake amount in dollars used to estimate payout
            and profit.

    Returns:
        An HTML string ready for
        ``st.markdown(…, unsafe_allow_html=True)``.
    """
    payout = stake * combined_odds if combined_odds > 0 else 0
    profit = payout - stake
    return (
        f'<div class="parlay-summary-v2">'
        f'<div class="ps2-tag">Live Summary</div>'
        f'<div class="ps2-title">'
        f'<span class="star">\u2b50</span> Pro Parlay Builder'
        f'</div>'
        f'<div class="ps2-stats">'
        f'<div class="ps2-stat">'
        f'<div class="ps2-label">Legs</div>'
        f'<div class="ps2-value">{num_legs}</div>'
        f'</div>'
        f'<div class="ps2-stat">'
        f'<div class="ps2-label">Combined Odds</div>'
        f'<div class="ps2-value gold">'
        f'{combined_odds:.2f}x</div>'
        f'</div>'
        f'<div class="ps2-stat">'
        f'<div class="ps2-label">Total Payout</div>'
        f'<div class="ps2-value green">'
        f'${payout:,.2f}</div>'
        f'</div>'
        f'<div class="ps2-stat">'
        f'<div class="ps2-label">Net Profit</div>'
        f'<div class="ps2-value">'
        f'${profit:,.2f}</div>'
        f'</div>'
        f'</div>'
        f'</div>'
    )


# ---------------------------------------------------------------------------
# Calculator
# ---------------------------------------------------------------------------


def render_calculator_card(
    icon: str,
    title: str,
    subtitle: str,
) -> str:
    """Return HTML for a calculator card header.

    Args:
        icon: Emoji icon for the calculator (e.g. "💰").
        title: Calculator title (e.g. "Single Bet Calculator").
        subtitle: Brief description of the calculator's purpose.

    Returns:
        Opening HTML for a calculator card, to be closed with </div>.
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


# ---------------------------------------------------------------------------
# Section header
# ---------------------------------------------------------------------------


def render_section_banner(
    kicker: str,
    title: str,
    subtitle: str,
) -> str:
    """Return a compact section header banner for each app page.

    Args:
        kicker: Small uppercase category label.
        title: Primary section title.
        subtitle: Supporting description shown under the title.

    Returns:
        HTML snippet for ``st.markdown(..., unsafe_allow_html=True)``.
    """
    return (
        '<div class="section-banner">'
        f'<div class="section-kicker">{kicker}</div>'
        f'<h3 class="section-title">{title}</h3>'
        f'<div class="section-subtitle">{subtitle}</div>'
        '</div>'
    )


# ---------------------------------------------------------------------------
# Shared utility helpers
# ---------------------------------------------------------------------------


def render_count_badge(count: int) -> str:
    """Return HTML for a small count badge pill."""
    return f'<span class="count-badge">{count}</span>'


def render_csv_download(
    df: pd.DataFrame,
    filename: str,
    label: str = "Export CSV",
) -> None:
    """Render a Streamlit CSV download button for *df*."""
    st.download_button(label, df.to_csv(index=False), filename, "text/csv")


# ---------------------------------------------------------------------------
# Plotly theme helper
# ---------------------------------------------------------------------------


def _apply_dark_theme(fig):
    """Apply the sportsbook dark theme to a Plotly figure."""
    fig.update_layout(
        paper_bgcolor=DARK_THEME["paper_bgcolor"],
        plot_bgcolor=DARK_THEME["plot_bgcolor"],
        font_color=DARK_THEME["font_color"],
        font_family="Inter, sans-serif",
        colorway=DARK_THEME["colorway"],
        title_font_size=14,
        title_font_color="#E8EAED",
        legend_bgcolor="rgba(0,0,0,0)",
        legend_font_color="#8899AA",
    )
    fig.update_xaxes(
        gridcolor=DARK_THEME["gridcolor"],
        zerolinecolor=DARK_THEME["gridcolor"],
        title_font_color="#8899AA",
        tickfont_color="#8899AA",
    )
    fig.update_yaxes(
        gridcolor=DARK_THEME["gridcolor"],
        zerolinecolor=DARK_THEME["gridcolor"],
        title_font_color="#8899AA",
        tickfont_color="#8899AA",
    )
    return fig
