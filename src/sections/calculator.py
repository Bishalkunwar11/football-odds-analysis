# src/sections/calculator.py
"""Bet Calculator section — single, accumulator, converter, Kelly, dutching, EV."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.bet_calculator import BetCalculator
from src.components.common import render_section_banner
from src.components.slip_card import render_slip_card


def render(*, odds_df: pd.DataFrame) -> None:
    """Render the Bet Calculator section.

    Args:
        odds_df: Latest odds DataFrame (needed for the Bet Builder sub-mode).
    """
    st.markdown(
        render_section_banner(
            "Quant Tools",
            "Bet Calculator",
            "Run payout, Kelly, dutching, and conversion math with pro layouts.",
        ),
        unsafe_allow_html=True,
    )

    calc_mode = st.radio(
        "Mode",
        ["Calculator Tools", "Bet Builder"],
        horizontal=True,
        key="calc_mode",
    )

    if calc_mode == "Bet Builder":
        _render_bet_builder(odds_df=odds_df)
    else:
        _render_calculator_tools()


# ---------------------------------------------------------------------------
# Bet Builder sub-mode
# ---------------------------------------------------------------------------


def _render_bet_builder(*, odds_df: pd.DataFrame) -> None:
    st.markdown(
        "Pick outcomes from available matches and build a single bet or "
        "accumulator with real odds."
    )
    BetCalculator()

    if odds_df.empty:
        st.info(
            "No odds data available. Use **Refresh Data** in the sidebar "
            "to fetch odds first."
        )
    else:
        h2h = odds_df[odds_df["market"] == "h2h"]
        if h2h.empty:
            st.info("No 1X2 odds available to build bets from.")
        else:
            match_info = (
                h2h[["match_id", "home_team", "away_team", "league"]]
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
            label_to_id = dict(zip(match_info["label"], match_info["match_id"]))

            st.markdown("#### Add a Selection")
            col_m, col_o, col_b = st.columns([3, 2, 2])
            with col_m:
                sel_match_label = st.selectbox(
                    "Match", options=list(label_to_id.keys()), key="builder_match"
                )
            sel_match_id = label_to_id.get(sel_match_label, "")
            match_h2h = h2h[h2h["match_id"] == sel_match_id]
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

            if st.button("\u2795 Add to Bet Slip", key="btn_add_slip"):
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
                        f"Added: {sel_outcome} ({sel_match_label}) @ {sel_odds:.2f}"
                    )
                else:
                    st.error("Cannot add \u2014 no valid odds selected.")

    # Bet Slip display
    st.markdown("---")
    st.markdown("#### \U0001f5d2\ufe0f Your Bet Slip")
    slip = st.session_state["bet_slip"]

    if not slip:
        st.info("Your bet slip is empty. Add selections above.")
        return

    for sel in slip:
        st.markdown(
            render_slip_card(
                match=sel.get("match", ""),
                outcome=sel.get("outcome", ""),
                odds=sel["decimal_odds"],
            ),
            unsafe_allow_html=True,
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
            "Stake ($)", min_value=0.0, value=10.0, step=5.0, key="builder_stake"
        )

    col_calc, col_clear = st.columns(2)
    with col_calc:
        if st.button("\U0001f4b0 Calculate Payout", key="btn_calc_slip"):
            bt = "single" if builder_bet_type.startswith("Single") else "accumulator"
            result = BetCalculator().build_bet_slip(slip, builder_stake, bet_type=bt)
            st.markdown("##### Results")
            r1, r2, r3 = st.columns(3)
            r1.metric("Combined Odds", f"{result['combined_odds']:.4f}")
            r2.metric("Total Payout", f"${result['total_payout']:.2f}")
            r3.metric("Total Profit", f"${result['total_profit']:.2f}")
            if bt == "accumulator":
                st.caption("Accumulator: all selections must win for a payout.")
            else:
                st.caption("Single: stake is placed on each selection independently.")
    with col_clear:
        if st.button("\U0001f5d1\ufe0f Clear Bet Slip", key="btn_clear_slip"):
            st.session_state["bet_slip"] = []
            st.rerun()


# ---------------------------------------------------------------------------
# Calculator Tools sub-mode
# ---------------------------------------------------------------------------


def _render_calculator_tools() -> None:
    bet_calc = BetCalculator()

    tab_single, tab_acc, tab_conv, tab_kelly, tab_dutch, tab_ev = st.tabs([
        "\U0001f4b0 Single Bet",
        "\U0001f4ca Accumulator",
        "\U0001f504 Odds Converter",
        "\U0001f393 Kelly",
        "\u2696\ufe0f Dutching",
        "\U0001f4d0 EV Calculator",
    ])

    # --- Single Bet ---
    with tab_single:
        st.caption("Calculate payout, profit, and implied probability.")
        c1, c2 = st.columns(2)
        with c1:
            sb_stake = st.number_input(
                "Stake ($)", min_value=0.0, value=100.0, step=10.0, key="sb_stake"
            )
        with c2:
            sb_odds = st.number_input(
                "Decimal Odds", min_value=1.01, value=2.50, step=0.05, key="sb_odds"
            )
        if st.button("\U0001f4b8 Calculate Payout", key="btn_single", use_container_width=True):
            result = bet_calc.calculate_payout(sb_stake, sb_odds)
            st.markdown(
                '<div class="calc-result-box"><div class="calc-grid-3">'
                f'<div><div class="calc-result-label">Payout</div>'
                f'<div class="calc-result-value">${result["payout"]:.2f}</div></div>'
                f'<div><div class="calc-result-label">Profit</div>'
                f'<div class="calc-result-value">${result["profit"]:.2f}</div></div>'
                f'<div><div class="calc-result-label">Implied Prob.</div>'
                f'<div class="calc-result-value">{result["implied_probability"]:.1%}</div></div>'
                '</div></div>',
                unsafe_allow_html=True,
            )

    # --- Accumulator ---
    with tab_acc:
        st.caption("Combine multiple selections with multiplied odds.")
        col_stake, col_legs = st.columns(2)
        with col_stake:
            acc_stake = st.number_input(
                "Stake ($)", min_value=0.0, value=10.0, step=5.0, key="acc_stake"
            )
        with col_legs:
            num_legs = st.number_input(
                "Number of Legs", min_value=2, max_value=20, value=3, step=1,
                key="acc_legs",
            )
        leg_odds: list[float] = []
        cols_acc = st.columns(min(int(num_legs), 5))
        for i in range(int(num_legs)):
            with cols_acc[i % len(cols_acc)]:
                val = st.number_input(
                    f"Leg {i+1} Odds", min_value=1.01, value=2.0, step=0.05,
                    key=f"acc_leg_{i}",
                )
                leg_odds.append(val)
        if st.button("\U0001f3af Calculate Accumulator", key="btn_acc", use_container_width=True):
            result = bet_calc.calculate_accumulator(acc_stake, leg_odds)
            st.markdown(
                '<div class="calc-result-box"><div class="calc-grid-3">'
                f'<div><div class="calc-result-label">Combined Odds</div>'
                f'<div class="calc-result-value">{result["combined_odds"]:.2f}x</div></div>'
                f'<div><div class="calc-result-label">Payout</div>'
                f'<div class="calc-result-value">${result["payout"]:.2f}</div></div>'
                f'<div><div class="calc-result-label">Profit</div>'
                f'<div class="calc-result-value">${result["profit"]:.2f}</div></div>'
                '</div>'
                '<div style="margin-top:0.5rem;font-size:0.7rem;color:var(--text-muted);text-align:center;">'
                '\u26a0\ufe0f All selections must win for a payout'
                '</div></div>',
                unsafe_allow_html=True,
            )

    # --- Odds Converter ---
    with tab_conv:
        st.caption("Convert between decimal, American, and fractional formats.")
        fmt = st.selectbox(
            "Input Format", ["Decimal", "American", "Fractional"], key="odds_fmt"
        )
        if fmt == "Decimal":
            dec = st.number_input(
                "Decimal Odds", min_value=1.01, value=2.50, step=0.05, key="conv_dec"
            )
            if st.button("\u26a1 Convert", key="btn_conv", use_container_width=True):
                num, den = bet_calc.decimal_to_fractional(dec)
                american = bet_calc.decimal_to_american(dec)
                st.markdown(
                    '<div class="calc-result-box"><div class="calc-grid-3">'
                    f'<div><div class="calc-result-label">Decimal</div>'
                    f'<div class="calc-result-value">{dec:.2f}</div></div>'
                    f'<div><div class="calc-result-label">Fractional</div>'
                    f'<div class="calc-result-value">{num}/{den}</div></div>'
                    f'<div><div class="calc-result-label">American</div>'
                    f'<div class="calc-result-value">{american:+d}</div></div>'
                    '</div></div>',
                    unsafe_allow_html=True,
                )
        elif fmt == "American":
            amer = st.number_input("American Odds", value=150, step=10, key="conv_amer")
            if amer == 0:
                st.warning("American odds cannot be zero.")
            elif st.button("\u26a1 Convert", key="btn_conv_a", use_container_width=True):
                dec = bet_calc.american_to_decimal(int(amer))
                num, den = bet_calc.decimal_to_fractional(dec)
                st.markdown(
                    '<div class="calc-result-box"><div class="calc-grid-3">'
                    f'<div><div class="calc-result-label">Decimal</div>'
                    f'<div class="calc-result-value">{dec:.4f}</div></div>'
                    f'<div><div class="calc-result-label">Fractional</div>'
                    f'<div class="calc-result-value">{num}/{den}</div></div>'
                    f'<div><div class="calc-result-label">American</div>'
                    f'<div class="calc-result-value">{int(amer):+d}</div></div>'
                    '</div></div>',
                    unsafe_allow_html=True,
                )
        else:  # Fractional
            fc1, fc2 = st.columns(2)
            with fc1:
                fnum = st.number_input(
                    "Numerator", min_value=1, value=3, step=1, key="conv_fnum"
                )
            with fc2:
                fden = st.number_input(
                    "Denominator", min_value=1, value=2, step=1, key="conv_fden"
                )
            if st.button("\u26a1 Convert", key="btn_conv_f", use_container_width=True):
                dec = bet_calc.fractional_to_decimal(int(fnum), int(fden))
                american = bet_calc.decimal_to_american(dec)
                st.markdown(
                    '<div class="calc-result-box"><div class="calc-grid-3">'
                    f'<div><div class="calc-result-label">Decimal</div>'
                    f'<div class="calc-result-value">{dec:.4f}</div></div>'
                    f'<div><div class="calc-result-label">Fractional</div>'
                    f'<div class="calc-result-value">{int(fnum)}/{int(fden)}</div></div>'
                    f'<div><div class="calc-result-label">American</div>'
                    f'<div class="calc-result-value">{american:+d}</div></div>'
                    '</div></div>',
                    unsafe_allow_html=True,
                )

    # --- Kelly Criterion ---
    with tab_kelly:
        st.caption("Calculate optimal stake size based on your edge and bankroll.")
        kc1, kc2 = st.columns(2)
        with kc1:
            kc_odds = st.number_input(
                "Decimal Odds", min_value=1.01, value=2.50, step=0.05, key="kc_odds"
            )
            kc_prob = st.slider(
                "Estimated Win Probability", 0.01, 0.99, 0.50, 0.01, key="kc_prob"
            )
        with kc2:
            kc_bankroll = st.number_input(
                "Bankroll ($)", min_value=1.0, value=1000.0, step=50.0, key="kc_bankroll"
            )
            kc_frac = st.slider(
                "Kelly Fraction (1 = full Kelly)", 0.1, 1.0, 0.5, 0.1, key="kc_frac"
            )
        if st.button("\U0001f9ee Calculate Kelly Stake", key="btn_kelly", use_container_width=True):
            result = bet_calc.kelly_criterion(kc_odds, kc_prob, kc_bankroll, kc_frac)
            st.markdown(
                '<div class="calc-result-box"><div class="calc-grid-3">'
                f'<div><div class="calc-result-label">Your Edge</div>'
                f'<div class="calc-result-value">{result["edge"]:.2%}</div></div>'
                f'<div><div class="calc-result-label">Kelly %</div>'
                f'<div class="calc-result-value">{result["kelly_fraction"]:.2%}</div></div>'
                f'<div><div class="calc-result-label">Stake</div>'
                f'<div class="calc-result-value">${result["recommended_stake"]:.2f}</div></div>'
                '</div></div>',
                unsafe_allow_html=True,
            )
            if result["edge"] <= 0:
                st.markdown(
                    '<div style="margin-top:0.5rem;font-size:0.7rem;'
                    'color:var(--accent-red);text-align:center;">'
                    '\u26a0\ufe0f No positive edge \u2014 Kelly recommends no bet'
                    '</div>',
                    unsafe_allow_html=True,
                )

    # --- Dutching ---
    with tab_dutch:
        st.caption("Distribute stake across outcomes for equal profit regardless of result.")
        col_dt_stake, col_dt_num = st.columns(2)
        with col_dt_stake:
            dt_stake = st.number_input(
                "Total Stake ($)", min_value=1.0, value=100.0, step=10.0, key="dt_stake"
            )
        with col_dt_num:
            dt_num = st.number_input(
                "Number of Selections", min_value=2, max_value=10, value=3, step=1,
                key="dt_num",
            )
        dt_odds: list[float] = []
        cols_dt = st.columns(min(int(dt_num), 5))
        for i in range(int(dt_num)):
            with cols_dt[i % len(cols_dt)]:
                val = st.number_input(
                    f"Selection {i+1} Odds", min_value=1.01, value=3.00, step=0.10,
                    key=f"dt_odds_{i}",
                )
                dt_odds.append(val)
        if st.button("\u26a1 Calculate Dutching", key="btn_dutch", use_container_width=True):
            result = bet_calc.dutching_calculator(dt_stake, dt_odds)
            st.markdown(
                '<div class="calc-result-box"><div class="calc-grid-3">'
                f'<div><div class="calc-result-label">Equal Payout</div>'
                f'<div class="calc-result-value">${result["equal_payout"]:.2f}</div></div>'
                f'<div><div class="calc-result-label">Profit</div>'
                f'<div class="calc-result-value">${result["profit"]:.2f}</div></div>'
                f'<div><div class="calc-result-label">Market Margin</div>'
                f'<div class="calc-result-value">{result["margin"]:.2%}</div></div>'
                '</div></div>',
                unsafe_allow_html=True,
            )
            st.markdown("**Individual Stakes:**")
            stake_cols = st.columns(min(int(dt_num), 3))
            for i, s in enumerate(result["stakes"]):
                with stake_cols[i % len(stake_cols)]:
                    st.metric(
                        f"Selection {i+1}",
                        f"${s:.2f}",
                        delta=f"@ {dt_odds[i]:.2f}",
                        delta_color="off",
                    )

    # --- EV Calculator ---
    with tab_ev:
        _render_ev_calculator()


# ---------------------------------------------------------------------------
# EV Calculator sub-tab
# ---------------------------------------------------------------------------


def _render_ev_calculator() -> None:
    st.caption("Compute expected value, breakeven probability, and Kelly fractions.")

    ev1, ev2, ev3 = st.columns(3)
    with ev1:
        ev_odds = st.number_input(
            "Decimal Odds", min_value=1.01, value=2.50, step=0.05, key="ev_odds"
        )
    with ev2:
        ev_prob = st.slider(
            "Estimated Win Probability", 0.01, 0.99, 0.45, 0.01, key="ev_prob"
        )
    with ev3:
        ev_stake = st.number_input(
            "Stake ($)", min_value=0.01, value=100.0, step=10.0, key="ev_stake"
        )

    if not st.button("📐 Calculate EV", key="btn_ev_calc", use_container_width=True):
        return

    # Core calculations
    ev_dollar = (ev_prob * (ev_odds - 1.0) - (1.0 - ev_prob)) * ev_stake
    ev_pct = (ev_dollar / ev_stake * 100.0) if ev_stake > 0 else 0.0
    breakeven = 1.0 / ev_odds if ev_odds > 0 else 0.0

    # Kelly fractions (full, half, quarter)
    edge = ev_prob - breakeven
    kelly_full_pct = max(0.0, edge / (ev_odds - 1.0))
    kelly_half_pct = kelly_full_pct / 2.0
    kelly_quarter_pct = kelly_full_pct / 4.0

    is_positive = ev_dollar > 0
    card_bg = "rgba(0,214,143,0.08)" if is_positive else "rgba(255,59,92,0.08)"
    card_border = "var(--accent-green)" if is_positive else "var(--accent-red)"
    ev_color = "var(--accent-green)" if is_positive else "var(--accent-red)"
    ev_icon = "✅" if is_positive else "❌"

    st.markdown(
        f'<div style="background:{card_bg};border:1px solid {card_border};'
        f'border-radius:10px;padding:1rem 1.2rem;margin:0.8rem 0;">'
        f'<div style="font-size:0.69rem;color:var(--text-muted);font-weight:700;'
        f'text-transform:uppercase;letter-spacing:0.1em;margin-bottom:0.6rem;">'
        f'{ev_icon} Expected Value Result</div>'
        f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:0.8rem;">'
        f'<div><div style="font-size:0.69rem;color:var(--text-muted);'
        f'text-transform:uppercase;letter-spacing:0.06em;">EV ($)</div>'
        f'<div style="font-family:\'Barlow Condensed\',sans-serif;font-size:1.4rem;'
        f'font-weight:800;color:{ev_color};">'
        f'{"+" if ev_dollar >= 0 else ""}{ev_dollar:.2f}</div></div>'
        f'<div><div style="font-size:0.69rem;color:var(--text-muted);'
        f'text-transform:uppercase;letter-spacing:0.06em;">EV (%)</div>'
        f'<div style="font-family:\'Barlow Condensed\',sans-serif;font-size:1.4rem;'
        f'font-weight:800;color:{ev_color};">'
        f'{"+" if ev_pct >= 0 else ""}{ev_pct:.2f}%</div></div>'
        f'<div><div style="font-size:0.69rem;color:var(--text-muted);'
        f'text-transform:uppercase;letter-spacing:0.06em;">Breakeven</div>'
        f'<div style="font-family:\'Barlow Condensed\',sans-serif;font-size:1.4rem;'
        f'font-weight:800;color:var(--text-primary);">'
        f'{breakeven:.1%}</div></div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Kelly stakes grid
    st.markdown(
        '<span style="font-size:0.69rem;color:var(--text-muted);font-weight:700;'
        'text-transform:uppercase;letter-spacing:0.1em;">Kelly Stake Sizes</span>',
        unsafe_allow_html=True,
    )
    k1, k2, k3 = st.columns(3)
    k1.metric("Full Kelly", f"{kelly_full_pct:.2%}", help="Aggressive — max growth rate")
    k2.metric("Half Kelly", f"{kelly_half_pct:.2%}", help="Balanced risk/growth")
    k3.metric("Quarter Kelly", f"{kelly_quarter_pct:.2%}", help="Conservative bankroll protection")

    # Breakeven probability bar
    impl_pct = breakeven * 100.0
    user_pct = ev_prob * 100.0

    # Position markers as percentage of bar width (clamped 0–100)
    impl_pos = max(0.0, min(100.0, impl_pct))
    user_pos = max(0.0, min(100.0, user_pct))

    st.markdown(
        '<span style="font-size:0.69rem;color:var(--text-muted);font-weight:700;'
        'text-transform:uppercase;letter-spacing:0.1em;margin-top:0.6rem;'
        'display:block;">Probability Comparison</span>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div style="position:relative;height:28px;background:var(--bg-raised);'
        f'border-radius:6px;margin:0.4rem 0 1.2rem;overflow:visible;">'
        # Implied probability tick (red)
        f'<div style="position:absolute;left:{impl_pos}%;top:0;height:100%;'
        f'width:2px;background:var(--accent-red);border-radius:1px;">'
        f'<div style="position:absolute;top:-18px;left:50%;transform:translateX(-50%);'
        f'font-size:0.6rem;color:var(--accent-red);white-space:nowrap;font-weight:700;">'
        f'Implied {impl_pct:.1f}%</div></div>'
        # User probability tick (green)
        f'<div style="position:absolute;left:{user_pos}%;top:0;height:100%;'
        f'width:2px;background:var(--accent-green);border-radius:1px;">'
        f'<div style="position:absolute;bottom:-18px;left:50%;transform:translateX(-50%);'
        f'font-size:0.6rem;color:var(--accent-green);white-space:nowrap;font-weight:700;">'
        f'Your Est. {user_pct:.1f}%</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )
