"""Custom parlay creation and calculation smoke tests."""

from __future__ import annotations

import re

from playwright.sync_api import Page, expect


def _open_parlay(page: Page) -> None:
    page.get_by_role("button", name=re.compile("Custom Parlay", re.IGNORECASE)).first.click(force=True)
    expect(page.get_by_text("Custom Parlay Builder")).to_be_visible(timeout=20000)


def test_add_single_leg_and_calculate(page: Page) -> None:
    _open_parlay(page)

    page.get_by_label("Selection (e.g. Arsenal ML, Over 2.5 Goals)").fill("Arsenal ML")
    page.get_by_role("spinbutton", name="Decimal Odds").fill("2.10")

    page.get_by_role("button", name=re.compile("Add Leg to Parlay", re.IGNORECASE)).click(force=True)

    expect(page.get_by_text("Arsenal ML")).to_be_visible(timeout=20000)

    page.get_by_role("button", name=re.compile("Calculate Parlay", re.IGNORECASE)).click(force=True)

    expect(page.get_by_text("Combined Odds")).to_be_visible(timeout=20000)
    expect(page.get_by_text("Total Payout")).to_be_visible(timeout=20000)
