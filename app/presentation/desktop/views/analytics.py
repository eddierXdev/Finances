"""Analytics screen with period filters and product/supplier reports."""

from __future__ import annotations

from datetime import UTC, datetime

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDateEdit,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTabWidget,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from app.application.analytics.models import (
    AnalyticsPeriod,
    ProductPerformance,
    ProductProfitability,
    SlowMovingProduct,
    SupplierProfitability,
)
from app.application.analytics.service import (
    AnalyticsService,
    AnalyticsSnapshot,
)
from app.presentation.desktop.form_utils import (
    display_datetime,
    display_money,
)
from app.presentation.desktop.table_model import ReadOnlyTableModel


class AnalyticsPage(QWidget):
    """Base-currency financial analysis over an optional period."""

    def __init__(
        self,
        analytics: AnalyticsService,
        *,
        base_currency: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._analytics = analytics
        self._base_currency = base_currency
        self._cards: dict[str, QLabel] = {}
        self.setObjectName("analyticsPage")
        self._build_ui()
        self.reload()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 24)
        layout.setSpacing(14)

        title = QLabel("Analytics", self)
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        description = QLabel(
            "Revenue, costs, profit, inventory and product or supplier "
            "performance converted into the configured base currency.",
            self,
        )
        description.setObjectName("pageDescription")
        description.setWordWrap(True)
        layout.addWidget(description)

        filters = QHBoxLayout()
        self._use_period = QCheckBox("Use period", self)
        self._use_period.setObjectName("analyticsUsePeriod")
        filters.addWidget(self._use_period)

        self._start = QDateEdit(QDate.currentDate().addMonths(-1), self)
        self._start.setObjectName("analyticsStartDate")
        self._start.setCalendarPopup(True)
        self._start.setDisplayFormat("yyyy-MM-dd")
        filters.addWidget(QLabel("From", self))
        filters.addWidget(self._start)

        self._end = QDateEdit(QDate.currentDate(), self)
        self._end.setObjectName("analyticsEndDate")
        self._end.setCalendarPopup(True)
        self._end.setDisplayFormat("yyyy-MM-dd")
        filters.addWidget(QLabel("To", self))
        filters.addWidget(self._end)

        apply = QPushButton("Apply", self)
        apply.setObjectName("applyAnalyticsButton")
        apply.clicked.connect(self.reload)
        filters.addWidget(apply)

        refresh = QPushButton("Refresh", self)
        refresh.setObjectName("refreshAnalyticsButton")
        refresh.clicked.connect(self.reload)
        filters.addWidget(refresh)
        filters.addStretch(1)
        layout.addLayout(filters)

        self._use_period.toggled.connect(self._toggle_period)
        self._toggle_period(False)

        self._warning = QLabel(self)
        self._warning.setObjectName("warningBanner")
        self._warning.setWordWrap(True)
        self._warning.hide()
        layout.addWidget(self._warning)

        self._error_banner = QLabel(self)
        self._error_banner.setObjectName("errorBanner")
        self._error_banner.setWordWrap(True)
        self._error_banner.hide()
        layout.addWidget(self._error_banner)

        cards = QHBoxLayout()
        cards.setSpacing(10)
        for key, label in (
            ("revenue", "Revenue"),
            ("cogs", "COGS"),
            ("gross", "Gross profit"),
            ("expenses", "Expenses"),
            ("net", "Net profit"),
            ("inventory", "Inventory"),
            ("capital", "Capital"),
            ("roi", "ROI"),
        ):
            value = _metric(label, self)
            cards.addWidget(value.parentWidget(), 1)
            self._cards[key] = value
        layout.addLayout(cards)

        self._best_model = ReadOnlyTableModel(
            ("Product", "Units", "Revenue"),
            self._best_values,
            right_columns=(1, 2),
            parent=self,
        )
        self._profit_model = ReadOnlyTableModel(
            (
                "Product",
                "Currency",
                "Units",
                "Revenue",
                "COGS",
                "Gross profit",
                "Margin",
            ),
            self._profit_values,
            right_columns=(2, 3, 4, 5, 6),
            center_columns=(1,),
            parent=self,
        )
        self._slow_model = ReadOnlyTableModel(
            ("Product", "Units", "Value", "Last sale", "Days"),
            self._slow_values,
            right_columns=(1, 2, 4),
            parent=self,
        )
        self._supplier_model = ReadOnlyTableModel(
            (
                "Supplier",
                "Units",
                "Revenue",
                "COGS",
                "Gross profit",
                "Customer refunds",
                "Supplier refunds",
            ),
            self._supplier_values,
            right_columns=(1, 2, 3, 4, 5, 6),
            parent=self,
        )

        self._tabs = QTabWidget(self)
        self._tabs.setObjectName("analyticsTabs")
        self._tabs.addTab(
            _table(self, "analyticsBestSellersTable", self._best_model, 0),
            "Best sellers",
        )
        self._tabs.addTab(
            _table(
                self, "analyticsProfitabilityTable", self._profit_model, 0
            ),
            "Profitability",
        )
        self._tabs.addTab(
            _table(self, "analyticsSlowMovingTable", self._slow_model, 0),
            "Slow moving",
        )
        self._tabs.addTab(
            _table(self, "analyticsSuppliersTable", self._supplier_model, 0),
            "Suppliers",
        )
        layout.addWidget(self._tabs, 1)

        self._footer = QLabel(self)
        self._footer.setObjectName("analyticsFooter")
        layout.addWidget(self._footer)

    def _toggle_period(self, enabled: bool) -> None:
        self._start.setEnabled(enabled)
        self._end.setEnabled(enabled)

    @staticmethod
    def _best_values(row: ProductPerformance) -> tuple[str, ...]:
        return (
            row.product_name,
            str(row.net_quantity),
            display_money(row.revenue),
        )

    @staticmethod
    def _profit_values(row: ProductProfitability) -> tuple[str, ...]:
        margin = f"{row.gross_margin}%" if row.gross_margin is not None else "—"
        return (
            row.product_name,
            row.currency.code,
            str(row.net_quantity),
            str(row.revenue),
            str(row.cogs),
            str(row.gross_profit),
            margin,
        )

    @staticmethod
    def _slow_values(row: SlowMovingProduct) -> tuple[str, ...]:
        last_sale = (
            row.last_sale_date.date().isoformat()
            if row.last_sale_date is not None
            else "Never"
        )
        days = (
            str(row.days_since_last_sale)
            if row.days_since_last_sale is not None
            else "—"
        )
        return (
            row.product_name,
            str(row.remaining_quantity),
            display_money(row.inventory_value),
            last_sale,
            days,
        )

    @staticmethod
    def _supplier_values(row: SupplierProfitability) -> tuple[str, ...]:
        return (
            row.supplier_name or "No supplier",
            str(row.net_quantity),
            display_money(row.revenue),
            display_money(row.cogs),
            display_money(row.gross_profit),
            display_money(row.customer_return_revenue),
            display_money(row.supplier_refunds),
        )

    def _period(self) -> AnalyticsPeriod:
        if not self._use_period.isChecked():
            return AnalyticsPeriod()
        start = datetime(
            self._start.date().year(),
            self._start.date().month(),
            self._start.date().day(),
            tzinfo=UTC,
        )
        end_date = self._end.date()
        end = datetime(
            end_date.year(),
            end_date.month(),
            end_date.day(),
            23,
            59,
            59,
            999999,
            tzinfo=UTC,
        )
        return AnalyticsPeriod(start=start, end=end)

    def reload(self, *_args) -> None:
        try:
            period = self._period()
            snapshot = self._analytics.analytics(period)
        except Exception as exc:
            self._show_error(f"Could not load analytics: {exc}")
            return
        self._show_error(None)
        self._render(snapshot)

    def _show_error(self, message: str | None) -> None:
        if message is None:
            self._error_banner.clear()
            self._error_banner.hide()
            return
        self._error_banner.setText(message)
        self._error_banner.show()

    def _render(self, snapshot: AnalyticsSnapshot) -> None:
        report = snapshot.report
        self._cards["revenue"].setText(str(report.revenue))
        self._cards["cogs"].setText(str(report.cogs))
        self._cards["gross"].setText(str(report.gross_profit))
        self._cards["expenses"].setText(str(report.expenses))
        self._cards["net"].setText(str(report.net_profit))
        self._cards["inventory"].setText(str(report.inventory_value))
        self._cards["capital"].setText(str(report.available_capital))
        self._cards["roi"].setText(
            f"{report.roi}%" if report.roi is not None else "—"
        )

        if report.missing_rates:
            pairs = ", ".join(
                f"{missing.base_code}/{missing.quote_code}"
                for missing in report.missing_rates
            )
            self._warning.setText(
                "Some values are excluded because these exchange rates are "
                f"missing: {pairs}."
            )
            self._warning.show()
        else:
            self._warning.clear()
            self._warning.hide()

        self._best_model.set_rows(snapshot.performance.best_sellers)
        self._profit_model.set_rows(snapshot.performance.most_profitable)
        self._slow_model.set_rows(snapshot.performance.slow_moving)
        self._supplier_model.set_rows(snapshot.suppliers.suppliers)
        period = report.period
        period_text = (
            f"{period.start.date().isoformat()} → "
            f"{period.end.date().isoformat()}"
            if period.start is not None and period.end is not None
            else "All time"
        )
        self._footer.setText(
            f"Base currency {report.base_currency.code} · {period_text} · "
            f"as of {display_datetime(report.as_of)}"
        )


def _metric(title: str, parent: QWidget) -> QLabel:
    container = QWidget(parent)
    container.setObjectName("analyticsMetric")
    layout = QVBoxLayout(container)
    layout.setContentsMargins(10, 8, 10, 8)
    layout.setSpacing(2)
    title_label = QLabel(title, container)
    title_label.setObjectName("metricTitle")
    value = QLabel("—", container)
    value.setObjectName("metricValue")
    layout.addWidget(title_label)
    layout.addWidget(value)
    return value


def _table(
    parent: QWidget,
    object_name: str,
    model: ReadOnlyTableModel,
    stretch_column: int,
) -> QTableView:
    table = QTableView(parent)
    table.setObjectName(object_name)
    table.setModel(model)
    table.setAlternatingRowColors(True)
    table.setSelectionBehavior(
        QAbstractItemView.SelectionBehavior.SelectRows
    )
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.verticalHeader().setVisible(False)
    table.horizontalHeader().setSectionResizeMode(
        stretch_column, QHeaderView.ResizeMode.Stretch
    )
    for column in range(model.columnCount()):
        if column != stretch_column:
            table.horizontalHeader().setSectionResizeMode(
                column, QHeaderView.ResizeMode.ResizeToContents
            )
    return table
