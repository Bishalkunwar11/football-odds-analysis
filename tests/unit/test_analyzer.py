"""Focused unit tests for OddsAnalyzer core calculations and scanners."""

from __future__ import annotations

import pandas as pd

from src.analyzer import OddsAnalyzer


def _odds_rows(prices_by_bookmaker: dict[str, dict[str, float]], match_id: str = "m1") -> pd.DataFrame:
    rows: list[dict] = []
    for bookmaker, outcomes in prices_by_bookmaker.items():
        for outcome_name, outcome_price in outcomes.items():
            rows.append(
                {
                    "match_id": match_id,
                    "home_team": "Home FC",
                    "away_team": "Away FC",
                    "commence_time": "2030-01-01T12:00:00Z",
                    "bookmaker": bookmaker,
                    "market": "h2h",
                    "outcome_name": outcome_name,
                    "outcome_price": outcome_price,
                }
            )
    return pd.DataFrame(rows)


def test_implied_probability_even_and_longshot() -> None:
    analyzer = OddsAnalyzer()
    assert analyzer.implied_probability(2.0) == 0.5
    assert analyzer.implied_probability(4.0) == 0.25


def test_calculate_margin_typical_range() -> None:
    analyzer = OddsAnalyzer()
    margin = analyzer.calculate_margin([1.85, 1.85])
    assert 0.03 < margin < 0.12


def test_find_arbitrage_detects_positive_case() -> None:
    analyzer = OddsAnalyzer()
    df = _odds_rows(
        {
            "BookA": {"Home": 2.10, "Away": 1.80},
            "BookB": {"Home": 1.80, "Away": 2.10},
        }
    )
    result = analyzer.find_arbitrage(df)
    assert not result.empty
    assert float(result.iloc[0]["arb_pct"]) > 0


def test_find_arbitrage_returns_empty_when_none() -> None:
    analyzer = OddsAnalyzer()
    df = _odds_rows(
        {
            "BookA": {"Home": 1.80, "Away": 1.80},
            "BookB": {"Home": 1.78, "Away": 1.79},
        }
    )
    result = analyzer.find_arbitrage(df)
    assert result.empty


def test_find_value_bets_detects_soft_book_edge() -> None:
    analyzer = OddsAnalyzer()
    df = _odds_rows(
        {
            "Pinnacle": {"Home": 2.0, "Away": 2.0},
            "Betfair": {"Home": 2.0, "Away": 2.0},
            "SoftBook": {"Home": 3.0, "Away": 1.6},
        }
    )
    result = analyzer.find_value_bets(
        df,
        sharp_bookmakers=["Pinnacle", "Betfair"],
        threshold=0.05,
    )

    assert not result.empty
    soft_home = result[
        (result["bookmaker"] == "SoftBook") & (result["outcome_name"] == "Home")
    ]
    assert not soft_home.empty


def test_find_value_bets_empty_with_extreme_threshold() -> None:
    analyzer = OddsAnalyzer()
    df = _odds_rows(
        {
            "BookA": {"Home": 2.0, "Away": 2.0},
            "BookB": {"Home": 2.05, "Away": 1.95},
        }
    )
    result = analyzer.find_value_bets(df, sharp_bookmakers=["BookA"], threshold=0.99)
    assert result.empty
