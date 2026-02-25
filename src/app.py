"""Streamlit dashboard for the football odds analysis system."""

import logging
import sys
from pathlib import Path

# Ensure the project root is on sys.path so that ``src`` is importable
# when Streamlit rewrites sys.path[0] to the script's directory.
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import pandas as pd
import plotly.express as px
import streamlit as st

from src.api_client import OddsAPIClient
from src.analyzer import OddsAnalyzer
from src.bet_calculator import BetCalculator
from src.config import LEAGUES, SHARP_BOOKMAKERS
from src.db_manager import DBManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="⚽ Football Odds Analysis",
    page_icon="⚽",
    layout="wide",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@st.cache_resource
def get_db() -> DBManager:
    """Return a cached database manager instance."""
    return DBManager()


@st.cache_data(ttl=300)
def load_latest_odds(sport_key: str | None = None) -> pd.DataFrame:
    """Load the latest odds from the database (cached 5 min)."""
    db = get_db()
    rows = db.get_latest_odds(sport_key)
    return pd.DataFrame(rows) if rows else pd.DataFrame()


@st.cache_data(ttl=300)
def load_upcoming_matches(sport_key: str | None = None) -> pd.DataFrame:
    """Load upcoming matches from the database (cached 5 min)."""
    db = get_db()
    rows = db.get_upcoming_matches(sport_key)
    return pd.DataFrame(rows) if rows else pd.DataFrame()


def fetch_and_store(selected_leagues: list[str]) -> int:
    """Fetch odds from the API and persist them.

    Args:
        selected_leagues: Display names of leagues to fetch.

    Returns:
        Number of odds rows stored.
    """
    client = OddsAPIClient()
    db = get_db()
    all_rows: list[dict] = []
    league_map = {v: k for k, v in LEAGUES.items()}

    for sport_key in selected_leagues:
        league_name = league_map.get(sport_key, sport_key)
        with st.spinner(f"Fetching {league_name}…"):
            rows = client.fetch_odds(sport_key)
            all_rows.extend(rows)

    if all_rows:
        db.store_odds(all_rows)
        # Clear caches so new data is reflected immediately
        load_latest_odds.clear()
        load_upcoming_matches.clear()

    return len(all_rows)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

st.sidebar.title("⚙️ Settings")

league_options = {name: key for name, key in LEAGUES.items()}
selected_league_names: list[str] = st.sidebar.multiselect(
    "Select Leagues",
    options=list(league_options.keys()),
    default=list(league_options.keys()),
)
selected_sport_keys: list[str] = [
    league_options[n] for n in selected_league_names
]

if st.sidebar.button("🔄 Refresh Data"):
    if not selected_sport_keys:
        st.sidebar.warning("Please select at least one league.")
    else:
        count = fetch_and_store(selected_sport_keys)
        if count:
            st.sidebar.success(f"Stored {count} odds rows.")
        else:
            st.sidebar.warning("No data returned. Check your API key.")

# ---------------------------------------------------------------------------
# Main content
# ---------------------------------------------------------------------------

st.title("⚽ Football Odds Analysis Dashboard")

tab_matches, tab_value, tab_arb, tab_movement, tab_margin, tab_builder, tab_calc = (
    st.tabs(
        [
            "📅 Matches",
            "💡 Value Bets",
            "🔄 Arbitrage",
            "📈 Movement",
            "📊 Margins",
            "🎯 Bet Builder",
            "🧮 Calculator",
        ]
    )
)

analyzer = OddsAnalyzer()

# Always load all data from DB, then filter by selected leagues in-app.
odds_df_all = load_latest_odds()
upcoming_df_all = load_upcoming_matches()

if selected_sport_keys and len(selected_sport_keys) < len(LEAGUES):
    odds_df = (
        odds_df_all[odds_df_all["sport_key"].isin(selected_sport_keys)]
        if not odds_df_all.empty
        else odds_df_all
    )
    upcoming_df_base = (
        upcoming_df_all[upcoming_df_all["sport_key"].isin(selected_sport_keys)]
        if not upcoming_df_all.empty
        else upcoming_df_all
    )
