"""Revenue, expenses and profit comparison chart."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from PySide6.QtWidgets import QWidget

from app.application.analytics.dashboard_charts import ChartAmount
from app.presentation.desktop.charts.chart_widget import (
    ChartDatum,
    ChartWidget,
    chart_locale,
    format_chart_money,
)


class RevenueExpenseChart(ChartWidget):
    """Render prepared period totals as a compact vertical bar chart."""

    def __init__(self, *, parent: QWidget | None = None) -> None:
        super().__init__("bar", value_kind="money", parent=parent)

    def set_series(
        self,
        items: Sequence[ChartAmount],
        *,
        labels: Mapping[str, str],
        currency_code: str,
        language: str,
    ) -> None:
        self.set_language(language)
        self.set_currency(currency_code)
        locale = chart_locale(language)
        tone_by_key = {
            "revenue": "accent",
            "expenses": "warning",
            "gross_profit": "positive",
            "net_profit": "positive",
        }
        data = []
        for item in items:
            value = float(item.amount.amount)
            tone = tone_by_key.get(item.key, "neutral")
            if item.key == "net_profit" and value < 0:
                tone = "negative"
            label = labels.get(item.key, item.key)
            data.append(
                ChartDatum(
                    label=label,
                    value=value,
                    tone=tone,
                    tooltip=(
                        f"{label}: "
                        f"{format_chart_money(value, currency_code, locale)}"
                    ),
                )
            )
        self.set_points(tuple(data))
