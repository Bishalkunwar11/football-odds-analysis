# src/components/match_card.py
"""Renders sportsbook-style match cards and featured live cards."""

from __future__ import annotations

import re


def _initials(name: str) -> str:
    """Return up to 2 capital initials from a team name."""
    words = re.findall(r"[A-Za-z]+", name)
    if not words:
        return "??"
    if len(words) == 1:
        return words[0][:2].upper()
    return (words[0][0] + words[-1][0]).upper()


def render_match_card_header(
    home: str,
    away: str,
    league: str,
    kickoff: str,
    edge_pct: float | None = None,
) -> str:
    """Return HTML for the top portion of a match card (no odds row).

    Includes league badge, team initial circles, team names, and either
    a kickoff time or a PRO EDGE badge when real edge > 0.

    Args:
        home:     Home team name.
        away:     Away team name.
        league:   League / competition label.
        kickoff:  ISO kick-off time string.
        edge_pct: Best value-bet edge for this match (0–1 scale).
                  PRO EDGE badge shown only when this is positive.
    """
    if edge_pct is not None and edge_pct > 0:
        right_meta = f'<span class="pro-edge-badge">PRO EDGE +{edge_pct:.1%}</span>'
    else:
        right_meta = f'<div class="kickoff">🕐 {kickoff}</div>'

    home_init = _initials(home)
    away_init = _initials(away)

    return (
        f'<div class="match-card">'
        f'<div class="card-meta-row">'
        f'<span class="league-badge">⚽ {league}</span>'
        f'{right_meta}'
        f'</div>'
        f'<div class="teams">'
        f'<div class="team-col">'
        f'<div class="team-init-circle">{home_init}</div>'
        f'<span class="team-name">{home}</span>'
        f'</div>'
        f'<span class="vs-badge">VS</span>'
        f'<div class="team-col team-col-away">'
        f'<div class="team-init-circle away-circle">{away_init}</div>'
        f'<span class="team-name away">{away}</span>'
        f'</div>'
        f'</div>'
        f'</div>'
    )


def render_odds_button_label(
    outcome: str,
    price: float,
    direction: str | None = None,
) -> str:
    """Return a plain-text label for an odds st.button().

    Format: ``{OUTCOME}  {price}  {arrow}``

    Args:
        outcome:   Outcome label (e.g. "Arsenal", "Draw").
        price:     Decimal odds.
        direction: "up", "down", or "stable" / None.
    """
    arrow = {"up": " ▲", "down": " ▼"}.get(direction or "stable", "")
    return f"{outcome}  {price:.2f}{arrow}"


def render_match_card(
    home: str,
    away: str,
    league: str,
    kickoff: str,
    odds: dict[str, float] | None = None,
    edge_pct: float | None = None,
) -> str:
    """Return full HTML for a match card (header + odds row).

    This is the legacy pure-HTML version used when clickable buttons are not
    needed (e.g. embedding in a grid context). For interactive slip-add
    buttons, use :func:`render_match_card_header` + ``st.button()`` in the
    calling section.

    Args:
        home:     Home team name.
        away:     Away team name.
        league:   League / competition label.
        kickoff:  ISO kick-off time string.
        odds:     Optional mapping of outcome label → best decimal price.
        edge_pct: Optional best edge percentage (0–1 scale).
    """
    header = render_match_card_header(home, away, league, kickoff, edge_pct)
    # Strip the closing </div> to append odds row inside the same card div
    header = header.rstrip()
    if header.endswith("</div>"):
        header = header[:-6]

    odds_html = ""
    if odds:
        btns: list[str] = []
        for label, price in odds.items():
            implied = 1 / price if price > 0 else 0
            btns.append(
                f'<div class="odds-btn" role="button" tabindex="0" '
                f'aria-label="{label} odds {price:.2f}">'
                f'<div class="outcome-label">{label}</div>'
                f'<div class="odds-value">{price:.2f}</div>'
                f'<div class="implied-prob">{implied:.0%}</div>'
                f'</div>'
            )
        odds_html = f'<div class="odds-row">{"".join(btns)}</div>'

    return f"{header}{odds_html}</div>"


def render_featured_live_card(
    home: str,
    away: str,
    home_score: int,
    away_score: int,
    minute: str,
    league: str,
) -> str:
    """Return HTML for a featured live match card."""
    return (
        f'<div class="featured-live">'
        f'<span class="fl-badge">Live Now</span>'
        f'<span class="fl-time">{minute} · {league}</span>'
        f'<div class="fl-teams">'
        f'<div class="fl-team">'
        f'<div class="fl-team-icon">🛡️</div>'
        f'<div class="fl-team-name">{home}</div>'
        f'</div>'
        f'<div style="text-align:center;">'
        f'<div class="fl-score">{home_score} – {away_score}</div>'
        f'<div class="fl-score-label">Score</div>'
        f'</div>'
        f'<div class="fl-team">'
        f'<div class="fl-team-icon">🛡️</div>'
        f'<div class="fl-team-name">{away}</div>'
        f'</div>'
        f'</div>'
        f'</div>'
    )
