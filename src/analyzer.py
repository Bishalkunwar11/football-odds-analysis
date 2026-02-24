"""Analysis engine: implied probability, margin, arbitrage, and value bets."""

import logging
from typing import Sequence

import pandas as pd

from src.config import SHARP_BOOKMAKERS

logger = logging.getLogger(__name__)


class OddsAnalyzer:
    """Performs mathematical analysis on odds data stored in DataFrames."""

    # ------------------------------------------------------------------
    # Core mathematics
    # ------------------------------------------------------------------

    @staticmethod
    def implied_probability(decimal_odds: float) -> float:
        """Convert decimal odds to implied probability.

        Args:
            decimal_odds: Decimal odds (e.g. 2.50).

        Returns:
            Implied probability in [0, 1].

        Raises:
            ValueError: If *decimal_odds* is not positive.
        """
        if decimal_odds <= 0:
            raise ValueError(
                f"decimal_odds must be positive, got {decimal_odds}"
            )
        return 1.0 / decimal_odds

    @staticmethod
    def calculate_margin(odds_list: Sequence[float]) -> float:
        """Calculate the bookmaker margin (vig / overround).

        Args:
            odds_list: Sequence of decimal odds for every outcome of a market.

        Returns:
            Margin as a fraction (e.g. 0.05 = 5 %).

        Raises:
            ValueError: If *odds_list* is empty or contains non-positive values.
        """
        if not odds_list:
            raise ValueError("odds_list must not be empty.")
        for o in odds_list:
            if o <= 0:
                raise ValueError(
                    f"All odds must be positive, got {o}"
                )
        return sum(1.0 / o for o in odds_list) - 1.0

    @staticmethod
    def calculate_fair_odds(odds_list: Sequence[float]) -> list[float]:
        """Remove the margin from a set of odds to obtain "fair" odds.

        Each fair odd is computed as: ``odd * sum(1/odd_i)``.

        Args:
            odds_list: Sequence of decimal odds for every outcome.

        Returns:
            List of fair (margin-free) decimal odds in the same order.

        Raises:
            ValueError: If *odds_list* is empty.
        """
        if not odds_list:
            raise ValueError("odds_list must not be empty.")
        total_implied = sum(1.0 / o for o in odds_list)
        return [o * total_implied for o in odds_list]

    # ------------------------------------------------------------------
    # DataFrame-level analysis
    # ------------------------------------------------------------------

    def find_arbitrage(
        self, match_odds_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Find arbitrage opportunities across bookmakers for each match.

        For each (match_id, market) pair the method collects the *best*
        (highest) price available across all bookmakers for every outcome.
        If ``sum(1 / best_prices) < 1`` an arbitrage exists.

        Args:
            match_odds_df: DataFrame with columns: match_id, home_team,
                away_team, commence_time, bookmaker, market, outcome_name,
                outcome_price.

        Returns:
            DataFrame of arbitrage opportunities with columns:
            match_id, home_team, away_team, commence_time, market,
            arb_pct, best_odds (dict str→float).
        """
        if match_odds_df.empty:
            return pd.DataFrame()

        required = {
            "match_id", "home_team", "away_team", "commence_time",
            "bookmaker", "market", "outcome_name", "outcome_price",
        }
        missing = required - set(match_odds_df.columns)
        if missing:
            raise ValueError(f"match_odds_df missing columns: {missing}")

        arb_rows: list[dict] = []

        # Only analyse h2h (1X2) and totals markets
        markets_to_check = match_odds_df["market"].unique()

        for (match_id, market), group in match_odds_df.groupby(
            ["match_id", "market"]
        ):
            if market not in markets_to_check:
                continue

            # Best price per outcome across all bookmakers
            best_prices = (
                group.groupby("outcome_name")["outcome_price"].max()
            )
            if best_prices.empty:
                continue

            inv_sum = sum(1.0 / p for p in best_prices.values if p > 0)

            if inv_sum < 1.0:
                arb_pct = round((1.0 / inv_sum - 1.0) * 100, 4)
                meta = group.iloc[0]
                arb_rows.append(
                    {
                        "match_id": match_id,
                        "home_team": meta["home_team"],
                        "away_team": meta["away_team"],
                        "commence_time": meta["commence_time"],
                        "market": market,
                        "arb_pct": arb_pct,
                        "best_odds": best_prices.to_dict(),
                    }
                )

        return pd.DataFrame(arb_rows)

    def get_consensus_line(
        self,
        match_odds_df: pd.DataFrame,
        sharp_books: list[str] | None = None,
    ) -> pd.DataFrame:
        """Average implied probabilities from sharp bookmakers.

        Args:
            match_odds_df: Full odds DataFrame (same schema as above).
            sharp_books: List of sharp bookmaker names (case-insensitive).
                Defaults to ``SHARP_BOOKMAKERS`` from config.

        Returns:
            DataFrame with columns: match_id, market, outcome_name,
            consensus_prob, consensus_fair_odds.
        """
        if sharp_books is None:
            sharp_books = SHARP_BOOKMAKERS

        if match_odds_df.empty:
            return pd.DataFrame()

        sharp_lower = [b.lower() for b in sharp_books]
        sharp_df = match_odds_df[
            match_odds_df["bookmaker"].str.lower().isin(sharp_lower)
        ]

        if sharp_df.empty:
            logger.warning(
                "No sharp bookmaker data found; falling back to all bookmakers."
            )
            sharp_df = match_odds_df

        consensus = (
            sharp_df.copy()
            .assign(
                implied_prob=lambda df: 1.0 / df["outcome_price"]
            )
            .groupby(["match_id", "market", "outcome_name"])["implied_prob"]
            .mean()
            .reset_index()
            .rename(columns={"implied_prob": "consensus_prob"})
        )

        consensus["consensus_fair_odds"] = 1.0 / consensus["consensus_prob"]
        return consensus

    def find_value_bets(
        self,
        match_odds_df: pd.DataFrame,
        sharp_bookmakers: list[str] | None = None,
        threshold: float = 0.05,
    ) -> pd.DataFrame:
        """Identify value bets by comparing bookmaker odds to the sharp line.

        A value bet exists when a bookmaker's implied probability is *lower*
        than the consensus (sharp) implied probability minus *threshold*,
        i.e. the bookmaker is offering better-than-fair odds.

        ``bookmaker_implied_prob < fair_implied_prob - threshold``

        Args:
            match_odds_df: Full odds DataFrame.
            sharp_bookmakers: Sharp bookmaker names for the consensus line.
            threshold: Minimum edge required (default: 0.05 = 5 %).

        Returns:
            DataFrame of value bets with columns: match_id, home_team,
            away_team, commence_time, market, outcome_name, bookmaker,
            outcome_price, bookmaker_prob, consensus_prob, edge.
        """
        if match_odds_df.empty:
            return pd.DataFrame()

        consensus = self.get_consensus_line(match_odds_df, sharp_bookmakers)
        if consensus.empty:
            return pd.DataFrame()

        df = match_odds_df.copy()
        df["bookmaker_prob"] = 1.0 / df["outcome_price"]

        merged = df.merge(
            consensus[["match_id", "market", "outcome_name", "consensus_prob"]],
            on=["match_id", "market", "outcome_name"],
            how="left",
        )

        value = merged[
            merged["bookmaker_prob"] < merged["consensus_prob"] - threshold
        ].copy()

        value["edge"] = (
            value["consensus_prob"] - value["bookmaker_prob"]
        ).round(4)

        cols = [
            "match_id", "home_team", "away_team", "commence_time",
            "market", "outcome_name", "bookmaker", "outcome_price",
            "bookmaker_prob", "consensus_prob", "edge",
        ]
        existing_cols = [c for c in cols if c in value.columns]
        return value[existing_cols].reset_index(drop=True)
