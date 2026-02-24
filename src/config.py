"""Configuration module: loads API keys and defines league/market constants."""

import os
from dotenv import load_dotenv

load_dotenv()

# The-Odds-API key from environment
ODDS_API_KEY: str = os.getenv("ODDS_API_KEY", "")

# Base URL for The-Odds-API v4
API_BASE_URL: str = "https://api.the-odds-api.com/v4/sports/"

# Supported leagues mapped to their API sport keys
LEAGUES: dict[str, str] = {
    "English Premier League": "soccer_epl",
    "La Liga": "soccer_spain_la_liga",
    "Serie A": "soccer_italy_serie_a",
    "Bundesliga": "soccer_germany_bundesliga",
    "Ligue 1": "soccer_france_ligue_one",
    "UEFA Champions League": "soccer_uefa_champs_league",
}

# Supported betting markets
MARKETS: list[str] = ["h2h", "totals"]

# Supported regions for odds
REGIONS: str = "us,uk,eu,au"

# Well-known sharp bookmakers used for consensus line calculation
SHARP_BOOKMAKERS: list[str] = ["pinnacle", "betfair_ex_eu", "betfair_ex_uk"]
