"""Alerts section — displays and manages system alerts."""

from __future__ import annotations

import streamlit as st


def render() -> None:
    st.markdown(
        '<div class="section-header">'
        '<div class="section-title">🔔 Alerts</div>'
        '<div class="section-sub">Value bets, arb opportunities, and price movement alerts</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    try:
        from src.db_manager import DBManager
        db = DBManager()
    except Exception as exc:
        st.error(f"Database unavailable: {exc}")
        return

    unread_count = db.get_unread_alert_count()

    top_col, btn_col = st.columns([7, 3])
    with top_col:
        st.markdown(
            f'<span style="color:var(--text-secondary);">'
            f'{unread_count} unread alert{"s" if unread_count != 1 else ""}'
            f'</span>',
            unsafe_allow_html=True,
        )
    with btn_col:
        if unread_count > 0:
            if st.button("Mark All Read", key="alerts_mark_all", use_container_width=True):
                db.mark_all_alerts_read()
                st.rerun()

    st.markdown("<hr style='margin:0.4rem 0 0.8rem;border-color:var(--border-subtle);'>", unsafe_allow_html=True)

    filter_type = st.selectbox(
        "Filter by type",
        ["All", "value_bet", "arb_opp", "price_move", "sharp_move"],
        key="alerts_filter",
    )

    alert_type_filter = None if filter_type == "All" else filter_type
    alerts = db.get_alerts(alert_type=alert_type_filter, limit=50)

    if not alerts:
        st.markdown(
            '<div class="empty-state">'
            '<div class="empty-icon">🔔</div>'
            '<div class="empty-text">No alerts yet.<br>'
            'Alerts appear automatically when value bets, arb opportunities,<br>'
            'or significant price moves are detected.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    _type_colors = {
        "value_bet":  "var(--primary)",
        "arb_opp":    "var(--accent-gold)",
        "price_move": "var(--accent-blue)",
        "sharp_move": "var(--accent-red)",
    }
    _type_icons = {
        "value_bet":  "💡",
        "arb_opp":    "🔄",
        "price_move": "📈",
        "sharp_move": "⚡",
    }

    for alert in alerts:
        alert_id   = alert.get("id")
        is_read    = bool(alert.get("is_read", False))
        atype      = alert.get("alert_type", "")
        color      = _type_colors.get(atype, "var(--text-primary)")
        icon       = _type_icons.get(atype, "🔔")
        read_style = "opacity:0.55;" if is_read else "border-left:3px solid var(--primary);"
        value_str  = f" · <span style='color:{color};font-weight:700;'>{alert.get('value','')}</span>" if alert.get("value") else ""

        col_card, col_btn = st.columns([8, 2])
        with col_card:
            st.markdown(
                f'<div class="match-card" style="margin-bottom:0.5rem;{read_style}">'
                f'{icon} <span style="font-weight:700;color:{color};">{alert.get("title","")}</span>'
                f'{value_str}<br>'
                f'<span style="font-size:0.82rem;color:var(--text-secondary);">{alert.get("detail","")}</span><br>'
                f'<span style="font-size:0.74rem;color:var(--text-muted);">{alert.get("created_at","")}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with col_btn:
            if not is_read and alert_id is not None:
                if st.button("Read", key=f"alert_read_{alert_id}", use_container_width=True):
                    db.mark_alert_read(alert_id)
                    st.rerun()
