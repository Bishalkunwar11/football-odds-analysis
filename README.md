# ⚽ Football Odds Analysis

A production-ready football (soccer) odds analysis system covering the top European competitions: **English Premier League, La Liga, Serie A, Bundesliga, Ligue 1, and the UEFA Champions League**.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Football Odds Analysis                       │
│                                                                 │
│  ┌─────────────┐    ┌──────────────┐    ┌──────────────────┐   │
│  │  The-Odds-  │───▶│  api_client  │───▶│   db_manager     │   │
│  │     API     │    │  (fetch &    │    │  (SQLite store)  │   │
│  └─────────────┘    │   parse)     │    └────────┬─────────┘   │
│                     └──────────────┘             │             │
│                                                  ▼             │
│                                        ┌──────────────────┐   │
│                                        │    analyzer      │   │
│                                        │  (vig, arb,      │   │
│                                        │   value bets)    │   │
│                                        └────────┬─────────┘   │
│                                                 │              │
│                                                 ▼              │
│                                        ┌──────────────────┐   │
│                                        │   app.py         │   │
│                                        │ (Streamlit UI)   │   │
│                                        └──────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Features

- **Live Odds Fetching** – pulls 1X2 (h2h) and Over/Under (totals) odds via The-Odds-API.
- **SQLite Persistence** – timestamped snapshots enable line-movement tracking.
- **Implied Probability** – converts decimal odds to probability.
- **Bookmaker Margin (Vig)** – calculates the overround for any market.
- **Arbitrage Scanner** – detects risk-free profit opportunities across bookmakers.
- **Value Bet Finder** – compares soft bookmakers against the sharp consensus line.
- **Custom Bet Calculator** – odds conversion, single bet & accumulator payouts, Kelly Criterion stake sizing, and dutching calculator.
- **Streamlit Dashboard** – 6-tab UI covering upcoming matches, value bets, arbitrage, odds movement charts, margin analysis, and bet calculator.

---

## Prerequisites

- Python 3.9+
- A free or paid API key from [The-Odds-API](https://the-odds-api.com/)

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/Bishalkunwar11/football-odds-analysis.git
cd football-odds-analysis

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Open .env and replace "your_api_key_here" with your actual API key
```

---

## Configuration

Edit the `.env` file:

```
ODDS_API_KEY=your_actual_api_key_here
```

---

## Running the System

### Fetch & store odds (one-time or scheduled)

```bash
python -m src.api_client
```

### Launch the Streamlit dashboard

```bash
streamlit run src/app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser, select leagues in the sidebar, and click **Refresh Data**.

---

## Running Tests

```bash
pytest tests/ -v
```

---

## Project Structure

```
football-odds-analysis/
├── src/
│   ├── __init__.py
│   ├── config.py           # API key & league/market constants
│   ├── api_client.py       # OddsAPIClient – fetch & parse JSON
│   ├── db_manager.py       # DBManager – SQLite schema & CRUD
│   ├── analyzer.py         # OddsAnalyzer – vig, arbitrage, value bets
│   ├── bet_calculator.py   # BetCalculator – payouts, parlays, Kelly, dutching
│   └── app.py              # Streamlit dashboard
├── data/                   # SQLite database storage (gitignored)
│   └── .gitkeep
├── tests/
│   ├── __init__.py
│   ├── test_analyzer.py
│   ├── test_api_client.py
│   ├── test_bet_calculator.py
│   └── test_db_manager.py
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Key Concepts

### Implied Probability
The probability implied by a bookmaker's odds:
```
implied_prob = 1 / decimal_odds
```

### Bookmaker Margin (Vig / Overround)
The built-in profit edge a bookmaker takes:
```
margin = sum(1 / odds_i) - 1
```
A fair book has margin = 0; most sportsbooks operate at 3–8 %.

### Arbitrage Betting
When the sum of the best (highest) implied probabilities across bookmakers is less than 1, a guaranteed profit exists regardless of the outcome:
```
arb_exists  ↔  sum(1 / best_odds_i) < 1
profit_pct  =  (1 / sum(1 / best_odds_i) - 1) × 100
```

### Value Betting
A value bet exists when a bookmaker's implied probability is lower than the sharp/consensus probability by more than a threshold *t*:
```
value_bet  ↔  bookmaker_prob < consensus_prob - t
edge       =  consensus_prob - bookmaker_prob
```

### Kelly Criterion
The Kelly Criterion calculates the optimal fraction of your bankroll to wager:
```
f* = (p × (odds − 1) − (1 − p)) / (odds − 1)
```
where *p* is the estimated win probability. Use fractional Kelly (e.g. half-Kelly) for reduced variance.

### Dutching
Dutching distributes a total stake across multiple selections so that the profit is the same regardless of which selection wins:
```
stake_i = total_stake × (1 / odds_i) / sum(1 / odds_j)
```

---

## Screenshots

*(Launch the dashboard and capture screenshots here)*

---

## License

MIT