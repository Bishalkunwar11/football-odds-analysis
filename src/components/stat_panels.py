# src/components/stat_panels.py
"""Renders small stat panels and KPI summary metric cards."""

from __future__ import annotations


def render_stat_panel(label: str, value: str) -> str:
    """Return HTML for a small stat panel.

    Args:
        label: Short uppercase label displayed above the value.
        value: Formatted value string (e.g. ``"42"`` or ``"5.3%"``).

    Returns:
        HTML string for ``st.markdown(..., unsafe_allow_html=True)``.
    """
    return (
        f'<div class="stat-panel">'
        f'<div class="stat-label">{label}</div>'
        f'<div class="stat-value">{value}</div>'
        f'</div>'
    )


def render_summary_metric_card(
    label: str,
    value: str | int,
    badge_text: str,
    color: str,
    meter_pct: float,
) -> str:
    """Return HTML for a styled KPI summary card.

    Bug fix: ``meter_pct`` is accepted as a single parameter (0–100).
    Callers must compute ``min(value / LIMIT * 100, 100)`` themselves.

    Args:
        label:      Short uppercase label displayed above the value.
        value:      Primary metric value (e.g. ``42`` or ``"5.3%"``).
        badge_text: Small text shown in a pill badge below the value.
        color:      Accent color key — ``"green"``, ``"red"``, ``"gold"``,
                    or ``"blue"``.
        meter_pct:  Progress meter fill 0–100 (clamped internally).

    Returns:
        HTML string for ``st.markdown(..., unsafe_allow_html=True)``.
    """
    meter_pct = max(0.0, min(100.0, meter_pct))

    return (
        f'<div class="summary-metric-card smc-{color}">'
        f'<div class="smc-label">{label}</div>'
        f'<div class="smc-value">{value}</div>'
        f'<span class="smc-badge smc-{color}">{badge_text}</span>'
        f'<div class="smc-meter">'
        f'<div class="smc-meter-fill smc-{color}" '
        f'style="transform:scaleX({meter_pct / 100:.3f});"></div>'
        f'</div>'
        f'</div>'
    )