else:
    odds_df = odds_df_all
    upcoming_df_base = upcoming_df_all

# ---------------------------------------------------------------------------
# Tab 1: Upcoming Matches
# ---------------------------------------------------------------------------
with tab_matches:
    st.subheader("Upcoming Matches")
    upcoming_df = upcoming_df_base

    if upcoming_df.empty:
        st.info(
            "No upcoming matches in the database. "
            "Use **Refresh Data** in the sidebar to fetch odds."
        )
    else:
        st.metric("Matches available", len(upcoming_df))

        if not odds_df.empty:
            # Show best available odds for h2h markets
            h2h = odds_df[odds_df["market"] == "h2h"]
            if not h2h.empty:
                best = (
                    h2h.groupby(["match_id", "outcome_name"])["outcome_price"]
                    .max()
                    .unstack("outcome_name")
                    .reset_index()
                )
                display = upcoming_df[
                    ["match_id", "league", "home_team", "away_team",
                     "commence_time"]
                ].merge(best, on="match_id", how="left")
                st.dataframe(display, use_container_width=True)
            else:
                st.dataframe(
                    upcoming_df[
                        ["league", "home_team", "away_team", "commence_time"]
                    ],
                    use_container_width=True,
                )
        else:
            st.dataframe(
                upcoming_df[
                    ["league", "home_team", "away_team", "commence_time"]
                ],
                use_container_width=True,
            )

# ---------------------------------------------------------------------------
# Tab 2: Value Bets
# ---------------------------------------------------------------------------
with tab_value:
    st.subheader("Value Bets")
    if odds_df.empty:
        st.info("No odds data available. Refresh data first.")
    else:
        threshold = st.slider(
            "Minimum edge threshold", 0.01, 0.20, 0.05, 0.01,
            key="value_threshold",
        )
        value_df = analyzer.find_value_bets(
            odds_df, sharp_bookmakers=SHARP_BOOKMAKERS, threshold=threshold
        )
        if value_df.empty:
            st.success(
                "No value bets found at the current threshold. "
                "Try lowering the threshold."
            )
        else:
            st.metric("Value bets found", len(value_df))
            # Highlight edge column
            styled = value_df.style.background_gradient(
                subset=["edge"], cmap="Greens"
            )
            st.dataframe(styled, use_container_width=True)

# ---------------------------------------------------------------------------
# Tab 3: Arbitrage Scanner
# ---------------------------------------------------------------------------
with tab_arb:
    st.subheader("Arbitrage Opportunities")
    if odds_df.empty:
        st.info("No odds data available. Refresh data first.")
    else:
        arb_df = analyzer.find_arbitrage(odds_df)
        if arb_df.empty:
            st.success("No arbitrage opportunities found in current data.")
        else:
            st.metric("Arbitrage opportunities", len(arb_df))
            display_arb = arb_df[
                ["home_team", "away_team", "commence_time", "market",
                 "arb_pct"]
            ].copy()
            display_arb.columns = [
                "Home", "Away", "Kick-off", "Market", "Profit %"
            ]
            st.dataframe(
                display_arb.style.format({"Profit %": "{:.4f}%"}),
                use_container_width=True,
            )

            st.markdown("### Best Odds per Opportunity")
            for _, row in arb_df.iterrows():
                with st.expander(
                    f"{row['home_team']} vs {row['away_team']} "
                    f"({row['market']}) — {row['arb_pct']:.4f}% profit"
                ):
                    st.json(row["best_odds"])

