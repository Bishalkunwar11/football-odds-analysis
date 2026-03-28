# src/components/live_ticker.py
"""Renders a scrolling live-scores ticker bar using pure CSS animation."""

from __future__ import annotations

_TICKER_CSS = """
<style>
@keyframes ticker-scroll {
  from { transform: translateX(0); }
  to   { transform: translateX(-50%); }
}
.ticker-wrap {
  overflow: hidden;
  white-space: nowrap;
  background: var(--bg-raised);
  border: 0.5px solid var(--border-subtle);
  border-radius: 8px;
  padding: 0.55rem 0;
  margin-bottom: 1rem;
  cursor: default;
}
.ticker-wrap:hover .ticker-track {
  animation-play-state: paused;
}
.ticker-track {
  display: inline-block;
  animation: ticker-scroll 40s linear infinite;
}
.ticker-item {
  display: inline-block;
  padding: 0 1.8rem;
  font-size: 0.74rem;
  font-weight: 600;
  font-family: 'DM Sans', sans-serif;
  vertical-align: middle;
}
.ticker-score {
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 0.9rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.ticker-min {
  font-size: 0.69rem;
  color: var(--text-secondary);
}
.ticker-league {
  font-size: 0.69rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
.ticker-sep {
  color: var(--border-mid);
  padding: 0 0.4rem;
  font-size: 0.72rem;
}
</style>
"""


def render_live_ticker(matches: list[dict]) -> str:
    """Return scrolling ticker HTML for a list of live/upcoming matches.

    Each *match* dict should contain:
        ``home``        — home team name
        ``away``        — away team name
        ``home_score``  — home score (int)
        ``away_score``  — away score (int)
        ``minute``      — match minute string (e.g. ``"74'"`` or ``"FT"``)
        ``league``      — league / competition label
        ``is_live``     — bool; True → accent-red, False → text-muted

    The content is duplicated so the CSS ``translateX(-50%)`` creates a
    seamless infinite loop without JavaScript.

    Args:
        matches: List of match dicts described above.

    Returns:
        HTML string including an embedded ``<style>`` block and the ticker
        markup, ready for ``st.markdown(..., unsafe_allow_html=True)``.
    """
    if not matches:
        return ""

    def _item(m: dict) -> str:
        is_live = m.get("is_live", False)
        score_color = "var(--accent-red)" if is_live else "var(--text-muted)"
        home = m.get("home", "")
        away = m.get("away", "")
        h_score = m.get("home_score", 0)
        a_score = m.get("away_score", 0)
        minute = m.get("minute", "")
        league = m.get("league", "")
        return (
            f'<span class="ticker-item">'
            f'<span style="color:var(--text-secondary);">{home}</span>'
            f' <span class="ticker-score" style="color:{score_color};">'
            f'{h_score} \u2013 {a_score}</span>'
            f' <span style="color:var(--text-secondary);">{away}</span>'
            f' <span class="ticker-min">\u00b7 {minute}</span>'
            f' <span class="ticker-league">\u00b7 {league}</span>'
            f'</span>'
            f'<span class="ticker-sep">|</span>'
        )

    single_pass = "".join(_item(m) for m in matches)
    # Duplicate so the -50% translate creates a seamless loop
    full_track = single_pass * 2

    return (
        f"{_TICKER_CSS}"
      f'<div class="ticker-wrap" aria-live="polite" aria-label="Live scores">'
        f'<div class="ticker-track">{full_track}</div>'
        f"</div>"
    )
