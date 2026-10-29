"""Top-product horizontal ranking chart."""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtWidgets import QWidget

from app.application.analytics.dashboard_charts import ChartQuantity
from app.presentation.desktop.charts.chart_widget import (
    ChartDatum,
    ChartWidget,
    chart_locale,
)


class ProductChart(ChartWidget):
    """Render prepared unit counts for the best-selling products."""

    def __init__(self, *, parent: QWidget | None = None) -> None:
        super().__init__("hbar", value_kind="quantity", parent=parent)

    def set_series(
        self,
        items: Sequence[ChartQuantity],
        *,
        language: str,
        unit_label: str,
    ) -> None:
        self.set_language(language)
        locale = chart_locale(language)
        self.set_points(
            tuple(
                ChartDatum(
                    label=item.label,
                    value=float(item.quantity),
                    tooltip=(
                        f"{item.label}: {locale.toString(item.quantity)} "
                        f"{unit_label}"
                    ),
                )
                for item in items
            )
        )