# ---------------------------------------------------------------------------
# Tab 4: Odds Movement
# ---------------------------------------------------------------------------
with tab_movement:
    st.subheader("Odds Movement")
    upcoming_df2 = upcoming_df_base

    if upcoming_df2.empty:
        st.info("No matches in the database.")
    else:
        match_labels = {
            f"{r['home_team']} vs {r['away_team']}": r["match_id"]
            for _, r in upcoming_df2.iterrows()
        }
        selected_match_label = st.selectbox(
            "Select Match", options=list(match_labels.keys())
        )
        selected_match_id = match_labels[selected_match_label]

        db2 = get_db()
        history = db2.get_odds_history(selected_match_id)
        hist_df = pd.DataFrame(history)

        if hist_df.empty:
            st.info("No historical odds for this match yet.")
        else:
            bookmakers = sorted(hist_df["bookmaker"].unique())
            selected_book = st.selectbox("Select Bookmaker", bookmakers)

            filtered = hist_df[
                (hist_df["bookmaker"] == selected_book)
                & (hist_df["market"] == "h2h")
            ]

            if filtered.empty:
                st.info("No h2h odds history for this bookmaker.")
            else:
                fig = px.line(
                    filtered,
                    x="timestamp",
                    y="outcome_price",
                    color="outcome_name",
                    title=f"Odds Movement – {selected_book}",
                    labels={
                        "timestamp": "Time",
                        "outcome_price": "Decimal Odds",
                        "outcome_name": "Outcome",
                    },
                    markers=True,
                )
                st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Tab 5: Margin Analysis
# ---------------------------------------------------------------------------
with tab_margin:
    st.subheader("Bookmaker Margin Analysis")
    if odds_df.empty:
        st.info("No odds data available. Refresh data first.")
    else:
        h2h_df = odds_df[odds_df["market"] == "h2h"]
        if h2h_df.empty:
            st.info("No 1X2 odds data available.")
        else:
            margins: list[dict] = []
            for (match_id, bookmaker), grp in h2h_df.groupby(
                ["match_id", "bookmaker"]
            ):
                prices = grp["outcome_price"].tolist()
                if len(prices) >= 2:  # noqa: PLR2004
                    try:
                        margin = analyzer.calculate_margin(prices)
                        margins.append(
                            {
                                "bookmaker": bookmaker,
                                "margin": margin * 100,
                            }
                        )
                    except ValueError:
                        continue

            if margins:
                margin_df = pd.DataFrame(margins)
                avg_margin = (
                    margin_df.groupby("bookmaker")["margin"]
                    .mean()
                    .reset_index()
                    .sort_values("margin")
                )

                fig_bar = px.bar(
                    avg_margin,
                    x="bookmaker",
                    y="margin",
                    title="Average Bookmaker Margin (%) – 1X2 Markets",
                    labels={
                        "bookmaker": "Bookmaker",
                        "margin": "Avg Margin (%)",
                    },
                    color="margin",
                    color_continuous_scale="RdYlGn_r",
                )
                fig_bar.update_layout(showlegend=False)
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("Insufficient data to compute margins.")

# ---------------------------------------------------------------------------
# Tab 6: Custom Bet Builder
# ---------------------------------------------------------------------------

# Initialise bet slip in session state
if "bet_slip" not in st.session_state:
    st.session_state["bet_slip"] = []

