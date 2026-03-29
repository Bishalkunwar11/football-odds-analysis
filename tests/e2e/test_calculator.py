"""Calculator section interaction tests."""

from __future__ import annotations

import re

from playwright.sync_api import Page, expect


def _open_calculator(page: Page) -> None:
    page.get_by_role("button", name=re.compile("Bet Calculator", re.IGNORECASE)).first.click(force=True)
    expect(page.get_by_text("Bet Calculator")).to_be_visible(timeout=20000)


def test_single_bet_calculation(page: Page) -> None:
    _open_calculator(page)

    stake_input = page.get_by_role("spinbutton", name="Stake ($)").first
    odds_input = page.get_by_role("spinbutton", name="Decimal Odds").first

    stake_input.fill("100")
    odds_input.fill("2.5")

    page.get_by_role("button", name=re.compile("Calculate Payout", re.IGNORECASE)).first.click(force=True)

    expect(page.get_by_text("Payout", exact=True)).to_be_visible(timeout=20000)
    expect(page.get_by_text("Profit", exact=True)).to_be_visible(timeout=20000)
