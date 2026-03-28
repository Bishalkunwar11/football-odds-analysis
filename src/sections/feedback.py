# src/sections/feedback.py
"""Feedback section — user rating and message submission."""

from __future__ import annotations

import logging
from datetime import datetime as _dt

import streamlit as st

from src.components.common import render_section_banner
from src.data.loaders import get_db

logger = logging.getLogger(__name__)


def render() -> None:
    """Render the Feedback section."""
    st.markdown(
        render_section_banner(
            "Operator Feedback",
            "User Feedback",
            "Capture platform quality signals, issues, and feature requests.",
        ),
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="alert-card">'
        '<div class="alert-header">'
        '<span class="alert-teams">\U0001f4ac Share Your Feedback</span>'
        '</div>'
        '<div class="alert-detail">'
        "Help us improve ApexOdds Pro by sharing your thoughts, "
        "reporting bugs, or requesting new features."
        '</div></div>',
        unsafe_allow_html=True,
    )

    with st.form("feedback_form", clear_on_submit=True):
        fb_category = st.selectbox(
            "Feedback Type",
            [
                "General Feedback",
                "Bug Report",
                "Feature Request",
                "Performance Issue",
                "UI / UX",
            ],
            key="fb_category",
        )
        fb_rating = st.slider(
            "Overall Rating (1 = Poor, 5 = Excellent)",
            min_value=1, max_value=5, value=5,
            key="fb_rating",
        )
        fb_message = st.text_area(
            "Your Message",
            placeholder="Describe your feedback in detail\u2026",
            height=140,
            key="fb_message",
        )
        submitted = st.form_submit_button(
            "\U0001f4e8 Submit Feedback",
            use_container_width=True,
            type="primary",
        )

    if submitted:
        msg = (fb_message or "").strip()
        if not msg:
            st.warning("\u26a0\ufe0f Please enter a message before submitting.")
        else:
            try:
                get_db().save_feedback(fb_category, fb_rating, msg)
                stars = "\u2605" * fb_rating + "\u2606" * (5 - fb_rating)
                st.success(
                    f"\u2705 Thank you! ({stars} \u00b7 {fb_category})"
                )
            except Exception as exc:  # noqa: BLE001
                logger.error("Failed to save feedback: %s", exc)
                st.error("\u274c Could not save feedback. Please try again.")

    st.markdown("---")
    st.markdown("##### Recent Feedback")
    recent = get_db().get_feedback(limit=20)

    if not recent:
        st.markdown(
            '<div class="empty-state">'
            '<div class="empty-icon">\U0001f4ac</div>'
            '<div class="empty-text">No feedback submitted yet.<br>'
            "Be the first to share your thoughts!</div>"
            '</div>',
            unsafe_allow_html=True,
        )
        return

    star_map = {
        1: "\u2605\u2606\u2606\u2606\u2606",
        2: "\u2605\u2605\u2606\u2606\u2606",
        3: "\u2605\u2605\u2605\u2606\u2606",
        4: "\u2605\u2605\u2605\u2605\u2606",
        5: "\u2605\u2605\u2605\u2605\u2605",
    }

    for entry in recent:
        rating_val = int(entry.get("rating", 1))
        stars_display = star_map.get(rating_val, "\u2605\u2606\u2606\u2606\u2606")
        raw_ts = entry.get("submitted_at") or ""
        try:
            submitted_at = _dt.fromisoformat(raw_ts).strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError):
            submitted_at = raw_ts[:16].replace("T", " ") if raw_ts else "\u2014"

        st.markdown(
            f'<div class="alert-card" style="margin-bottom:0.5rem;">'
            f'<div class="alert-header">'
            f'<span class="alert-teams">{entry["category"]}</span>'
            f'<span style="color:var(--accent-gold);font-size:0.9rem;margin-left:0.5rem;">'
            f'{stars_display}</span>'
            f'<span style="color:var(--text-muted);font-size:0.7rem;margin-left:auto;">'
            f'{submitted_at} UTC</span>'
            f'</div>'
            f'<div class="alert-detail">{entry["message"]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
