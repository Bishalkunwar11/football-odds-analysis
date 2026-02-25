"""Unit tests for BetCalculator."""

import pytest

from src.bet_calculator import BetCalculator


@pytest.fixture()
def calc() -> BetCalculator:
    return BetCalculator()


# ---------------------------------------------------------------------------
# decimal_to_fractional
# ---------------------------------------------------------------------------

class TestDecimalToFractional:
    def test_standard_conversion(self, calc: BetCalculator) -> None:
        assert calc.decimal_to_fractional(2.5) == (3, 2)

    def test_even_money(self, calc: BetCalculator) -> None:
        assert calc.decimal_to_fractional(2.0) == (1, 1)

    def test_short_odds(self, calc: BetCalculator) -> None:
        assert calc.decimal_to_fractional(1.5) == (1, 2)

    def test_long_odds(self, calc: BetCalculator) -> None:
        assert calc.decimal_to_fractional(10.0) == (9, 1)

    def test_invalid_raises(self, calc: BetCalculator) -> None:
        with pytest.raises(ValueError):
            calc.decimal_to_fractional(1.0)

    def test_negative_raises(self, calc: BetCalculator) -> None:
        with pytest.raises(ValueError):
            calc.decimal_to_fractional(-1.5)


# ---------------------------------------------------------------------------
# decimal_to_american
# ---------------------------------------------------------------------------

class TestDecimalToAmerican:
    def test_positive_american(self, calc: BetCalculator) -> None:
        # 2.50 → +150
        assert calc.decimal_to_american(2.5) == 150

    def test_even_money(self, calc: BetCalculator) -> None:
        # 2.0 → +100
        assert calc.decimal_to_american(2.0) == 100

    def test_negative_american(self, calc: BetCalculator) -> None:
        # 1.5 → -200
        assert calc.decimal_to_american(1.5) == -200

    def test_invalid_raises(self, calc: BetCalculator) -> None:
        with pytest.raises(ValueError):
            calc.decimal_to_american(1.0)


# ---------------------------------------------------------------------------
# american_to_decimal
# ---------------------------------------------------------------------------

class TestAmericanToDecimal:
    def test_positive_american(self, calc: BetCalculator) -> None:
        assert calc.american_to_decimal(150) == pytest.approx(2.5)

    def test_negative_american(self, calc: BetCalculator) -> None:
        assert calc.american_to_decimal(-200) == pytest.approx(1.5)

    def test_even_money(self, calc: BetCalculator) -> None:
        assert calc.american_to_decimal(100) == pytest.approx(2.0)

    def test_zero_raises(self, calc: BetCalculator) -> None:
        with pytest.raises(ValueError):
            calc.american_to_decimal(0)


# ---------------------------------------------------------------------------
# fractional_to_decimal
# ---------------------------------------------------------------------------

class TestFractionalToDecimal:
    def test_standard(self, calc: BetCalculator) -> None:
        assert calc.fractional_to_decimal(3, 2) == pytest.approx(2.5)

    def test_even_money(self, calc: BetCalculator) -> None:
        assert calc.fractional_to_decimal(1, 1) == pytest.approx(2.0)

    def test_zero_denominator_raises(self, calc: BetCalculator) -> None:
        with pytest.raises(ValueError):
            calc.fractional_to_decimal(3, 0)

    def test_negative_values_raise(self, calc: BetCalculator) -> None:
        with pytest.raises(ValueError):
            calc.fractional_to_decimal(-1, 2)


# ---------------------------------------------------------------------------
# calculate_payout
# ---------------------------------------------------------------------------

class TestCalculatePayout:
    def test_basic_payout(self, calc: BetCalculator) -> None:
        result = calc.calculate_payout(100, 2.5)
        assert result["payout"] == 250.0
        assert result["profit"] == 150.0
        assert result["implied_probability"] == pytest.approx(0.4)

    def test_zero_stake(self, calc: BetCalculator) -> None:
        result = calc.calculate_payout(0, 2.0)
        assert result["payout"] == 0.0
        assert result["profit"] == 0.0

    def test_negative_stake_raises(self, calc: BetCalculator) -> None:
        with pytest.raises(ValueError):
            calc.calculate_payout(-10, 2.0)

    def test_invalid_odds_raises(self, calc: BetCalculator) -> None:
        with pytest.raises(ValueError):
            calc.calculate_payout(100, 0)


# ---------------------------------------------------------------------------
# calculate_accumulator
# ---------------------------------------------------------------------------