with tab_builder:
    st.subheader("Custom Bet Builder")
    st.markdown(
        "Pick outcomes from available matches and build a single bet or "
        "accumulator with real odds."
    )

    bet_calc_builder = BetCalculator()

    if odds_df.empty:
        st.info(
            "No odds data available. Use **Refresh Data** in the sidebar "
            "to fetch odds first."
        )
    else:
        h2h_builder = odds_df[odds_df["market"] == "h2h"]
        if h2h_builder.empty:
            st.info("No 1X2 odds available to build bets from.")
        else:
            # Build match labels
            match_info = (
                h2h_builder[["match_id", "home_team", "away_team", "league"]]
                .drop_duplicates("match_id")
                .reset_index(drop=True)
            )
            match_info["label"] = (
                match_info["home_team"]
                + " vs "
                + match_info["away_team"]
                + " ("
                + match_info["league"]
                + ")"
            )
            label_to_id = dict(
                zip(match_info["label"], match_info["match_id"])
            )

            st.markdown("#### Add a Selection")
            col_m, col_o, col_b = st.columns([3, 2, 2])
            with col_m:
                sel_match_label = st.selectbox(
                    "Match",
                    options=list(label_to_id.keys()),
                    key="builder_match",
                )
            sel_match_id = label_to_id.get(sel_match_label, "")

            # Available outcomes for selected match
            match_h2h = h2h_builder[h2h_builder["match_id"] == sel_match_id]
            outcomes = sorted(match_h2h["outcome_name"].unique())
            bookmakers = sorted(match_h2h["bookmaker"].unique())

            with col_o:
                sel_outcome = st.selectbox(
                    "Outcome", options=outcomes, key="builder_outcome"
                )
            with col_b:
                sel_bookmaker = st.selectbox(
                    "Bookmaker", options=bookmakers, key="builder_book"
                )

            # Find the specific odds row
            specific = match_h2h[
                (match_h2h["outcome_name"] == sel_outcome)
                & (match_h2h["bookmaker"] == sel_bookmaker)
            ]
            if not specific.empty:
                sel_odds = float(specific.iloc[0]["outcome_price"])
                st.markdown(
                    f"**Selected odds:** `{sel_odds:.2f}` "
                    f"({sel_outcome} @ {sel_bookmaker})"
                )
            else:
                sel_odds = None
                st.warning("No odds found for this combination.")

            if st.button("➕ Add to Bet Slip", key="btn_add_slip"):
                if sel_odds is not None and sel_odds > 1.0:
                    st.session_state["bet_slip"].append(
                        {
                            "match": sel_match_label,
                            "outcome": sel_outcome,
                            "bookmaker": sel_bookmaker,
                            "decimal_odds": sel_odds,
                        }
                    )
                    st.success(
                        f"Added: {sel_outcome} ({sel_match_label}) "
                        f"@ {sel_odds:.2f}"
                    )
                else:
                    st.error("Cannot add — no valid odds selected.")

    # --- Bet Slip Display ---
    st.markdown("---")
    st.markdown("#### 🗒️ Your Bet Slip")
    slip = st.session_state["bet_slip"]

    if not slip:
        st.info("Your bet slip is empty. Add selections above.")
    else:
        slip_df = pd.DataFrame(slip)
        slip_df.index = range(1, len(slip_df) + 1)
        slip_df.index.name = "#"
        st.dataframe(
            slip_df.rename(
                columns={
                    "match": "Match",
                    "outcome": "Outcome",
                    "bookmaker": "Bookmaker",
                    "decimal_odds": "Odds",
                }
            ),
            use_container_width=True,
        )

        col_type, col_stake = st.columns(2)
        with col_type:
            builder_bet_type = st.radio(
                "Bet Type",
                ["Single (each selection)", "Accumulator (combined)"],
                key="builder_bet_type",
                horizontal=True,
            )
        with col_stake:
            builder_stake = st.number_input(
                "Stake ($)", min_value=0.0, value=10.0, step=5.0,
                key="builder_stake",
            )

        col_calc, col_clear = st.columns(2)
        with col_calc:
            if st.button("💰 Calculate Payout", key="btn_calc_slip"):
                bt = (
                    "single"
                    if builder_bet_type.startswith("Single")
                    else "accumulator"
                )
                result = bet_calc_builder.build_bet_slip(
                    slip, builder_stake, bet_type=bt,
                )
                st.markdown("##### Results")
                r1, r2, r3 = st.columns(3)
                r1.metric("Combined Odds", f"{result['combined_odds']:.4f}")
                r2.metric("Total Payout", f"${result['total_payout']:.2f}")
                r3.metric("Total Profit", f"${result['total_profit']:.2f}")

                if bt == "accumulator":
                    st.caption(
                        "Accumulator: all selections must win for a payout."
                    )
                else:
                    st.caption(
                        "Single: stake is placed on each selection independently."
                    )
        with col_clear:
            if st.button("🗑️ Clear Bet Slip", key="btn_clear_slip"):
                st.session_state["bet_slip"] = []
                st.rerun()

