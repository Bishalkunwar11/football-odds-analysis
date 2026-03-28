# src/sections/bankroll.py
"""Bankroll Tracker section — manual bet log, P&L chart, and KPI dashboard.

All data is stored in ``st.session_state`` — no database writes are performed.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.components.common import _apply_dark_theme, render_section_banner

# ---------------------------------------------------------------------------
# Session state keys used by this section
# ---------------------------------------------------------------------------
_BANKROLL_KEY = "bankroll_start"
_BET_LOG_KEY = "bet_log"


def _ensure_state() -> None:
    if _BANKROLL_KEY not in st.session_state:
        st.session_state[_BANKROLL_KEY] = 1000.0
    if _BET_LOG_KEY not in st.session_state:
        st.session_state[_BET_LOG_KEY] = []


# ---------------------------------------------------------------------------
# P&L helpers
# ---------------------------------------------------------------------------

def _calc_profit(result: str, stake: float, odds: float) -> float:
    if result == "W":
        return round((odds - 1.0) * stake, 4)
    if result == "L":
        return round(-stake, 4)
    return 0.0  # Void


def _build_log_df(bet_log: list[dict]) -> pd.DataFrame:
    """Return a DataFrame with a cumulative P&L column."""
    if not bet_log:
        return pd.DataFrame()

    rows = []
    running = 0.0
    for i, entry in enumerate(bet_log, 1):
        profit = _calc_profit(
            entry.get("result", "L"),
            float(entry.get("stake", 0.0)),
            float(entry.get("odds", 1.0)),
        )
        running = round(running + profit, 4)
        rows.append(
            {
                "#":          i,
                "Match":      entry.get("match", ""),
                "Outcome":    entry.get("outcome", ""),
                "Odds":       float(entry.get("odds", 1.0)),
                "Stake":      float(entry.get("stake", 0.0)),
                "Result":     entry.get("result", ""),
                "P&L":        profit,
                "Cum. P&L":   running,
            }
        )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Section entry point
# ---------------------------------------------------------------------------

def render() -> None:
    """Render the Bankroll Tracker section."""
    _ensure_state()

    st.markdown(
        render_section_banner(
            "Bankroll Manager",
            "\U0001f4bc Bankroll Tracker",
            "Log your bets, track cumulative P&L, and measure ROI over time.",
        ),
        unsafe_allow_html=True,
    )

    # ── a) Starting bankroll ─────────────────────────────────────────────────
    st.markdown(
        "<span style='font-size:0.72rem;color:var(--text-muted);"
        "font-weight:700;text-transform:uppercase;letter-spacing:0.12em;'>"
        "Starting Bankroll</span>",
        unsafe_allow_html=True,
    )
    bankroll_start = st.number_input(
        "Starting Bankroll ($)",
        min_value=1.0,
        value=float(st.session_state[_BANKROLL_KEY]),
        step=100.0,
        key="bankroll_input",
        label_visibility="collapsed",
    )
    st.session_state[_BANKROLL_KEY] = bankroll_start

    st.markdown("<hr style='margin:0.6rem 0;border-color:var(--border-subtle);'>",
                unsafe_allow_html=True)

    # ── b) Bet log form ──────────────────────────────────────────────────────
    st.markdown(
        "<span style='font-size:0.72rem;color:var(--text-muted);"
        "font-weight:700;text-transform:uppercase;letter-spacing:0.12em;'>"
        "Log a Completed Bet</span>",
        unsafe_allow_html=True,
    )
    with st.form("bet_log_form", clear_on_submit=True):
        f_col1, f_col2 = st.columns(2)
        with f_col1:
            f_match = st.text_input(
                "Match", placeholder="e.g. Arsenal vs Chelsea", key="f_match"
            )
            f_odds = st.number_input(
                "Decimal Odds", min_value=1.01, value=2.00, step=0.05, key="f_odds"
            )
        with f_col2:
            f_outcome = st.text_input(
                "Outcome", placeholder="e.g. Arsenal ML", key="f_outcome"
            )
            f_stake = st.number_input(
                "Stake ($)", min_value=0.01, value=10.0, step=1.0, key="f_stake"
            )

        f_result = st.radio(
            "Result", ["W", "L", "V"],
            horizontal=True,
            key="f_result",
            help="W = Win · L = Loss · V = Void / Push",
        )
        submitted = st.form_submit_button(
            "\u2795 Add to Log", use_container_width=True, type="primary"
        )

    if submitted:
        if not f_match.strip():
            st.warning("Please enter a match name.")
        else:
            st.session_state[_BET_LOG_KEY].append(
                {
                    "match":   f_match.strip(),
                    "outcome": f_outcome.strip(),
                    "odds":    float(f_odds),
                    "stake":   float(f_stake),
                    "result":  f_result,
                }
            )
            profit = _calc_profit(f_result, float(f_stake), float(f_odds))
            label = "\U0001f7e2 Win" if f_result == "W" else ("\U0001f7e1 Void" if f_result == "V" else "\U0001f534 Loss")
            st.success(
                f"{label} logged: {f_outcome or f_match} @ {f_odds:.2f} — "
                f"P&L: {'+'if profit>=0 else ''}{profit:.2f}"
            )

    bet_log = st.session_state[_BET_LOG_KEY]
    log_df = _build_log_df(bet_log)

    if log_df.empty:
        st.markdown(
            '<div class="empty-state">'
            '<div class="empty-icon">\U0001f4bc</div>'
            '<div class="empty-text">No bets logged yet.<br>'
            'Use the form above to record your first bet.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    # ── d) KPI row ───────────────────────────────────────────────────────────
    total_wagered = log_df["Stake"].sum()
    total_pnl = log_df["Cum. P&L"].iloc[-1]
    roi_pct = (total_pnl / total_wagered * 100.0) if total_wagered > 0 else 0.0
    wins = (log_df["Result"] == "W").sum()
    settled = log_df[log_df["Result"].isin(["W", "L"])].shape[0]
    win_rate = (wins / settled * 100.0) if settled > 0 else 0.0
    current_bankroll = bankroll_start + total_pnl

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total Wagered", f"${total_wagered:,.2f}")
    k2.metric(
        "Total P&L",
        f"{'+'if total_pnl>=0 else ''}{total_pnl:,.2f}",
        delta=f"{total_pnl:+.2f}",
        delta_color="normal",
    )
    k3.metric("ROI", f"{roi_pct:+.1f}%")
    k4.metric("Win Rate", f"{win_rate:.1f}%")
    k5.metric("Bankroll", f"${current_bankroll:,.2f}")

    st.markdown("<hr style='margin:0.5rem 0;border-color:var(--border-subtle);'>",
                unsafe_allow_html=True)

    # ── e) Cumulative P&L chart ──────────────────────────────────────────────
    x = log_df["#"].tolist()
    cum = log_df["Cum. P&L"].tolist()
    pos_y = [max(0.0, v) for v in cum]
    neg_y = [min(0.0, v) for v in cum]

    fig = go.Figure()
    # Positive area fill
    fig.add_trace(go.Scatter(
        x=x, y=pos_y,
        fill="tozeroy",
        fillcolor="rgba(0,214,143,0.15)",
        line=dict(color="rgba(0,0,0,0)", width=0),
        showlegend=False,
        hoverinfo="skip",
    ))
    # Negative area fill
    fig.add_trace(go.Scatter(
        x=x, y=neg_y,
        fill="tozeroy",
        fillcolor="rgba(255,59,92,0.15)",
        line=dict(color="rgba(0,0,0,0)", width=0),
        showlegend=False,
        hoverinfo="skip",
    ))
    # Main line
    fig.add_trace(go.Scatter(
        x=x,
        y=cum,
        name="Cumulative P&L",
        line=dict(color="#1A6FFF", width=2),
        mode="lines+markers",
        marker=dict(size=5, color="#1A6FFF"),
        hovertemplate="Bet #%{x}<br>Cum. P&L: $%{y:,.2f}<extra></extra>",
    ))
    # Zero baseline
    fig.add_hline(
        y=0,
        line_dash="dash",
        line_color="rgba(255,255,255,0.15)",
        line_width=1,
    )
    fig.update_layout(
        title="Cumulative P&L Over Time",
        xaxis_title="Bet #",
        yaxis_title="P&L ($)",
        showlegend=False,
        height=300,
        margin=dict(l=0, r=0, t=36, b=0),
    )
    _apply_dark_theme(fig)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # ── c) P&L table ────────────────────────────────────────────────────────
    st.markdown("##### Bet Log")
    st.dataframe(
        log_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Odds":     st.column_config.NumberColumn(format="%.2f"),
            "Stake":    st.column_config.NumberColumn(format="$%.2f"),
            "P&L":      st.column_config.NumberColumn(format="$%+.2f"),
            "Cum. P&L": st.column_config.NumberColumn(format="$%+.2f"),
        },
    )

    # ── f) Export + g) Clear ─────────────────────────────────────────────────
    exp_col, clr_col = st.columns(2)
    with exp_col:
        st.download_button(
            "\U0001f4e5 Export Bet Log (CSV)",
            log_df.to_csv(index=False),
            "bet_log.csv",
            "text/csv",
            use_container_width=True,
        )
    with clr_col:
        if st.button(
            "\U0001f5d1\ufe0f Clear Log", key="btn_clear_log", use_container_width=True
        ):
            st.session_state["_confirm_clear_log"] = True

    if st.session_state.get("_confirm_clear_log"):
        st.warning(
            "\u26a0\ufe0f This will permanently delete all logged bets for this session."
        )
        conf_yes, conf_no = st.columns(2)
        with conf_yes:
            if st.button(
                "Yes, clear everything", key="btn_confirm_clear", use_container_width=True
            ):
                st.session_state[_BET_LOG_KEY] = []
                st.session_state["_confirm_clear_log"] = False
                st.rerun()
        with conf_no:
            if st.button("Cancel", key="btn_cancel_clear", use_container_width=True):
                st.session_state["_confirm_clear_log"] = False
                st.rerun()
