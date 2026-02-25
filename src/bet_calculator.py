"""Custom Bet Calculator: odds conversion, payout, parlay, Kelly, and dutching."""

import logging
import math
from itertools import combinations
from typing import Sequence

logger = logging.getLogger(__name__)


class BetCalculator:
    """Provides common betting calculations for the football odds system."""

    # ------------------------------------------------------------------
    # Odds conversion
    # ------------------------------------------------------------------

    @staticmethod
    def decimal_to_fractional(decimal_odds: float) -> tuple[int, int]:
        """Convert decimal odds to fractional (numerator, denominator).

        Args:
            decimal_odds: Decimal odds (e.g. 2.50).

        Returns:
            Tuple *(numerator, denominator)* — e.g. ``(3, 2)`` for 2.50.

        Raises:
            ValueError: If *decimal_odds* <= 1.
        """
        if decimal_odds <= 1.0:
            raise ValueError(
                f"decimal_odds must be > 1 for fractional conversion, got {decimal_odds}"
            )
        # Express (decimal - 1) as a fraction, then simplify
        # Multiply by 100 to avoid floating-point issues, then reduce
        numerator = round((decimal_odds - 1) * 100)
        denominator = 100
        gcd = math.gcd(numerator, denominator)
        return numerator // gcd, denominator // gcd

    @staticmethod
    def decimal_to_american(decimal_odds: float) -> int:
        """Convert decimal odds to American (moneyline) odds.

        Args:
            decimal_odds: Decimal odds (e.g. 2.50).

        Returns:
            American odds as an integer (positive or negative).

        Raises:
            ValueError: If *decimal_odds* <= 1.
        """
        if decimal_odds <= 1.0:
            raise ValueError(
                f"decimal_odds must be > 1, got {decimal_odds}"
            )
        if decimal_odds >= 2.0:
            return round((decimal_odds - 1) * 100)
        return round(-100 / (decimal_odds - 1))

    @staticmethod
    def american_to_decimal(american_odds: int) -> float:
        """Convert American (moneyline) odds to decimal.

        Args:
            american_odds: Positive or negative moneyline value.

        Returns:
            Equivalent decimal odds.

        Raises:
            ValueError: If *american_odds* is zero.
        """
        if american_odds == 0:
            raise ValueError("american_odds cannot be zero.")
        if american_odds > 0:
            return round(american_odds / 100 + 1, 4)
        return round(100 / abs(american_odds) + 1, 4)

    @staticmethod
    def fractional_to_decimal(numerator: int, denominator: int) -> float:
        """Convert fractional odds to decimal.

        Args:
            numerator: Fraction numerator (e.g. 3 in 3/2).
            denominator: Fraction denominator (e.g. 2 in 3/2).

        Returns:
            Equivalent decimal odds.

        Raises:
            ValueError: If *denominator* is zero or values are negative.
        """
        if denominator == 0:
            raise ValueError("denominator cannot be zero.")
        if numerator < 0 or denominator < 0:
            raise ValueError("numerator and denominator must be non-negative.")
        return round(numerator / denominator + 1, 4)

    # ------------------------------------------------------------------
    # Payout calculations
    # ------------------------------------------------------------------

    @staticmethod
    def calculate_payout(stake: float, decimal_odds: float) -> dict[str, float]:
        """Calculate payout and profit for a single bet.

        Args:
            stake: Amount wagered.
            decimal_odds: Decimal odds for the selection.

        Returns:
            Dict with keys ``stake``, ``decimal_odds``, ``payout``,
            ``profit``, and ``implied_probability``.

        Raises:
            ValueError: If *stake* is negative or *decimal_odds* <= 0.
        """
        if stake < 0:
            raise ValueError(f"stake must be non-negative, got {stake}")
        if decimal_odds <= 0:
            raise ValueError(
                f"decimal_odds must be positive, got {decimal_odds}"
            )
        payout = round(stake * decimal_odds, 2)
        profit = round(payout - stake, 2)
        implied_prob = round(1.0 / decimal_odds, 4)
        return {
            "stake": stake,
            "decimal_odds": decimal_odds,
            "payout": payout,
            "profit": profit,
            "implied_probability": implied_prob,
        }

    @staticmethod
    def calculate_accumulator(
        stake: float, odds_list: Sequence[float]
    ) -> dict[str, float | int]:
        """Calculate the combined odds and payout for a parlay / accumulator.

        Args:
            stake: Amount wagered on the accumulator.
            odds_list: Decimal odds for each leg.

        Returns:
            Dict with ``stake``, ``num_legs``, ``combined_odds``,
            ``payout``, ``profit``, and ``implied_probability``.

        Raises:
            ValueError: If *stake* < 0, *odds_list* is empty, or any
                odds value is <= 1.
        """
        if stake < 0:
            raise ValueError(f"stake must be non-negative, got {stake}")
        if not odds_list:
            raise ValueError("odds_list must not be empty.")
        for o in odds_list:
            if o <= 1.0:
                raise ValueError(
                    f"All decimal odds must be > 1 for an accumulator, got {o}"
                )
        combined = 1.0
        for o in odds_list:
            combined *= o
        combined = round(combined, 4)
        payout = round(stake * combined, 2)
        profit = round(payout - stake, 2)
        implied_prob = round(1.0 / combined, 6) if combined > 0 else 0.0
        return {
            "stake": stake,
            "num_legs": len(odds_list),
            "combined_odds": combined,
            "payout": payout,
            "profit": profit,
            "implied_probability": implied_prob,
        }

    @staticmethod
    def kelly_criterion(
        decimal_odds: float,
        win_probability: float,
        bankroll: float = 1.0,
        fractional_kelly: float = 1.0,
    ) -> dict[str, float]:
        """Calculate the Kelly Criterion optimal stake.

        ``f* = (p * (odds - 1) - (1 - p)) / (odds - 1)``

        where *p* is the estimated win probability and *odds* are decimal.

        Args:
            decimal_odds: Decimal odds offered.
            win_probability: Estimated probability of winning (0, 1).
            bankroll: Total bankroll (default 1.0 = fractional result).
            fractional_kelly: Fraction of full Kelly to use (e.g. 0.5 for
                half-Kelly). Default 1.0.

        Returns:
            Dict with ``decimal_odds``, ``win_probability``,
            ``edge``, ``kelly_fraction``, ``recommended_stake``,
            and ``bankroll``.

        Raises:
            ValueError: On invalid inputs.
        """
        if decimal_odds <= 1.0:
            raise ValueError(
                f"decimal_odds must be > 1, got {decimal_odds}"
            )
        if not 0 < win_probability < 1:
            raise ValueError(
                f"win_probability must be in (0, 1), got {win_probability}"
            )
        if bankroll <= 0:
            raise ValueError(f"bankroll must be positive, got {bankroll}")
        if not 0 < fractional_kelly <= 1:
            raise ValueError(
                f"fractional_kelly must be in (0, 1], got {fractional_kelly}"
            )

        b = decimal_odds - 1  # net odds (profit per unit staked)
        q = 1 - win_probability
        kelly_f = (win_probability * b - q) / b
        kelly_f = max(kelly_f, 0.0)  # never recommend negative stake

        edge = round(win_probability * decimal_odds - 1, 4)
        adjusted = round(kelly_f * fractional_kelly, 4)
        recommended = round(adjusted * bankroll, 2)

        return {
            "decimal_odds": decimal_odds,
            "win_probability": win_probability,
            "edge": edge,
            "kelly_fraction": adjusted,
            "recommended_stake": recommended,
            "bankroll": bankroll,
        }

    @staticmethod
    def dutching_calculator(
        total_stake: float, odds_list: Sequence[float]
    ) -> dict[str, object]:
        """Calculate individual stakes to equalise profit across outcomes.

        Dutching distributes a total stake across multiple selections so
        that the *profit* is the same regardless of which selection wins.

        ``stake_i = total_stake * (1 / odds_i) / sum(1 / odds_j)``

        Args:
            total_stake: Total amount to distribute.
            odds_list: Decimal odds for each selection.

        Returns:
            Dict with ``total_stake``, ``stakes`` (list of individual
            stakes), ``equal_payout``, ``profit``, and ``margin``.

        Raises:
            ValueError: If *total_stake* <= 0, *odds_list* is empty,
                or any odds value is <= 0.
        """
        if total_stake <= 0:
            raise ValueError(
                f"total_stake must be positive, got {total_stake}"
            )
        if not odds_list:
            raise ValueError("odds_list must not be empty.")
        for o in odds_list:
            if o <= 0:
                raise ValueError(
                    f"All odds must be positive, got {o}"
                )

        inv_sum = sum(1.0 / o for o in odds_list)
        stakes = [round(total_stake * (1.0 / o) / inv_sum, 2) for o in odds_list]
        # All selections yield the same payout: total_stake / inv_sum
        equal_payout = round(total_stake / inv_sum, 2)
        profit = round(equal_payout - total_stake, 2)
        margin = round(inv_sum - 1.0, 4)

        return {
            "total_stake": total_stake,
            "stakes": stakes,
            "equal_payout": equal_payout,
            "profit": profit,
            "margin": margin,
        }

    # ------------------------------------------------------------------
    # Bet slip builder
    # ------------------------------------------------------------------

    @staticmethod
    def build_bet_slip(
        selections: Sequence[dict],
        stake: float,
        bet_type: str = "single",
        bankroll: float = 1000.0,
        fractional_kelly: float = 0.5,
    ) -> dict[str, object]:
        """Build a bet slip from a list of selections and compute payouts.

        Each selection dict must contain at least a ``"decimal_odds"`` key
        (float > 1).  Additional keys (e.g. ``"match"``, ``"outcome"``)
        are passed through unchanged in the returned per-selection data.

        Args:
            selections: Sequence of dicts, each with ``"decimal_odds"``
                and optionally ``"win_probability"``.
            stake: Total amount wagered.
            bet_type: ``"single"`` (one bet per selection) or
                ``"accumulator"`` (all selections combined).
            bankroll: Bankroll for Kelly Criterion calculation.
            fractional_kelly: Fraction of full Kelly to use.

        Returns:
            Dict with ``bet_type``, ``stake``, ``selections`` (list of
            enriched dicts), ``combined_odds``, ``total_payout``, and
            ``total_profit``.

        Raises:
            ValueError: On invalid inputs.
        """
        if not selections:
            raise ValueError("selections must not be empty.")
        if stake < 0:
            raise ValueError(f"stake must be non-negative, got {stake}")
        if bet_type not in ("single", "accumulator"):
            raise ValueError(
                f"bet_type must be 'single' or 'accumulator', got '{bet_type}'"
            )

        enriched: list[dict] = []
        combined_odds = 1.0

        for sel in selections:
            odds = sel.get("decimal_odds")
            if odds is None or odds <= 1.0:
                raise ValueError(
                    f"Each selection must have decimal_odds > 1, got {odds}"
                )
            implied_prob = round(1.0 / odds, 4)
            entry: dict = {**sel, "implied_probability": implied_prob}

            # Kelly recommendation when win_probability is provided
            win_prob = sel.get("win_probability")
            if win_prob is not None and 0 < win_prob < 1:
                b = odds - 1
                q = 1.0 - win_prob
                kf = max((win_prob * b - q) / b, 0.0)
                kf_adj = round(kf * fractional_kelly, 4)
                entry["kelly_stake"] = round(kf_adj * bankroll, 2)
            else:
                entry["kelly_stake"] = None

            combined_odds *= odds
            enriched.append(entry)

        combined_odds = round(combined_odds, 4)

        if bet_type == "accumulator":
            total_payout = round(stake * combined_odds, 2)
            total_profit = round(total_payout - stake, 2)
        else:  # single — stake applied to each selection independently
            total_payout = round(
                sum(stake * sel["decimal_odds"] for sel in selections), 2
            )
            total_profit = round(total_payout - stake * len(selections), 2)

        return {
            "bet_type": bet_type,
            "stake": stake,
            "selections": enriched,
            "combined_odds": combined_odds,
            "total_payout": total_payout,
            "total_profit": total_profit,
        }

    # ------------------------------------------------------------------
    # Round-robin parlay calculator
    # ------------------------------------------------------------------

    @staticmethod
    def calculate_round_robin(
        stake_per_combo: float,
        odds_list: Sequence[float],
        combo_size: int,
    ) -> dict[str, object]:
        """Calculate all round-robin parlays of a given combination size.

        A round-robin takes *n* selections and builds every possible
        parlay of *combo_size* legs.  For example, 4 selections with
        ``combo_size=2`` produces ``C(4,2) = 6`` two-leg parlays.

        Args:
            stake_per_combo: Stake placed on each individual parlay.
            odds_list: Decimal odds for each selection (all must be > 1).
            combo_size: Number of legs per parlay (2 ≤ combo_size ≤ len).

        Returns:
            Dict with ``stake_per_combo``, ``num_combos``, ``total_staked``,
            ``combos`` (list of dicts with ``legs``, ``combined_odds``,
            ``payout``), ``total_payout_all_win``, and
            ``total_profit_all_win``.

        Raises:
            ValueError: On invalid inputs.
        """
        if stake_per_combo < 0:
            raise ValueError(
                f"stake_per_combo must be non-negative, got {stake_per_combo}"
            )
        if not odds_list:
            raise ValueError("odds_list must not be empty.")
        if combo_size < 2:
            raise ValueError(
                f"combo_size must be >= 2, got {combo_size}"
            )
        if combo_size > len(odds_list):
            raise ValueError(
                f"combo_size ({combo_size}) cannot exceed number of "
                f"selections ({len(odds_list)})."
            )
        for o in odds_list:
            if o <= 1.0:
                raise ValueError(
                    f"All decimal odds must be > 1, got {o}"
                )

        combos: list[dict] = []
        for indices in combinations(range(len(odds_list)), combo_size):
            combined = 1.0
            for i in indices:
                combined *= odds_list[i]
            combined = round(combined, 4)
            payout = round(stake_per_combo * combined, 2)
            combos.append(
                {
                    "legs": list(indices),
                    "combined_odds": combined,
                    "payout": payout,
                }
            )

        num_combos = len(combos)
        total_staked = round(stake_per_combo * num_combos, 2)
        total_payout = round(sum(c["payout"] for c in combos), 2)
        total_profit = round(total_payout - total_staked, 2)

        return {
            "stake_per_combo": stake_per_combo,
            "num_combos": num_combos,
            "total_staked": total_staked,
            "combos": combos,
            "total_payout_all_win": total_payout,
            "total_profit_all_win": total_profit,
        }