# ---------------------------------------------------------------------------
# Tab 7: Custom Bet Calculator
# ---------------------------------------------------------------------------
with tab_calc:
    st.subheader("Custom Bet Calculator")

    bet_calc = BetCalculator()

    calc_section = st.radio(
        "Select Calculator",
        [
            "Single Bet",
            "Accumulator / Parlay",
            "Odds Converter",
            "Kelly Criterion",
            "Dutching",
        ],
        horizontal=True,
        key="calc_section",
    )

    # --- Single Bet ---
    if calc_section == "Single Bet":
        st.markdown("#### Single Bet Payout")
        col1, col2 = st.columns(2)
        with col1:
            sb_stake = st.number_input(
                "Stake", min_value=0.0, value=100.0, step=10.0,
                key="sb_stake",
            )
        with col2:
            sb_odds = st.number_input(
                "Decimal Odds", min_value=1.01, value=2.50, step=0.05,
                key="sb_odds",
            )
        if st.button("Calculate Payout", key="btn_single"):
            result = bet_calc.calculate_payout(sb_stake, sb_odds)
            c1, c2, c3 = st.columns(3)
            c1.metric("Payout", f"${result['payout']:.2f}")
            c2.metric("Profit", f"${result['profit']:.2f}")
            c3.metric("Implied Probability", f"{result['implied_probability']:.2%}")

    # --- Accumulator / Parlay ---
    elif calc_section == "Accumulator / Parlay":
        st.markdown("#### Accumulator / Parlay Calculator")
        acc_stake = st.number_input(
            "Stake", min_value=0.0, value=10.0, step=5.0,
            key="acc_stake",
        )
        num_legs = st.number_input(
            "Number of Legs", min_value=2, max_value=20, value=3, step=1,
            key="acc_legs",
        )
        leg_odds: list[float] = []
        cols = st.columns(min(int(num_legs), 5))
        for i in range(int(num_legs)):
            with cols[i % len(cols)]:
                val = st.number_input(
                    f"Leg {i + 1} Odds", min_value=1.01, value=2.0, step=0.05,
                    key=f"acc_leg_{i}",
                )
                leg_odds.append(val)
        if st.button("Calculate Accumulator", key="btn_acc"):
            result = bet_calc.calculate_accumulator(acc_stake, leg_odds)
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Combined Odds", f"{result['combined_odds']:.4f}")
            c2.metric("Payout", f"${result['payout']:.2f}")
            c3.metric("Profit", f"${result['profit']:.2f}")
            c4.metric("Implied Prob.", f"{result['implied_probability']:.4%}")

    # --- Odds Converter ---
    elif calc_section == "Odds Converter":
        st.markdown("#### Odds Format Converter")
        fmt = st.selectbox(
            "Input Format",
            ["Decimal", "American", "Fractional"],
            key="odds_fmt",
        )
        if fmt == "Decimal":
            dec = st.number_input(
                "Decimal Odds", min_value=1.01, value=2.50, step=0.05,
                key="conv_dec",
            )
            if st.button("Convert", key="btn_conv"):
                num, den = bet_calc.decimal_to_fractional(dec)
                american = bet_calc.decimal_to_american(dec)
                c1, c2, c3 = st.columns(3)
                c1.metric("Decimal", f"{dec:.2f}")
                c2.metric("Fractional", f"{num}/{den}")
                c3.metric("American", f"{american:+d}")
        elif fmt == "American":
            amer = st.number_input(
                "American Odds", value=150, step=10, key="conv_amer",
            )
            if amer == 0:
                st.warning("American odds cannot be zero.")
            elif st.button("Convert", key="btn_conv_a"):
                dec = bet_calc.american_to_decimal(int(amer))
                num, den = bet_calc.decimal_to_fractional(dec)
                c1, c2, c3 = st.columns(3)
                c1.metric("Decimal", f"{dec:.4f}")
                c2.metric("Fractional", f"{num}/{den}")
                c3.metric("American", f"{int(amer):+d}")
        else:  # Fractional
            fc1, fc2 = st.columns(2)
            with fc1:
                fnum = st.number_input(
                    "Numerator", min_value=1, value=3, step=1,
                    key="conv_fnum",
                )
            with fc2:
                fden = st.number_input(
                    "Denominator", min_value=1, value=2, step=1,
                    key="conv_fden",
                )
            if st.button("Convert", key="btn_conv_f"):
                dec = bet_calc.fractional_to_decimal(int(fnum), int(fden))
                american = bet_calc.decimal_to_american(dec)
                c1, c2, c3 = st.columns(3)
                c1.metric("Decimal", f"{dec:.4f}")
                c2.metric("Fractional", f"{int(fnum)}/{int(fden)}")
                c3.metric("American", f"{american:+d}")

    # --- Kelly Criterion ---
    elif calc_section == "Kelly Criterion":
        st.markdown("#### Kelly Criterion Stake Calculator")
        kc1, kc2 = st.columns(2)
        with kc1:
            kc_odds = st.number_input(
                "Decimal Odds", min_value=1.01, value=2.50, step=0.05,
                key="kc_odds",
            )
            kc_prob = st.slider(
                "Estimated Win Probability",
                0.01, 0.99, 0.50, 0.01,
                key="kc_prob",
            )
        with kc2:
            kc_bankroll = st.number_input(
                "Bankroll", min_value=1.0, value=1000.0, step=50.0,
                key="kc_bankroll",
            )
            kc_frac = st.slider(
                "Kelly Fraction (1 = full Kelly)",
                0.1, 1.0, 0.5, 0.1,
                key="kc_frac",
            )
        if st.button("Calculate Kelly Stake", key="btn_kelly"):
            result = bet_calc.kelly_criterion(
                kc_odds, kc_prob, kc_bankroll, kc_frac
            )
            c1, c2, c3 = st.columns(3)
            c1.metric("Edge", f"{result['edge']:.2%}")
            c2.metric("Kelly Fraction", f"{result['kelly_fraction']:.4f}")
            c3.metric(
                "Recommended Stake",
                f"${result['recommended_stake']:.2f}",
            )
            if result["edge"] <= 0:
                st.warning(
                    "⚠️ No positive edge detected — Kelly recommends no bet."
                )

    # --- Dutching ---
    else:
        st.markdown("#### Dutching Calculator")
        dt_stake = st.number_input(
            "Total Stake", min_value=1.0, value=100.0, step=10.0,
            key="dt_stake",
        )
        dt_num = st.number_input(
            "Number of Selections", min_value=2, max_value=10, value=3, step=1,
            key="dt_num",
        )
        dt_odds: list[float] = []
        cols_dt = st.columns(min(int(dt_num), 5))
        for i in range(int(dt_num)):
            with cols_dt[i % len(cols_dt)]:
                val = st.number_input(
                    f"Selection {i + 1} Odds",
                    min_value=1.01, value=3.00, step=0.10,
                    key=f"dt_odds_{i}",
                )
                dt_odds.append(val)
        if st.button("Calculate Dutching", key="btn_dutch"):
            result = bet_calc.dutching_calculator(dt_stake, dt_odds)
            c1, c2, c3 = st.columns(3)
            c1.metric("Equal Payout", f"${result['equal_payout']:.2f}")
            c2.metric("Profit", f"${result['profit']:.2f}")
            c3.metric("Market Margin", f"{result['margin']:.2%}")
            st.markdown("**Individual Stakes:**")
            stake_data = {
                f"Selection {i + 1} (@ {dt_odds[i]:.2f})": f"${s:.2f}"
                for i, s in enumerate(result["stakes"])
            }
            st.json(stake_data)
