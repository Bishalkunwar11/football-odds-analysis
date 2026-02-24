"""Unit tests for OddsAnalyzer."""

import pytest
import pandas as pd

from src.analyzer import OddsAnalyzer


@pytest.fixture()
def analyzer() -> OddsAnalyzer:
    return OddsAnalyzer()


# ---------------------------------------------------------------------------
# implied_probability
# ---------------------------------------------------------------------------

class TestImpliedProbability:
    def test_even_odds(self, analyzer: OddsAnalyzer) -> None:
        assert analyzer.implied_probability(2.0) == pytest.approx(0.5)

    def test_heavy_favourite(self, analyzer: OddsAnalyzer) -> None:
        assert analyzer.implied_probability(1.25) == pytest.approx(0.8)

    def test_long_shot(self, analyzer: OddsAnalyzer) -> None:
        assert analyzer.implied_probability(10.0) == pytest.approx(0.1)

    def test_invalid_zero(self, analyzer: OddsAnalyzer) -> None:
        with pytest.raises(ValueError):
            analyzer.implied_probability(0)

    def test_invalid_negative(self, analyzer: OddsAnalyzer) -> None:
        with pytest.raises(ValueError):
            analyzer.implied_probability(-1.5)


# ---------------------------------------------------------------------------
# calculate_margin
# ---------------------------------------------------------------------------

class TestCalculateMargin:
    def test_fair_book_no_margin(self, analyzer: OddsAnalyzer) -> None:
        # 50/50 market with no vig: 1/2 + 1/2 = 1 → margin = 0
        assert analyzer.calculate_margin([2.0, 2.0]) == pytest.approx(0.0)

    def test_typical_book_margin(self, analyzer: OddsAnalyzer) -> None:
        # 1/1.91 + 1/1.91 ≈ 1.0471 → margin ≈ 4.71 %
        margin = analyzer.calculate_margin([1.91, 1.91])
        assert pytest.approx(margin, abs=1e-4) == (2 / 1.91) - 1

    def test_three_way_market(self, analyzer: OddsAnalyzer) -> None:
        # Typical 1X2 market
        margin = analyzer.calculate_margin([2.5, 3.2, 2.8])
        assert margin > 0

    def test_empty_list_raises(self, analyzer: OddsAnalyzer) -> None:
        with pytest.raises(ValueError):
            analyzer.calculate_margin([])

    def test_negative_odds_raises(self, analyzer: OddsAnalyzer) -> None:
        with pytest.raises(ValueError):
            analyzer.calculate_margin([2.0, -1.0])


# ---------------------------------------------------------------------------
# calculate_fair_odds
# ---------------------------------------------------------------------------

class TestCalculateFairOdds:
    def test_removes_margin(self, analyzer: OddsAnalyzer) -> None:
        # With margin the implied probs sum > 1; after removal they sum to 1
        fair = analyzer.calculate_fair_odds([1.91, 1.91])
        assert sum(1.0 / o for o in fair) == pytest.approx(1.0)

    def test_already_fair(self, analyzer: OddsAnalyzer) -> None:
        # 2.0, 2.0 is already fair – should remain unchanged
        fair = analyzer.calculate_fair_odds([2.0, 2.0])
        assert fair == pytest.approx([2.0, 2.0])

    def test_empty_raises(self, analyzer: OddsAnalyzer) -> None:
        with pytest.raises(ValueError):
            analyzer.calculate_fair_odds([])


# ---------------------------------------------------------------------------
# find_arbitrage
# ---------------------------------------------------------------------------

def _make_h2h_df(
    odds_map: dict[str, dict[str, float]],
    match_id: str = "match1",
) -> pd.DataFrame:
    """Build a minimal odds DataFrame for a single h2h match.

    Args:
        odds_map: {bookmaker: {outcome: price}}
        match_id: Match identifier.
    """
    rows = []
    for book, outcomes in odds_map.items():
        for outcome, price in outcomes.items():
            rows.append(
                {
                    "match_id": match_id,
                    "home_team": "Home FC",
                    "away_team": "Away FC",
                    "commence_time": "2030-01-01T12:00:00Z",
                    "bookmaker": book,
                    "market": "h2h",
                    "outcome_name": outcome,
                    "outcome_price": price,
                }
            )
    return pd.DataFrame(rows)


