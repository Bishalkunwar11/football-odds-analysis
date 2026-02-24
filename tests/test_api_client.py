"""Unit tests for OddsAPIClient."""

from unittest.mock import MagicMock, patch

import pytest

from src.api_client import OddsAPIClient


SAMPLE_EVENT = {
    "id": "abc123",
    "sport_key": "soccer_epl",
    "sport_title": "English Premier League",
    "home_team": "Arsenal",
    "away_team": "Chelsea",
    "commence_time": "2030-01-10T15:00:00Z",
    "bookmakers": [
        {
            "key": "pinnacle",
            "title": "Pinnacle",
            "markets": [
                {
                    "key": "h2h",
                    "outcomes": [
                        {"name": "Arsenal", "price": 2.10},
                        {"name": "Chelsea", "price": 3.50},
                        {"name": "Draw", "price": 3.20},
                    ],
                }
            ],
        },
        {
            "key": "bet365",
            "title": "Bet365",
            "markets": [
                {
                    "key": "totals",
                    "outcomes": [
                        {"name": "Over", "price": 1.90, "point": 2.5},
                        {"name": "Under", "price": 1.90, "point": 2.5},
                    ],
                }
            ],
        },
    ],
}


class TestParseResponse:
    def setup_method(self) -> None:
        self.client = OddsAPIClient(api_key="test-key")

    def test_parse_basic_structure(self) -> None:
        rows = self.client._parse_response([SAMPLE_EVENT], "soccer_epl")
        # 3 h2h outcomes from Pinnacle + 2 totals from Bet365
        assert len(rows) == 5

    def test_parse_match_fields(self) -> None:
        rows = self.client._parse_response([SAMPLE_EVENT], "soccer_epl")
        first = rows[0]
        assert first["match_id"] == "abc123"
        assert first["home_team"] == "Arsenal"
        assert first["away_team"] == "Chelsea"
        assert first["sport_key"] == "soccer_epl"
        assert first["league"] == "English Premier League"

    def test_parse_bookmaker_name(self) -> None:
        rows = self.client._parse_response([SAMPLE_EVENT], "soccer_epl")
        bookmakers = {r["bookmaker"] for r in rows}
        assert "Pinnacle" in bookmakers
        assert "Bet365" in bookmakers

    def test_parse_totals_point(self) -> None:
        rows = self.client._parse_response([SAMPLE_EVENT], "soccer_epl")
        totals = [r for r in rows if r["market"] == "totals"]
        assert len(totals) == 2
        assert totals[0]["point"] == 2.5

    def test_parse_h2h_no_point(self) -> None:
        rows = self.client._parse_response([SAMPLE_EVENT], "soccer_epl")
        h2h = [r for r in rows if r["market"] == "h2h"]
        for r in h2h:
            assert r["point"] is None

    def test_empty_response(self) -> None:
        rows = self.client._parse_response([], "soccer_epl")
        assert rows == []

    def test_event_with_no_bookmakers(self) -> None:
        event = {**SAMPLE_EVENT, "bookmakers": []}
        rows = self.client._parse_response([event], "soccer_epl")
        assert rows == []


class TestFetchOdds:
    def setup_method(self) -> None:
        self.client = OddsAPIClient(api_key="test-key")

    def test_fetch_returns_parsed_rows(self) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = [SAMPLE_EVENT]
        mock_response.headers = {
            "x-requests-remaining": "490",
            "x-requests-used": "10",
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(self.client.session, "get", return_value=mock_response):
            rows = self.client.fetch_odds("soccer_epl")

        assert len(rows) == 5

    def test_fetch_handles_http_error(self) -> None:
        import requests

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = (
            requests.exceptions.HTTPError("403")
        )

        with patch.object(self.client.session, "get", return_value=mock_response):
            rows = self.client.fetch_odds("soccer_epl")

        assert rows == []

    def test_fetch_handles_connection_error(self) -> None:
        import requests

        with patch.object(
            self.client.session,
            "get",
            side_effect=requests.exceptions.ConnectionError("no conn"),
        ):
            rows = self.client.fetch_odds("soccer_epl")

        assert rows == []
