# src/components/odds_ladder.py
"""Renders a bookmaker odds ladder table."""

from __future__ import annotations

import pandas as pd


def render_odds_ladder(match_id: str, odds_df: pd.DataFrame) -> str:
    """Return HTML for a full odds-ladder table for one match."""
    no_data_tpl = '<p style="font-size:0.75rem;color:var(--text-muted);">{}</p>'

    if odds_df.empty:
        return no_data_tpl.format("No odds data available.")

    h2h = odds_df[(odds_df["match_id"] == match_id) & (odds_df["market"] == "h2h")]
    if h2h.empty:
        return no_data_tpl.format("No 1X2 odds available for this match.")

    outcomes: list[str] = sorted(h2h["outcome_name"].unique())
    bookmakers: list[str] = sorted(h2h["bookmaker"].unique())

    price_matrix: dict[str, dict[str, float]] = {}
    for _, row in h2h.iterrows():
        book = str(row["bookmaker"])
        outcome = str(row["outcome_name"])
        price = float(row["outcome_price"])
        price_matrix.setdefault(book, {})
        if price > price_matrix[book].get(outcome, 0.0):
            price_matrix[book][outcome] = price

    best: dict[str, float] = {}
    worst: dict[str, float] = {}
    for outcome in outcomes:
        prices = [
            price_matrix[book][outcome]
            for book in bookmakers
            if outcome in price_matrix.get(book, {})
        ]
        if prices:
            best[outcome] = max(prices)
            worst[outcome] = min(prices)

    table_style = "width:100%;border-collapse:collapse;font-size:0.77rem;background:var(--bg-surface);"
    th_style = (
        "padding:0.38rem 0.65rem;text-align:center;"
        "color:var(--text-muted);font-size:0.69rem;font-weight:700;"
        "text-transform:uppercase;letter-spacing:0.08em;"
        "border-bottom:1px solid var(--border-subtle);"
    )
    td_style = "padding:0.38rem 0.65rem;text-align:center;border-bottom:0.5px solid var(--border-subtle);"

    header_cells = "".join(f'<th style="{th_style}">{outcome}</th>' for outcome in outcomes)
    header_row = (
        f'<tr>'
        f'<th style="{th_style};text-align:left;">Bookmaker</th>'
        f'{header_cells}'
        f'<th style="{th_style}">Margin</th>'
        f'</tr>'
    )

    data_rows = ""
    for book in bookmakers:
        prices = price_matrix.get(book, {})
        outcome_cells = ""
        margin_sum = 0.0

        for outcome in outcomes:
            price = prices.get(outcome)
            if price:
                margin_sum += 1.0 / price
                if price == best.get(outcome):
                    color = "var(--accent-green)"
                    weight = "700"
                elif price == worst.get(outcome):
                    color = "var(--accent-red)"
                    weight = "400"
                else:
                    color = "var(--text-primary)"
                    weight = "400"
                outcome_cells += (
                    f'<td style="{td_style}color:{color};font-weight:{weight};'
                    f'font-family:\'Barlow Condensed\',sans-serif;">{price:.2f}</td>'
                )
            else:
                outcome_cells += f'<td style="{td_style}color:var(--text-muted);">-</td>'

        margin_pct = (margin_sum - 1.0) * 100.0 if margin_sum > 0 else 0.0
        margin_color = (
            "var(--accent-green)" if margin_pct < 3.0
            else "var(--accent-red)" if margin_pct > 7.0
            else "var(--text-secondary)"
        )

        data_rows += (
            f'<tr>'
            f'<td style="{td_style}text-align:left;color:var(--text-secondary);">{book}</td>'
            f'{outcome_cells}'
            f'<td style="{td_style}color:{margin_color};font-weight:600;">{margin_pct:.2f}%</td>'
            f'</tr>'
        )

    implied_cells = ""
    for outcome in outcomes:
        best_price = best.get(outcome, 0.0)
        implied_pct = (1.0 / best_price * 100.0) if best_price > 0 else 0.0
        implied_cells += (
            f'<td style="{td_style}color:var(--text-muted);font-size:0.72rem;">'
            f'{implied_pct:.1f}%</td>'
        )

    implied_row = (
        f'<tr style="border-top:1px solid var(--border-mid);">'
        f'<td style="{td_style}text-align:left;color:var(--text-muted);font-style:italic;font-size:0.72rem;">Implied Prob.</td>'
        f'{implied_cells}'
        f'<td style="{td_style}color:var(--text-muted);">-</td>'
        f'</tr>'
    )

    return (
        f'<div style="overflow-x:auto;border-radius:8px;border:0.5px solid var(--border-subtle);">'
        f'<table style="{table_style}">'
        f'<thead>{header_row}</thead>'
        f'<tbody>{data_rows}{implied_row}</tbody>'
        f'</table>'
        f'</div>'
    )
