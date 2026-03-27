"""Focused unit tests for BetCalculator payout, accumulator, Kelly, and conversions."""

from __future__ import annotations

import pytest

from src.bet_calculator import BetCalculator


def test_calculate_payout_standard_case() -> None:
    calc = BetCalculator()
    result = calc.calculate_payout(stake=100, decimal_odds=2.50)

    assert result["payout"] == 250.0
    assert result["profit"] == 150.0


def test_calculate_accumulator_combines_odds_and_profit() -> None:
    calc = BetCalculator()
    result = calc.calculate_accumulator(stake=50, odds_list=[1.8, 2.0, 1.5])

    assert result["combined_odds"] == pytest.approx(5.4)
    assert result["payout"] == pytest.approx(270.0)
    assert result["profit"] == pytest.approx(220.0)


def test_kelly_criterion_positive_edge_half_kelly() -> None:
    calc = BetCalculator()
    result = calc.kelly_criterion(
        decimal_odds=2.2,
        win_probability=0.55,
        bankroll=1000,
        fractional_kelly=0.5,
    )

    assert result["edge"] > 0
    assert 0 < result["kelly_fraction"] < 0.2
    assert result["recommended_stake"] > 0


def test_decimal_to_american_positive_case() -> None:
    calc = BetCalculator()
    assert calc.decimal_to_american(2.5) == 150


def test_american_to_decimal_negative_case() -> None:
    calc = BetCalculator()
    assert calc.american_to_decimal(-150) == pytest.approx(1.6667, rel=1e-3)


def test_fractional_to_decimal_case() -> None:
    calc = BetCalculator()
    assert calc.fractional_to_decimal(5, 2) == 3.5
