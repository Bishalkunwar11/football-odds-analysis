"""Bankroll tracker interaction tests."""

from __future__ import annotations

import re

from playwright.sync_api import Page, expect


def _open_bankroll(page: Page) -> None:
    page.get_by_role("button", name=re.compile("Bankroll", re.IGNORECASE)).first.click(force=True)
    expect(page.get_by_text("Bankroll Tracker")).to_be_visible(timeout=20000)


def test_log_completed_bet_updates_metrics(page: Page) -> None:
    _open_bankroll(page)

    page.get_by_label("Match").fill("Arsenal vs Chelsea")
    page.get_by_label("Outcome").fill("Arsenal ML")
    page.get_by_role("spinbutton", name="Decimal Odds").fill("2.00")
    page.get_by_role("spinbutton", name="Stake ($)").fill("10")
    page.get_by_label("Result").get_by_text("W").click()

    page.get_by_role("button", name=re.compile("Add to Log", re.IGNORECASE)).click(force=True)

    expect(page.get_by_text("Total Wagered")).to_be_visible(timeout=20000)
    expect(page.get_by_text("ROI")).to_be_visible(timeout=20000)
