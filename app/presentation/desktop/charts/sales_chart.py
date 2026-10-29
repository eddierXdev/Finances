"""Sales evolution line chart."""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtWidgets import QWidget

from app.application.analytics.dashboard_charts import SalesEvolutionPoint
from app.presentation.desktop.charts.chart_widget import (
    ChartDatum,
    ChartWidget,
    chart_locale,
    format_chart_bucket,
    format_chart_money,
    format_chart_tooltip_date,
)


class SalesEvolutionChart(ChartWidget):
    """Render the prepared net-revenue time series."""

    def __init__(self, *, parent: QWidget | None = None) -> None:
        super().__init__("line", value_kind="money", parent=parent)

    def set_series(
        self,
        points: Sequence[SalesEvolutionPoint],
        *,
        granularity: str,
        currency_code: str,
        language: str,
    ) -> None:
        self.set_language(language)
        self.set_currency(currency_code)
        locale = chart_locale(language)
        self.set_points(
            tuple(
                ChartDatum(
                    label=format_chart_bucket(
                        point.period_start,
                        granularity,
                        language,
                    ),
                    value=float(point.revenue.amount),
                    tooltip=(
                        f"{format_chart_tooltip_date(point.period_start, granularity, language)}"
                        ": "
                        f"{format_chart_money(float(point.revenue.amount), currency_code, locale)}"
                    ),
                )
                for point in points
            )
        )