class TestCalculateAccumulator:
    def test_two_leg_parlay(self, calc: BetCalculator) -> None:
        result = calc.calculate_accumulator(10, [2.0, 3.0])
        assert result["num_legs"] == 2
        assert result["combined_odds"] == pytest.approx(6.0)
        assert result["payout"] == pytest.approx(60.0)
        assert result["profit"] == pytest.approx(50.0)

    def test_single_leg(self, calc: BetCalculator) -> None:
        result = calc.calculate_accumulator(50, [2.5])
        assert result["combined_odds"] == pytest.approx(2.5)
        assert result["payout"] == pytest.approx(125.0)

    def test_empty_list_raises(self, calc: BetCalculator) -> None:
        with pytest.raises(ValueError):
            calc.calculate_accumulator(10, [])

    def test_odds_below_one_raises(self, calc: BetCalculator) -> None:
        with pytest.raises(ValueError):
            calc.calculate_accumulator(10, [2.0, 0.5])

    def test_negative_stake_raises(self, calc: BetCalculator) -> None:
        with pytest.raises(ValueError):
            calc.calculate_accumulator(-10, [2.0])


# ---------------------------------------------------------------------------
# kelly_criterion
# ---------------------------------------------------------------------------

class TestKellyCriterion:
    def test_positive_edge(self, calc: BetCalculator) -> None:
        # Decimal 2.0, true prob 60 % → edge = 0.2, kelly_f = 0.2
        result = calc.kelly_criterion(2.0, 0.6, bankroll=1000)
        assert result["edge"] > 0
        assert result["kelly_fraction"] == pytest.approx(0.2)
        assert result["recommended_stake"] == pytest.approx(200.0)

    def test_no_edge(self, calc: BetCalculator) -> None:
        # Fair odds: 2.0 at 50 % → edge = 0, stake = 0
        result = calc.kelly_criterion(2.0, 0.5)
        assert result["kelly_fraction"] == 0.0
        assert result["recommended_stake"] == 0.0

    def test_negative_edge_clamps_to_zero(self, calc: BetCalculator) -> None:
        # Odds 2.0 with 30 % win prob → negative kelly, clamped to 0
        result = calc.kelly_criterion(2.0, 0.3)
        assert result["kelly_fraction"] == 0.0
        assert result["recommended_stake"] == 0.0

    def test_half_kelly(self, calc: BetCalculator) -> None:
        result = calc.kelly_criterion(2.0, 0.6, bankroll=1000, fractional_kelly=0.5)
        assert result["kelly_fraction"] == pytest.approx(0.1)
        assert result["recommended_stake"] == pytest.approx(100.0)

    def test_invalid_odds_raises(self, calc: BetCalculator) -> None:
        with pytest.raises(ValueError):
            calc.kelly_criterion(1.0, 0.5)

    def test_invalid_probability_raises(self, calc: BetCalculator) -> None:
        with pytest.raises(ValueError):
            calc.kelly_criterion(2.0, 0.0)
        with pytest.raises(ValueError):
            calc.kelly_criterion(2.0, 1.0)

    def test_invalid_bankroll_raises(self, calc: BetCalculator) -> None:
        with pytest.raises(ValueError):
            calc.kelly_criterion(2.0, 0.6, bankroll=0)


# ---------------------------------------------------------------------------
# dutching_calculator
# ---------------------------------------------------------------------------

class TestDutchingCalculator:
    def test_two_outcomes(self, calc: BetCalculator) -> None:
        result = calc.dutching_calculator(100, [2.0, 3.0])
        assert len(result["stakes"]) == 2
        # Stakes should sum to ≈ total_stake
        assert sum(result["stakes"]) == pytest.approx(100, abs=0.02)
        # Each selection should produce the same payout
        for stake, odds in zip(result["stakes"], [2.0, 3.0]):
            assert stake * odds == pytest.approx(result["equal_payout"], abs=0.05)

    def test_equal_odds(self, calc: BetCalculator) -> None:
        result = calc.dutching_calculator(100, [2.0, 2.0])
        assert result["stakes"] == pytest.approx([50.0, 50.0])
        assert result["equal_payout"] == 100.0
        assert result["profit"] == 0.0

    def test_profit_when_overlapping(self, calc: BetCalculator) -> None:
        # Odds where sum(1/o) < 1 → positive profit (like dutching an arb)
        result = calc.dutching_calculator(100, [3.5, 3.5, 3.5])
        assert result["profit"] > 0

    def test_empty_list_raises(self, calc: BetCalculator) -> None:
        with pytest.raises(ValueError):
            calc.dutching_calculator(100, [])

    def test_zero_stake_raises(self, calc: BetCalculator) -> None:
        with pytest.raises(ValueError):
            calc.dutching_calculator(0, [2.0])

    def test_invalid_odds_raises(self, calc: BetCalculator) -> None:
        with pytest.raises(ValueError):
            calc.dutching_calculator(100, [2.0, -1.0])
