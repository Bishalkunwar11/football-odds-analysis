"""Unit tests for HTML rendering helpers in app.py."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Streamlit must be mocked *before* importing app.py.  The mock
# must be thorough enough to survive module-level execution of
# st.columns, st.session_state, st.number_input, etc.
_st_mock = MagicMock()
_st_mock.columns = lambda n=2, **kw: (
    [MagicMock() for _ in range(n)] if isinstance(n, int)
    else [MagicMock() for _ in n]
)
_st_mock.cache_resource = lambda f=None, **kw: (
    f if f else (lambda fn: fn)
)
_st_mock.cache_data = lambda f=None, **kw: (
    f if f else (lambda fn: fn)
)
# session_state behaves like a dict
_st_mock.session_state = {
    "active_section": "matches",
    "bet_slip": [],
    "parlay_legs": [],
    "last_refreshed": None,
    "slip_pane_stake": 100.0,
    "parlay_stake": 10.0,
}
# number_input / slider / text_input should return sensible defaults
_st_mock.number_input = MagicMock(return_value=100.0)
_st_mock.slider = MagicMock(return_value=0.05)
_st_mock.text_input = MagicMock(return_value="")
_st_mock.selectbox = MagicMock(return_value="Decimal")
_st_mock.multiselect = MagicMock(return_value=[])
_st_mock.radio = MagicMock(return_value="Calculator Tools")
_st_mock.button = MagicMock(return_value=False)
_st_mock.column_config = MagicMock()
sys.modules["streamlit"] = _st_mock

# Ensure project root is importable
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src.app import (  # noqa: E402
    render_featured_live_card,
    render_parlay_leg,
    render_parlay_summary,
    render_payout_hero,
)


# -------------------------------------------------------------------
# render_parlay_summary
# -------------------------------------------------------------------


class TestRenderParlaySummary:
    """Tests for the enhanced parlay summary banner."""

    def test_contains_live_summary_tag(self) -> None:
        """Banner includes the 'Live Summary' tag."""
        html = render_parlay_summary(3, 5.0, 100.0)
        assert "Live Summary" in html

    def test_contains_pro_parlay_title(self) -> None:
        """Banner includes the 'Pro Parlay Builder' title."""
        html = render_parlay_summary(2, 3.5, 50.0)
        assert "Pro Parlay Builder" in html

    def test_displays_leg_count(self) -> None:
        """Number of legs is rendered in the stats row."""
        html = render_parlay_summary(4, 10.0, 100.0)
        assert ">4<" in html

    def test_displays_combined_odds_with_x_suffix(self) -> None:
        """Combined odds are shown with an 'x' suffix."""
        html = render_parlay_summary(2, 3.50, 10.0)
        assert "3.50x" in html

    def test_displays_payout(self) -> None:
        """Total payout is calculated as stake * combined_odds."""
        html = render_parlay_summary(2, 5.0, 100.0)
        # 100 * 5.0 = 500.00
        assert "$500.00" in html

    def test_displays_net_profit(self) -> None:
        """Net profit is payout minus stake."""
        html = render_parlay_summary(2, 5.0, 100.0)
        # profit = 500 - 100 = 400.00
        assert "$400.00" in html

    def test_zero_combined_odds(self) -> None:
        """Handles zero combined odds gracefully."""
        html = render_parlay_summary(0, 0, 100.0)
        assert "$0.00" in html

    def test_uses_v2_css_class(self) -> None:
        """Uses the new parlay-summary-v2 CSS class."""
        html = render_parlay_summary(1, 2.0, 10.0)
        assert "parlay-summary-v2" in html


# -------------------------------------------------------------------
# render_parlay_leg
# -------------------------------------------------------------------


class TestRenderParlayLeg:
    """Tests for the enhanced parlay leg card with probability bar."""

    def test_contains_leg_number(self) -> None:
        """Leg card shows the index number."""
        html = render_parlay_leg(1, "Arsenal ML", 1.85, 0.541)
        assert "#1" in html

    def test_contains_label(self) -> None:
        """Leg card shows the selection label."""
        html = render_parlay_leg(1, "Arsenal ML", 1.85, 0.541)
        assert "Arsenal ML" in html

    def test_contains_odds(self) -> None:
        """Leg card shows decimal odds."""
        html = render_parlay_leg(1, "Test", 2.10, 0.476)
        assert "2.10" in html

    def test_contains_implied_probability(self) -> None:
        """Leg card shows implied probability percentage."""
        html = render_parlay_leg(1, "Test", 2.0, 0.50)
        assert "50.0%" in html

    def test_contains_probability_bar(self) -> None:
        """Leg card includes a visual probability bar."""
        html = render_parlay_leg(1, "Test", 2.0, 0.50)
        assert "prob-bar" in html
        assert "prob-fill" in html
        assert 'width:50%' in html

    def test_prob_bar_clamps_to_100(self) -> None:
        """Probability bar width is clamped to 100% maximum."""
        html = render_parlay_leg(1, "Test", 0.5, 1.5)
        assert 'width:100%' in html

    def test_prob_bar_clamps_to_0(self) -> None:
        """Probability bar width is clamped to 0% minimum."""
        html = render_parlay_leg(1, "Test", 2.0, -0.1)
        assert 'width:0%' in html

    def test_meta_displayed_when_provided(self) -> None:
        """Optional metadata is included below the label."""
        html = render_parlay_leg(
            1, "Arsenal ML", 1.85, 0.541,
            meta="Premier League \u2022 Today 20:00",
        )
        assert "Premier League" in html
        assert "leg-meta" in html

    def test_meta_omitted_when_empty(self) -> None:
        """No metadata element when meta is not provided."""
        html = render_parlay_leg(1, "Test", 2.0, 0.5)
        assert "leg-meta" not in html

    def test_uses_v2_css_class(self) -> None:
        """Uses the new parlay-leg-v2 CSS class."""
        html = render_parlay_leg(1, "Test", 2.0, 0.5)
        assert "parlay-leg-v2" in html


# -------------------------------------------------------------------
# render_featured_live_card
# -------------------------------------------------------------------


class TestRenderFeaturedLiveCard:
    """Tests for the featured live match card."""

    def test_contains_live_badge(self) -> None:
        """Card includes a 'Live Now' badge."""
        html = render_featured_live_card(
            "Man City", "Arsenal", 2, 1, "74'", "Premier League",
        )
        assert "Live Now" in html

    def test_contains_team_names(self) -> None:
        """Card displays both team names."""
        html = render_featured_live_card(
            "Man City", "Arsenal", 2, 1, "74'", "Premier League",
        )
        assert "Man City" in html
        assert "Arsenal" in html

    def test_contains_score(self) -> None:
        """Card displays the match score."""
        html = render_featured_live_card(
            "Man City", "Arsenal", 2, 1, "74'", "Premier League",
        )
        assert "2 - 1" in html

    def test_contains_minute_and_league(self) -> None:
        """Card displays the match minute and league."""
        html = render_featured_live_card(
            "Man City", "Arsenal", 2, 1, "74'", "Premier League",
        )
        assert "74'" in html
        assert "Premier League" in html

    def test_uses_featured_live_css_class(self) -> None:
        """Uses the featured-live CSS class."""
        html = render_featured_live_card(
            "Home", "Away", 0, 0, "1'", "League",
        )
        assert "featured-live" in html


# -------------------------------------------------------------------
# render_payout_hero
# -------------------------------------------------------------------


class TestRenderPayoutHero:
    """Tests for the payout hero display widget."""

    def test_contains_payout_value(self) -> None:
        """Displays the formatted payout amount."""
        html = render_payout_hero(1245.00, 100.00)
        assert "$1,245.00" in html

    def test_contains_stake_note(self) -> None:
        """Shows a note including the original stake."""
        html = render_payout_hero(500.00, 50.00)
        assert "$50.00 stake" in html

    def test_contains_potential_payout_label(self) -> None:
        """Shows the 'Potential Payout' label."""
        html = render_payout_hero(100.00, 10.00)
        assert "Potential Payout" in html

    def test_uses_payout_hero_css_class(self) -> None:
        """Uses the payout-hero CSS class."""
        html = render_payout_hero(100.00, 10.00)
        assert "payout-hero" in html
