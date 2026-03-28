# src/components/match_card.py
"""Renders sportsbook-style match cards and featured live cards."""

from __future__ import annotations


def render_match_card(
    home: str,
    away: str,
    league: str,
    kickoff: str,
    odds: dict[str, float] | None = None,
    edge_pct: float | None = None,
) -> str:
    """Return HTML for a single sportsbook-style match card.

    Layout:
        Row 1 — league badge (left) | kickoff time or PRO EDGE badge (right)
        Row 2 — home team | VS | away team
        Row 3 — odds buttons (1 / X / 2) spanning full width

    Args:
        home:     Home team name.
        away:     Away team name.
        league:   League / competition label shown in the badge.
        kickoff:  ISO kick-off time string displayed on the card.
        odds:     Optional mapping of outcome label → best decimal price.
        edge_pct: Optional best edge percentage for this match (0–1 scale).
                  When positive a PRO EDGE badge is shown instead of kickoff.

    Returns:
        HTML string for ``st.markdown(..., unsafe_allow_html=True)``.
    """
    # Right-side meta: PRO EDGE badge or kickoff time
    if edge_pct is not None and edge_pct > 0:
        right_meta = (
            f'<span class="pro-edge-badge">PRO EDGE +{edge_pct:.1%}</span>'
        )
    else:
        right_meta = f'<div class="kickoff">\U0001f550 {kickoff}</div>'

    # Odds button row
    odds_html = ""
    if odds:
        btns: list[str] = []
        for label, price in odds.items():
            if price > 2.0:
                movement = ' <span class="odds-up">\u25b2</span>'
            elif price < 1.8:
                movement = ' <span class="odds-down">\u25bc</span>'
            else:
                movement = ""
            btns.append(
                    f'<div class="odds-btn" role="button" tabindex="0" '
                    f'aria-label="{label} odds {price:.2f}">'
                f'<div class="outcome-label">{label}</div>'
                f'<div class="odds-value">{price:.2f}{movement}</div>'
                f'</div>'
            )
        odds_html = f'<div class="odds-row">{"".join(btns)}</div>'

    return (
        f'<div class="match-card">'
        f'<div class="card-meta-row">'
        f'<span class="league-badge">\u26bd {league}</span>'
        f'{right_meta}'
        f'</div>'
        f'<div class="teams">'
        f'<span class="team-name">{home}</span>'
        f'<span class="vs-badge">VS</span>'
        f'<span class="team-name away">{away}</span>'
        f'</div>'
        f'{odds_html}'
        f'</div>'
    )


def render_featured_live_card(
    home: str,
    away: str,
    home_score: int,
    away_score: int,
    minute: str,
    league: str,
) -> str:
    """Return HTML for a featured live match card.

    Args:
        home:       Home team name.
        away:       Away team name.
        home_score: Current score for the home team.
        away_score: Current score for the away team.
        minute:     Match minute string (e.g. ``"74'"``).
        league:     League / competition label.

    Returns:
        HTML string for ``st.markdown(..., unsafe_allow_html=True)``.
    """
    return (
        f'<div class="featured-live">'
        f'<span class="fl-badge">Live Now</span>'
        f'<span class="fl-time">{minute} \u00b7 {league}</span>'
        f'<div class="fl-teams">'
        f'<div class="fl-team">'
        f'<div class="fl-team-icon">\U0001f6e1\ufe0f</div>'
        f'<div class="fl-team-name">{home}</div>'
        f'</div>'
        f'<div style="text-align:center;">'
        f'<div class="fl-score">{home_score} \u2013 {away_score}</div>'
        f'<div class="fl-score-label">Score</div>'
        f'</div>'
        f'<div class="fl-team">'
        f'<div class="fl-team-icon">\U0001f6e1\ufe0f</div>'
        f'<div class="fl-team-name">{away}</div>'
        f'</div>'
        f'</div>'
        f'</div>'
    )
