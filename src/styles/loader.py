# src/styles/loader.py
"""CSS loader — reads assets/styles.css and injects it once via st.markdown."""

from pathlib import Path

import streamlit as st


def apply_styles() -> None:
    """Inject the global stylesheet into the Streamlit page.

    Reads ``src/assets/styles.css`` relative to this file and wraps it in a
    ``<style>`` block.  Call this once at app startup, after
    ``st.set_page_config``.
    """
    css_path = Path(__file__).resolve().parent.parent / "assets" / "styles.css"
    st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)
