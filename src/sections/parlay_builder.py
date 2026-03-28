# src/sections/parlay_builder.py
"""Custom Parlay Builder section — multi-leg slip with payout modes."""

from __future__ import annotations

import streamlit as st

from src.bet_calculator import BetCalculator
from src.components.calculator_card import render_calculator_card
from src.components.common import render_section_banner
from src.components.parlay import render_parlay_leg, render_parlay_summary


def render() -> None:
    """Render the Custom Parlay Builder section."""
    st.markdown(
        render_section_banner(
            "Builder",
            "Custom Parlay Builder",
            "Assemble multi-leg slips and inspect payout profiles in real time.",
        ),
        unsafe_allow_html=True,
    )

    parlay_calc = BetCalculator()
    legs = st.session_state["parlay_legs"]

    # Running summary banner (always visible when legs exist)
    if legs:
        combined = 1.0
        for lg in legs:
            combined *= lg["decimal_odds"]
        combined = round(combined, 4)
        summary_stake = st.session_state.get("parlay_stake", 10.0)
        st.markdown(
            render_parlay_summary(len(legs), combined, summary_stake),
            unsafe_allow_html=True,
        )

    # Display existing legs
    if not legs:
        st.markdown(
            '<div class="empty-state">'
            '<div class="empty-icon">\U0001f3af</div>'
            '<div class="empty-text">No selections added yet.<br>'
            'Build your parlay by adding picks below.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<span style='font-size:0.78rem;color:var(--text-muted);"
            "font-weight:700;text-transform:uppercase;"
            "letter-spacing:0.15em;'>Selected Legs</span>",
            unsafe_allow_html=True,
        )
        for i, lg in enumerate(legs):
            leg_col, rm_col = st.columns([8, 1])
            with leg_col:
                prob = 1.0 / lg["decimal_odds"]
                st.markdown(
                    render_parlay_leg(i + 1, lg["label"], lg["decimal_odds"], prob),
                    unsafe_allow_html=True,
                )
            with rm_col:
                if st.button("\u2716", key=f"rm_leg_{i}", help=f"Remove {lg['label']}"):
                    st.session_state["parlay_legs"].pop(i)
                    st.rerun()

        if st.button("\U0001f5d1\ufe0f Clear All Picks", key="btn_clear_parlay"):
            st.session_state["parlay_legs"] = []
            st.rerun()

    # Add a leg card
    st.markdown(
        render_calculator_card(
            "\u2795", "Add a Leg", "Extend your parlay by adding another selection"
        ),
        unsafe_allow_html=True,
    )
    pc1, pc2 = st.columns([3, 3])
    with pc1:
        parlay_label = st.text_input(
            "Selection (e.g. Arsenal ML, Over 2.5 Goals)",
            key="parlay_label",
            placeholder="Selection Name",
        )
    with pc2:
        parlay_odds_fmt = st.selectbox(
            "Odds format",
            ["Decimal", "American", "Fractional"],
            key="parlay_odds_fmt",
        )

    if parlay_odds_fmt == "Decimal":
        parlay_dec = st.number_input(
            "Decimal Odds", min_value=1.01, value=2.00, step=0.05, key="parlay_dec"
        )
    elif parlay_odds_fmt == "American":
        parlay_amer = st.number_input(
            "American Odds", value=150, step=10, key="parlay_amer"
        )
        parlay_dec = (
            parlay_calc.american_to_decimal(int(parlay_amer))
            if parlay_amer != 0
            else 2.0
        )
    else:
        pf1, pf2 = st.columns(2)
        with pf1:
            parlay_num = st.number_input(
                "Numerator", min_value=1, value=3, step=1, key="parlay_fnum"
            )
        with pf2:
            parlay_den = st.number_input(
                "Denominator", min_value=1, value=2, step=1, key="parlay_fden"
            )
        parlay_dec = parlay_calc.fractional_to_decimal(int(parlay_num), int(parlay_den))

    implied = 1.0 / parlay_dec if parlay_dec > 0 else 0
    st.markdown(
        f"**Odds:** `{parlay_dec:.4f}` \u00b7 "
        f"**Implied probability:** `{implied:.1%}`"
    )

    if st.button(
        "\u2795 Add Leg to Parlay", key="btn_add_parlay_leg", use_container_width=True
    ):
        label = parlay_label.strip() or f"Leg {len(legs) + 1}"
        if parlay_dec > 1.0:
            st.session_state["parlay_legs"].append(
                {"label": label, "decimal_odds": round(parlay_dec, 4)}
            )
            st.success(f"Added: **{label}** @ {parlay_dec:.4f}")
        else:
            st.error("Odds must be greater than 1.0.")

    st.markdown("</div>", unsafe_allow_html=True)

    # Calculation options (only when legs exist)
    if not legs:
        return

    st.markdown(
        render_calculator_card(
            "\U0001f4b0",
            "Calculate Payout",
            "Choose your bet type and calculate potential returns",
        ),
        unsafe_allow_html=True,
    )

    parlay_mode = st.radio(
        "Bet type",
        ["Straight Parlay", "Round-Robin", "Singles"],
        horizontal=True,
        key="parlay_mode",
    )
    parlay_stake = st.number_input(
        "Stake ($)", min_value=0.0, value=10.0, step=5.0, key="parlay_stake"
    )
    odds_list = [lg["decimal_odds"] for lg in legs]

    if parlay_mode == "Straight Parlay":
        if st.button(
            "\U0001f4b8 Calculate Parlay", key="btn_calc_parlay", use_container_width=True
        ):
            result = parlay_calc.calculate_accumulator(parlay_stake, odds_list)
            st.markdown(
                '<div class="calc-result-box"><div class="calc-grid-3">'
                f'<div><div class="calc-result-label">Combined Odds</div>'
                f'<div class="calc-result-value">{result["combined_odds"]:.2f}x</div></div>'
                f'<div><div class="calc-result-label">Total Payout</div>'
                f'<div class="calc-result-value">${result["payout"]:.2f}</div></div>'
                f'<div><div class="calc-result-label">Profit</div>'
                f'<div class="calc-result-value">${result["profit"]:.2f}</div></div>'
                '</div>'
                f'<div style="margin-top:0.5rem;font-size:0.7rem;color:var(--text-muted);text-align:center;">'
                f'\u26a0\ufe0f All {len(legs)} legs must win \u00b7 '
                f'Implied: {result["implied_probability"]:.1%}'
                '</div></div>',
                unsafe_allow_html=True,
            )

    elif parlay_mode == "Round-Robin":
        max_combo = len(legs)
        combo_size = st.slider(
            "Legs per combo",
            min_value=2,
            max_value=max(max_combo, 2),
            value=min(2, max_combo),
            key="rr_combo_size",
        )
        if combo_size > len(legs):
            st.warning("Combo size cannot exceed the number of legs.")
        elif st.button(
            "\U0001f4b8 Calculate Round-Robin",
            key="btn_calc_rr",
            use_container_width=True,
        ):
            result = parlay_calc.calculate_round_robin(parlay_stake, odds_list, combo_size)
            st.markdown(
                '<div class="calc-result-box"><div class="calc-grid-3">'
                f'<div><div class="calc-result-label">Parlays</div>'
                f'<div class="calc-result-value">{result["num_combos"]}</div></div>'
                f'<div><div class="calc-result-label">Total Payout</div>'
                f'<div class="calc-result-value">${result["total_payout_all_win"]:.2f}</div></div>'
                f'<div><div class="calc-result-label">Profit</div>'
                f'<div class="calc-result-value">${result["total_profit_all_win"]:.2f}</div></div>'
                '</div>'
                f'<div style="margin-top:0.5rem;font-size:0.7rem;color:var(--text-muted);text-align:center;">'
                f'Total Staked: ${result["total_staked"]:.2f} \u00b7 '
                f'{result["num_combos"]} parlays of {combo_size} legs each'
                '</div></div>',
                unsafe_allow_html=True,
            )
            st.markdown("**Individual Parlays:**")
            for idx, combo in enumerate(result["combos"], 1):
                combo_labels = [legs[i]["label"] for i in combo["legs"]]
                with st.expander(
                    f"Parlay {idx}: {' + '.join(combo_labels)} \u2014 "
                    f"Odds {combo['combined_odds']:.4f} \u2192 ${combo['payout']:.2f}"
                ):
                    for i in combo["legs"]:
                        st.markdown(
                            f"- **{legs[i]['label']}** @ {legs[i]['decimal_odds']:.2f}"
                        )

    else:  # Singles
        if st.button(
            "\U0001f4b8 Calculate Singles",
            key="btn_calc_singles",
            use_container_width=True,
        ):
            st.markdown("**Single-Bet Payouts:**")
            total_payout = 0.0
            for lg in legs:
                res = parlay_calc.calculate_payout(parlay_stake, lg["decimal_odds"])
                total_payout += res["payout"]
                c1, c2, c3 = st.columns([3, 1, 1])
                c1.markdown(f"**{lg['label']}** @ {lg['decimal_odds']:.2f}")
                c2.metric("Payout", f"${res['payout']:.2f}")
                c3.metric("Profit", f"${res['profit']:.2f}")
            total_staked = parlay_stake * len(legs)
            st.markdown(
                '<div class="calc-result-box" style="margin-top:1rem;">'
                '<div class="calc-grid-2">'
                f'<div><div class="calc-result-label">Total Staked</div>'
                f'<div class="calc-result-value">${total_staked:.2f}</div></div>'
                f'<div><div class="calc-result-label">Total Payout (all win)</div>'
                f'<div class="calc-result-value">${total_payout:.2f}</div></div>'
                '</div></div>',
                unsafe_allow_html=True,
            )

    st.markdown("</div>", unsafe_allow_html=True)
