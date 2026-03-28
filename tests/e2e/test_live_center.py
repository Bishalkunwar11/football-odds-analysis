"""Live center interaction smoke tests."""

from __future__ import annotations

import re

from playwright.sync_api import Page, expect


def test_live_center_bet_now_button_works(page: Page) -> None:
    page.get_by_role("button", name=re.compile("Live Center", re.IGNORECASE)).first.click(force=True)

    expect(page.get_by_text("Simulated data")).to_be_visible(timeout=20000)

    bet_now = page.get_by_role("button", name=re.compile("BET NOW", re.IGNORECASE)).first
    expect(bet_now).to_be_visible(timeout=20000)
    bet_now.click(force=True)

    expect(page.get_by_text("demo mode")).to_be_visible(timeout=20000)
