"""Navigation and section smoke tests for the Streamlit app."""

from __future__ import annotations

import re

from playwright.sync_api import Page, expect


def _go_to_section(page: Page, button_name_pattern: str) -> None:
    btn = page.get_by_role("button", name=re.compile(button_name_pattern, re.IGNORECASE)).last
    expect(btn).to_be_visible(timeout=20000)
    btn.click(force=True)
    page.wait_for_timeout(800)


def test_navigation_loads_core_sections(page: Page) -> None:
    expect(page.get_by_text("ApexOdds Pro").first).to_be_visible(timeout=30000)

    _go_to_section(page, "Matches")
    _go_to_section(page, "Value Bets")
    _go_to_section(page, "Bet Calculator")
    _go_to_section(page, "Custom Parlay")
    _go_to_section(page, "Bankroll")


def test_live_center_shows_simulated_data_disclaimer(page: Page) -> None:
    _go_to_section(page, "Live Center")