class TestFindArbitrage:
    def test_no_arbitrage(self, analyzer: OddsAnalyzer) -> None:
        df = _make_h2h_df(
            {
                "BookA": {"Home": 2.0, "Draw": 3.2, "Away": 3.4},
                "BookB": {"Home": 1.9, "Draw": 3.0, "Away": 3.6},
            }
        )
        result = analyzer.find_arbitrage(df)
        assert result.empty

    def test_arbitrage_detected(self, analyzer: OddsAnalyzer) -> None:
        # Crafted odds: best prices → 1/3.5 + 1/3.5 + 1/3.5 ≈ 0.857 < 1
        df = _make_h2h_df(
            {
                "BookA": {"Home": 3.5, "Draw": 2.0, "Away": 2.0},
                "BookB": {"Home": 2.0, "Draw": 3.5, "Away": 2.0},
                "BookC": {"Home": 2.0, "Draw": 2.0, "Away": 3.5},
            }
        )
        result = analyzer.find_arbitrage(df)
        assert not result.empty
        assert result.iloc[0]["arb_pct"] > 0

    def test_empty_dataframe(self, analyzer: OddsAnalyzer) -> None:
        result = analyzer.find_arbitrage(pd.DataFrame())
        assert result.empty

    def test_missing_columns_raises(self, analyzer: OddsAnalyzer) -> None:
        with pytest.raises(ValueError):
            analyzer.find_arbitrage(pd.DataFrame({"match_id": [1]}))


# ---------------------------------------------------------------------------
# find_value_bets
# ---------------------------------------------------------------------------

class TestFindValueBets:
    def _make_df(self) -> pd.DataFrame:
        """Create a DataFrame where BookSoft offers +10 % edge on Home."""
        rows = [
            # Sharp bookmaker – well-calibrated odds
            {
                "match_id": "m1",
                "home_team": "Home FC",
                "away_team": "Away FC",
                "commence_time": "2030-01-01T12:00:00Z",
                "bookmaker": "Pinnacle",
                "market": "h2h",
                "outcome_name": "Home",
                "outcome_price": 2.0,   # implied 50 %
            },
            {
                "match_id": "m1",
                "home_team": "Home FC",
                "away_team": "Away FC",
                "commence_time": "2030-01-01T12:00:00Z",
                "bookmaker": "Pinnacle",
                "market": "h2h",
                "outcome_name": "Away",
                "outcome_price": 2.0,   # implied 50 %
            },
            # Soft bookmaker offering significantly higher odds on Home
            {
                "match_id": "m1",
                "home_team": "Home FC",
                "away_team": "Away FC",
                "commence_time": "2030-01-01T12:00:00Z",
                "bookmaker": "BookSoft",
                "market": "h2h",
                "outcome_name": "Home",
                "outcome_price": 3.5,   # implied ≈ 28.6 % (edge vs 50 % = 21.4 %)
            },
            {
                "match_id": "m1",
                "home_team": "Home FC",
                "away_team": "Away FC",
                "commence_time": "2030-01-01T12:00:00Z",
                "bookmaker": "BookSoft",
                "market": "h2h",
                "outcome_name": "Away",
                "outcome_price": 1.5,   # implied ≈ 66.7 %
            },
        ]
        return pd.DataFrame(rows)

    def test_value_bet_found(self, analyzer: OddsAnalyzer) -> None:
        df = self._make_df()
        result = analyzer.find_value_bets(
            df, sharp_bookmakers=["Pinnacle"], threshold=0.05
        )
        assert not result.empty
        # The Home outcome at BookSoft should be flagged
        assert "BookSoft" in result["bookmaker"].values

    def test_no_value_bets_high_threshold(self, analyzer: OddsAnalyzer) -> None:
        df = _make_h2h_df(
            {"BookA": {"Home": 2.0, "Away": 2.0}}, "m2"
        )
        result = analyzer.find_value_bets(
            df, sharp_bookmakers=["BookA"], threshold=0.99
        )
        assert result.empty

    def test_empty_dataframe(self, analyzer: OddsAnalyzer) -> None:
        result = analyzer.find_value_bets(pd.DataFrame())
        assert result.empty
