"""Configuration module: loads API keys and defines league/market constants."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from the project root regardless of cwd.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

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

# ---------------------------------------------------------------------------
# UI display constants
# ---------------------------------------------------------------------------

# Stake quick-add button amounts (£/$ increments shown in the bet slip)
STAKE_QUICK_ADD: list[int] = [10, 50, 100, 1_000]

# KPI meter upper bounds (used to scale progress bars on the dashboard)
METER_LIMIT_MATCHES: int = 200
METER_LIMIT_VALUE_BETS: int = 50
METER_LIMIT_ARB_OPS: int = 20

# Default minimum edge % shown in the Value Bets section slider
DEFAULT_EDGE_THRESHOLD: float = 0.05
