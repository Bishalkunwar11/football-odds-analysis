"""Dashboard home — KPI row, hot bets, P&L sparkline, upcoming fixtures, recent alerts."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.analyzer import OddsAnalyzer


def render(
    odds_df: pd.DataFrame,
    upcoming_df: pd.DataFrame,
    analyzer: OddsAnalyzer,
    stats: dict,
) -> None:
    st.markdown(
        '<div class="section-header">'
        '<div class="section-title">🏠 Dashboard</div>'
        '<div class="section-sub">Overview of markets, bets, and performance</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── KPI row ───────────────────────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("Matches", stats.get("num_matches", 0))
    with k2:
        st.metric("Value Bets", stats.get("num_value_bets", 0))
    with k3:
        st.metric("Arb Opps", stats.get("num_arb_opps", 0))
    with k4:
        # Bankroll from DB
        try:
            from src.db_manager import DBManager
            _bk = DBManager().get_bankroll_stats()
            roi = _bk.get("roi_pct", 0.0)
            balance = _bk.get("balance", 0.0)
            st.metric("Bankroll", f"${balance:.0f}", delta=f"{roi:+.1f}% ROI")
        except Exception:
            st.metric("Bankroll", "—")

    st.markdown("<hr style='margin:0.6rem 0 1rem;border-color:var(--border-subtle);'>", unsafe_allow_html=True)

    # ── Hot Bets ──────────────────────────────────────────────────────────────
    st.markdown("#### 🔥 Hot Bets")
    if not odds_df.empty:
        try:
            value_df = analyzer.find_value_bets(odds_df)
            if not value_df.empty:
                top5 = value_df.nlargest(5, "edge_pct")
                for _, row in top5.iterrows():
                    st.markdown(
                        f'<div class="match-card" style="margin-bottom:0.5rem;">'
                        f'<span style="color:var(--accent-gold);font-weight:700;">'
                        f'{row.get("outcome","")}</span> — '
                        f'<span style="color:var(--text-secondary);">{row.get("match","")}</span> · '
                        f'<span style="color:var(--primary);">Edge: {row.get("edge_pct",0):.1f}%</span> · '
                        f'<span style="font-family:var(--font-mono);">{row.get("decimal_odds",0):.2f}</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.info("No value bets found with current data.")
        except Exception:
            st.info("Value bet analysis unavailable.")
    else:
        st.info("No odds data loaded. Refresh or add an API key.")

    st.markdown("<hr style='margin:0.6rem 0 1rem;border-color:var(--border-subtle);'>", unsafe_allow_html=True)

    # ── Upcoming fixtures preview ─────────────────────────────────────────────
    left_col, right_col = st.columns([3, 2])

    with left_col:
        st.markdown("#### 📅 Upcoming Fixtures")
        if not upcoming_df.empty:
            preview = upcoming_df.head(3)
            for _, row in preview.iterrows():
                home = row.get("home_team", row.get("home", "Home"))
                away = row.get("away_team", row.get("away", "Away"))
                commence = row.get("commence_time", "")
                if pd.notna(commence) and commence:
                    try:
                        dt = pd.to_datetime(commence)
                        commence = dt.strftime("%b %d %H:%M")
                    except Exception:
                        pass
                st.markdown(
                    f'<div class="match-card" style="margin-bottom:0.5rem;">'
                    f'<span style="font-weight:600;">{home}</span>'
                    f' <span style="color:var(--text-muted);">vs</span> '
                    f'<span style="font-weight:600;">{away}</span>'
                    f'<span style="float:right;color:var(--text-secondary);font-size:0.8rem;">{commence}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            if st.button("View All Matches →", key="dash_view_matches"):
                st.session_state["active_section"] = "matches"
                st.rerun()
        else:
            st.info("No upcoming fixtures.")

    # ── Recent alerts ─────────────────────────────────────────────────────────
    with right_col:
        st.markdown("#### 🔔 Recent Alerts")
        try:
            from src.db_manager import DBManager
            recent = DBManager().get_alerts(limit=3)
            if recent:
                for alert in recent:
                    read_style = "opacity:0.5;" if alert.get("is_read") else ""
                    st.markdown(
                        f'<div class="match-card" style="margin-bottom:0.5rem;{read_style}">'
                        f'<span style="font-weight:600;color:var(--primary);">{alert.get("title","")}</span><br>'
                        f'<span style="font-size:0.8rem;color:var(--text-secondary);">{alert.get("detail","")}</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                if st.button("View All Alerts →", key="dash_view_alerts"):
                    st.session_state["active_section"] = "alerts"
                    st.rerun()
            else:
                st.info("No alerts yet.")
        except Exception:
            st.info("Alert system unavailable.")

    # ── P&L sparkline ─────────────────────────────────────────────────────────
    st.markdown("#### 📈 P&L (7-day)")
    try:
        from src.db_manager import DBManager
        pnl_data = DBManager().get_pnl_timeseries(days=7)
        if pnl_data:
            pnl_df = pd.DataFrame(pnl_data)
            if not pnl_df.empty and "date" in pnl_df.columns and "cumulative_pnl" in pnl_df.columns:
                pnl_df = pnl_df.set_index("date")
                st.line_chart(pnl_df[["cumulative_pnl"]], height=140)
            else:
                st.info("No P&L data yet. Log some bets in Bankroll.")
        else:
            st.info("No P&L data yet. Log some bets in Bankroll.")
    except Exception:
        st.info("P&L data unavailable.")
