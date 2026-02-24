"""API client for fetching football odds from The-Odds-API."""

import logging
from typing import Any

import requests

from src.config import API_BASE_URL, LEAGUES, MARKETS, ODDS_API_KEY, REGIONS

logger = logging.getLogger(__name__)


class OddsAPIClient:
    """Client for The-Odds-API that fetches and parses odds data."""

    def __init__(self, api_key: str = ODDS_API_KEY) -> None:
        """Initialise the client with an API key.

        Args:
            api_key: The-Odds-API key. Defaults to value from environment.
        """
        self.api_key = api_key
        self.session = requests.Session()

    def fetch_odds(
        self,
        sport_key: str,
        markets: list[str] | None = None,
        regions: str = REGIONS,
    ) -> list[dict[str, Any]]:
        """Fetch odds for a specific sport/league.

        Args:
            sport_key: API sport key, e.g. ``soccer_epl``.
            markets: Betting markets to request (default: h2h and totals).
            regions: Comma-separated region string.

        Returns:
            List of parsed match dicts.
        """
        if markets is None:
            markets = MARKETS

        url = f"{API_BASE_URL}{sport_key}/odds/"
        params: dict[str, str] = {
            "apiKey": self.api_key,
            "regions": regions,
            "markets": ",".join(markets),
            "oddsFormat": "decimal",
            "dateFormat": "iso",
        }

        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
        except requests.exceptions.HTTPError as exc:
            logger.error("HTTP error fetching %s: %s", sport_key, exc)
            return []
        except requests.exceptions.RequestException as exc:
            logger.error("Request error fetching %s: %s", sport_key, exc)
            return []

        self._log_quota(response.headers)
        return self._parse_response(response.json(), sport_key)

    def fetch_all_leagues(self) -> list[dict[str, Any]]:
        """Fetch odds for all configured leagues.

        Returns:
            Combined list of parsed match dicts from every league.
        """
        all_matches: list[dict[str, Any]] = []
        for league_name, sport_key in LEAGUES.items():
            logger.info("Fetching odds for %s (%s)…", league_name, sport_key)
            matches = self.fetch_odds(sport_key)
            all_matches.extend(matches)
        return all_matches

    def _parse_response(
        self, data: list[dict[str, Any]], sport_key: str
    ) -> list[dict[str, Any]]:
        """Parse raw JSON response from The-Odds-API into a flat structure.

        Args:
            data: Raw list of event dicts returned by the API.
            sport_key: Sport key used for the request.

        Returns:
            List of match dicts with bookmaker odds flattened.
        """
        results: list[dict[str, Any]] = []

        for event in data:
            base = {
                "match_id": event.get("id", ""),
                "sport_key": event.get("sport_key", sport_key),
                "league": event.get("sport_title", ""),
                "home_team": event.get("home_team", ""),
                "away_team": event.get("away_team", ""),
                "commence_time": event.get("commence_time", ""),
            }

            for bookmaker in event.get("bookmakers", []):
                bookmaker_key = bookmaker.get("key", "")
                bookmaker_title = bookmaker.get("title", bookmaker_key)

                for market in bookmaker.get("markets", []):
                    market_key = market.get("key", "")
                    for outcome in market.get("outcomes", []):
                        row = dict(base)
                        row["bookmaker"] = bookmaker_title
                        row["market"] = market_key
                        row["outcome_name"] = outcome.get("name", "")
                        row["outcome_price"] = float(outcome.get("price", 0))
                        row["point"] = outcome.get("point")
                        results.append(row)

        return results

    def _log_quota(self, headers: requests.structures.CaseInsensitiveDict) -> None:
        """Log remaining API requests from response headers.

        Args:
            headers: HTTP response headers.
        """
        remaining = headers.get("x-requests-remaining")
        used = headers.get("x-requests-used")
        if remaining is not None:
            logger.info(
                "API quota – used: %s, remaining: %s", used, remaining
            )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    client = OddsAPIClient()
    matches = client.fetch_all_leagues()
    print(f"Fetched {len(matches)} odds rows across all leagues.")
