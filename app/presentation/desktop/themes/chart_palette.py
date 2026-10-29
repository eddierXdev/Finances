"""Semantic colors for native QPainter charts.

QSS styles the widget tree; painted charts need the same semantic palette in
Python. Keeping it here avoids scattering color literals through chart widgets.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ChartPalette:
    """Theme-aware colors used by the native chart renderer."""

    text: str
    muted_text: str
    grid: str
    axis: str
    accent: str
    accent_soft: str
    positive: str
    negative: str
    warning: str
    neutral: str
    track: str


_LIGHT = ChartPalette(
    text="#111827",
    muted_text="#6b7280",
    grid="#e5e7eb",
    axis="#d1d5db",
    accent="#2563eb",
    accent_soft="#dbeafe",
    positive="#059669",
    negative="#dc2626",
    warning="#d97706",
    neutral="#64748b",
    track="#f1f5f9",
)

_DARK = ChartPalette(
    text="#f8fafc",
    muted_text="#94a3b8",
    grid="#334155",
    axis="#475569",
    accent="#60a5fa",
    accent_soft="#1e3a8a",
    positive="#34d399",
    negative="#f87171",
    warning="#fbbf24",
    neutral="#94a3b8",
    track="#1e293b",
)


def chart_palette(theme: str) -> ChartPalette:
    """Return the chart palette for a concrete theme name."""
    return _DARK if theme == "dark" else _LIGHT
