"""Dashboard V2 built from prepared analytics read models."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.application.analytics.dashboard_charts import (
    ChartAmount,
    ChartQuantity,
    DashboardChartData,
)
from app.application.analytics.models import (
    AccountBalance,
    AnalyticsPeriod,
    ConsolidatedReport,
    ProductPerformance,
    ProductPerformanceReport,
    SlowMovingProduct,
)
from app.application.analytics.service import AnalyticsService
from app.presentation.desktop.charts import (
    ProductChart,
    RevenueExpenseChart,
    SalesEvolutionChart,
    chart_locale,
    format_chart_money,
)
from app.presentation.desktop.components import (
    DataTable,
    FilterBar,
    PageHeader,
    PeriodFilter,
    SectionCard,
    StatCard,
)
from app.presentation.desktop.form_utils import display_datetime
from app.presentation.desktop.i18n.translator import Translator
from app.presentation.desktop.table_model import ReadOnlyTableModel
from app.presentation.desktop.themes.theme_manager import ThemeManager


class DashboardPage(QWidget):
    """Business overview with period filters, KPIs, charts and attention rows."""

    def __init__(
        self,
        analytics: AnalyticsService,
        *,
        base_currency: str,
        translator: Translator | None = None,
        theme_manager: ThemeManager | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._analytics = analytics
        self._base_currency = base_currency
        self._translator = translator or Translator()
        self._theme_manager = theme_manager or ThemeManager()
        self._cards: dict[str, StatCard] = {}
        self._last_report: ConsolidatedReport | None = None
        self._last_performance: ProductPerformanceReport | None = None
        self._last_charts: DashboardChartData | None = None

        self.setObjectName("dashboardPage")
        self._build_ui()
        self._translator.language_changed.connect(self.retranslate)
        self._theme_manager.theme_changed.connect(self._on_theme_changed)
        self.retranslate()
        self._apply_chart_palette()
        self.reload()

    def _build_ui(self) -> None:
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(0)

        self._scroll_area = QScrollArea(self)
        self._scroll_area.setObjectName("dashboardScrollArea")
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._scroll_area.viewport().setObjectName("dashboardViewport")

        content = QWidget(self._scroll_area)
        content.setObjectName("dashboardContent")
        content.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(32, 28, 32, 24)
        layout.setSpacing(18)

        self._build_header(layout)
        self._build_banners(layout)
        self._build_metrics(layout)
        self._build_charts(layout)
        self._build_accounts(layout)

        self._footer = QLabel(self)
        self._footer.setObjectName("dashboardFooter")
        self._footer.setWordWrap(True)
        layout.addWidget(self._footer)

        self._scroll_area.setWidget(content)
        page_layout.addWidget(self._scroll_area)

    def _build_header(self, layout: QVBoxLayout) -> None:
        self._page_header = PageHeader(parent=self)
        self._refresh_button = QPushButton(self._page_header)
        self._refresh_button.setObjectName("refreshDashboardButton")
        self._refresh_button.clicked.connect(self.reload)
        self._page_header.add_action(self._refresh_button)
        layout.addWidget(self._page_header)

        self._filter_bar = FilterBar(self)
        self._period_filter = PeriodFilter(
            self._translator,
            parent=self._filter_bar,
        )
        self._period_filter.period_changed.connect(self.reload)
        self._filter_bar.add_widget(self._period_filter)
        self._filter_bar.add_stretch()
        layout.addWidget(self._filter_bar)

    def _build_banners(self, layout: QVBoxLayout) -> None:
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

    def _build_metrics(self, layout: QVBoxLayout) -> None:
        cards = QGridLayout()
        cards.setContentsMargins(0, 0, 0, 0)
        cards.setHorizontalSpacing(12)
        cards.setVerticalSpacing(12)
        for column in range(3):
            cards.setColumnStretch(column, 1)

        definitions = (
            "capital",
            "revenue",
            "net_profit",
            "inventory",
            "gross_profit",
            "expenses",
        )
        for index, key in enumerate(definitions):
            card = StatCard(parent=self)
            self._cards[key] = card
            cards.addWidget(card, index // 3, index % 3)
        layout.addLayout(cards)

    def _build_charts(self, layout: QVBoxLayout) -> None:
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
        for column in range(3):
            grid.setColumnStretch(column, 1)

        self._sales_card = SectionCard(parent=self)
        self._sales_card.setMinimumHeight(320)
        self._sales_chart = SalesEvolutionChart(parent=self._sales_card)
        self._sales_card.add_content(self._sales_chart)
        grid.addWidget(self._sales_card, 0, 0, 1, 2)

        self._revenue_card = SectionCard(parent=self)
        self._revenue_card.setMinimumHeight(320)
        self._revenue_chart = RevenueExpenseChart(parent=self._revenue_card)
        self._revenue_card.add_content(self._revenue_chart)
        grid.addWidget(self._revenue_card, 0, 2)

        self._products_card = SectionCard(parent=self)
        self._product_chart = ProductChart(parent=self._products_card)
        self._best_model = ReadOnlyTableModel(
            (),
            self._best_values,
            right_columns=(1, 2),
            parent=self,
        )
        self._best_table = DataTable(
            "dashboardBestSellersTable",
            self._best_model,
            stretch_column=0,
            parent=self._products_card,
        )
        self._products_tabs = QTabWidget(self._products_card)
        self._products_tabs.setObjectName("dashboardProductsTabs")
        self._products_tabs.setDocumentMode(True)
        self._products_tabs.addTab(self._product_chart, "")
        table_page = QWidget(self._products_tabs)
        table_layout = QVBoxLayout(table_page)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.addWidget(self._best_table)
        self._products_tabs.addTab(table_page, "")
        self._products_card.add_content(self._products_tabs)
        grid.addWidget(self._products_card, 1, 0)

        self._attention_card = SectionCard(parent=self)
        self._slow_model = ReadOnlyTableModel(
            (),
            self._slow_values,
            right_columns=(1, 2),
            parent=self,
        )
        self._slow_table = DataTable(
            "dashboardSlowMovingTable",
            self._slow_model,
            stretch_column=0,
            parent=self._attention_card,
        )
        self._attention_card.add_content(self._slow_table)
        grid.addWidget(self._attention_card, 1, 1, 1, 2)

        layout.addLayout(grid)

    def _build_accounts(self, layout: QVBoxLayout) -> None:
        self._accounts_card = SectionCard(parent=self)
        self._accounts_model = ReadOnlyTableModel(
            (),
            self._account_values,
            right_columns=(2,),
            center_columns=(1, 3),
            muted=lambda row: not row.is_active,
            parent=self,
        )
        self._accounts_table = DataTable(
            "dashboardAccountsTable",
            self._accounts_model,
            stretch_column=0,
            parent=self._accounts_card,
        )
        self._accounts_card.add_content(self._accounts_table)
        layout.addWidget(self._accounts_card)

    def reload(self, *_args) -> None:
        period = self._period_filter.current_period()
        try:
            report, performance, charts = self._load(period)
        except Exception as exc:
            self._show_error(str(exc))
            return
        self._show_error(None)
        self._last_report = report
        self._last_performance = performance
        self._last_charts = charts
        self._render(report, performance, charts)

    def _load(
        self,
        period: AnalyticsPeriod,
    ) -> tuple[
        ConsolidatedReport,
        ProductPerformanceReport,
        DashboardChartData,
    ]:
        if hasattr(self._analytics, "dashboard_overview"):
            overview = self._analytics.dashboard_overview(period, limit=8)
            return overview.report, overview.performance, overview.charts

        if hasattr(self._analytics, "analytics"):
            snapshot = self._analytics.analytics(period, limit=8)
        else:
            snapshot = self._analytics.dashboard()
        report = snapshot.report
        performance = snapshot.performance
        return report, performance, self._fallback_charts(report, performance)

    def _fallback_charts(
        self,
        report,
        performance,
    ) -> DashboardChartData:
        best_sellers = getattr(performance, "best_sellers", ())
        return DashboardChartData(
            sales_evolution=(),
            granularity="day",
            revenue_expenses=(
                ChartAmount("revenue", report.revenue),
                ChartAmount("expenses", report.expenses),
                ChartAmount("gross_profit", report.gross_profit),
                ChartAmount("net_profit", report.net_profit),
            ),
            top_products=tuple(
                ChartQuantity(
                    label=product.product_name,
                    quantity=product.net_quantity,
                )
                for product in best_sellers
                if product.net_quantity > 0
            ),
        )

    def _render(
        self,
        report: ConsolidatedReport,
        performance: ProductPerformanceReport,
        charts: DashboardChartData,
    ) -> None:
        t = self._translator.tr

        self._set_card(
            "capital",
            self._money_value(report.available_capital),
            t(
                "dashboard.metric.capital_hint",
                invested=self._money_value(report.invested_capital),
            ),
            tone="neutral",
        )
        self._set_card(
            "revenue",
            self._money_value(report.revenue),
            t("dashboard.metric.revenue_hint"),
            tone="accent",
        )
        self._set_card(
            "net_profit",
            self._money_value(report.net_profit),
            _margin_text(
                report.net_margin,
                t("dashboard.margin.net"),
                t("dashboard.margin.unavailable"),
            ),
            negative=report.net_profit.amount < 0,
            tone="positive",
        )
        self._set_card(
            "inventory",
            self._money_value(report.inventory_value),
            t(
                "dashboard.metric.inventory_hint",
                units=report.native_inventory.total_units,
            ),
            tone="neutral",
        )
        self._set_card(
            "gross_profit",
            self._money_value(report.gross_profit),
            _margin_text(
                report.gross_margin,
                t("dashboard.margin.gross"),
                t("dashboard.margin.unavailable"),
            ),
            tone="positive",
        )
        self._set_card(
            "expenses",
            self._money_value(report.expenses),
            t("dashboard.metric.expenses_hint"),
            tone="warning",
        )

        if report.missing_rates:
            pairs = ", ".join(
                f"{missing.base_code}/{missing.quote_code}"
                for missing in report.missing_rates
            )
            self._warning.setText(
                t("dashboard.warning.missing_rates", pairs=pairs)
            )
            self._warning.show()
        else:
            self._warning.clear()
            self._warning.hide()

        self._sales_chart.set_series(
            charts.sales_evolution,
            granularity=charts.granularity,
            currency_code=report.base_currency.code,
            language=self._translator.language,
        )
        self._revenue_chart.set_series(
            charts.revenue_expenses,
            labels={
                "revenue": t("dashboard.chart.revenue"),
                "expenses": t("dashboard.chart.expenses"),
                "gross_profit": t("dashboard.chart.gross_profit"),
                "net_profit": t("dashboard.chart.net_profit"),
            },
            currency_code=report.base_currency.code,
            language=self._translator.language,
        )
        self._product_chart.set_series(
            charts.top_products,
            language=self._translator.language,
            unit_label=t("dashboard.units"),
        )

        self._best_table.set_rows(tuple(performance.best_sellers)[:8])
        self._slow_table.set_rows(tuple(performance.slow_moving)[:8])
        self._accounts_table.set_rows(
            tuple(report.native_accounts.accounts)
        )

        self._footer.setText(
            t(
                "dashboard.footer",
                currency=report.base_currency.code,
                as_of=display_datetime(report.as_of),
                period=self._period_label(report.period),
                status=(
                    t("dashboard.data.complete")
                    if report.is_complete
                    else t("dashboard.data.incomplete")
                ),
            )
        )

    def _set_card(
        self,
        key: str,
        value: str,
        hint: str,
        *,
        negative: bool = False,
        tone: str | None = None,
    ) -> None:
        self._cards[key].set_value(
            value,
            hint,
            negative=negative,
            tone=tone,
        )

    def _best_values(self, row: ProductPerformance) -> tuple[str, ...]:
        return (
            row.product_name,
            str(row.net_quantity),
            self._money_values(row.revenue),
        )

    def _slow_values(self, row: SlowMovingProduct) -> tuple[str, ...]:
        last_sale = (
            row.last_sale_date.date().isoformat()
            if row.last_sale_date is not None
            else self._translator.tr("dashboard.never")
        )
        return (
            row.product_name,
            str(row.remaining_quantity),
            self._money_values(row.inventory_value),
            last_sale,
        )

    def _account_values(self, row: AccountBalance) -> tuple[str, ...]:
        return (
            row.account_name,
            row.currency.code,
            self._money_value(row.balance),
            (
                self._translator.tr("dashboard.account.active")
                if row.is_active
                else self._translator.tr("dashboard.account.inactive")
            ),
        )

    def _money_value(self, value) -> str:
        return format_chart_money(
            float(value.amount),
            value.currency.code,
            chart_locale(self._translator.language),
        )

    def _money_values(self, values) -> str:
        values = tuple(values)
        if not values:
            return "—"
        return " + ".join(self._money_value(value) for value in values)

    def _period_label(self, period: AnalyticsPeriod) -> str:
        t = self._translator.tr
        if period.start is None and period.end is None:
            return t("dashboard.period.all_time")
        if period.start is not None and period.end is not None:
            return t(
                "dashboard.period.range",
                start=display_datetime(period.start),
                end=display_datetime(period.end),
            )
        if period.start is not None:
            return t(
                "dashboard.period.from",
                start=display_datetime(period.start),
            )
        return t(
            "dashboard.period.until",
            end=display_datetime(period.end),
        )

    def _show_error(self, message: str | None) -> None:
        if message is None:
            self._error_banner.clear()
            self._error_banner.hide()
            return
        self._error_banner.setText(
            self._translator.tr("dashboard.error.load", error=message)
        )
        self._error_banner.show()

    def _on_theme_changed(self, *_args) -> None:
        self._apply_chart_palette()

    def _apply_chart_palette(self) -> None:
        palette = self._theme_manager.chart_palette
        for chart in (
            self._sales_chart,
            self._revenue_chart,
            self._product_chart,
        ):
            chart.set_palette(palette)

    def retranslate(self, *_args) -> None:
        t = self._translator.tr
        self._page_header.set_eyebrow(t("dashboard.eyebrow"))
        self._page_header.set_title(t("dashboard.title"))
        self._page_header.set_description(t("dashboard.description"))
        self._refresh_button.setText(t("dashboard.refresh"))
        self._refresh_button.setAccessibleName(t("dashboard.refresh"))

        metric_keys = {
            "capital": "dashboard.metric.capital",
            "revenue": "dashboard.metric.revenue",
            "net_profit": "dashboard.metric.net_profit",
            "inventory": "dashboard.metric.inventory",
            "gross_profit": "dashboard.metric.gross_profit",
            "expenses": "dashboard.metric.expenses",
        }
        for key, translation_key in metric_keys.items():
            self._cards[key].set_title(t(translation_key))

        self._sales_card.set_title(t("dashboard.chart.sales.title"))
        self._sales_card.set_description(
            t("dashboard.chart.sales.description")
        )
        self._revenue_card.set_title(t("dashboard.chart.revenue.title"))
        self._revenue_card.set_description(
            t("dashboard.chart.revenue.description")
        )
        self._products_card.set_title(t("dashboard.chart.products.title"))
        self._products_card.set_description(
            t("dashboard.chart.products.description")
        )
        self._products_tabs.setTabText(
            0,
            t("dashboard.chart.products.chart_tab"),
        )
        self._products_tabs.setTabText(
            1,
            t("dashboard.chart.products.table_tab"),
        )
        self._products_tabs.setAccessibleName(
            t("dashboard.chart.products.title")
        )
        self._products_tabs.setAccessibleDescription(
            t("dashboard.chart.products.description")
        )
        self._attention_card.set_title(t("dashboard.attention.title"))
        self._attention_card.set_description(
            t("dashboard.attention.description")
        )
        self._accounts_card.set_title(t("dashboard.accounts.title"))
        self._accounts_card.set_description(
            t("dashboard.accounts.description")
        )

        self._best_table.set_headers(
            (
                t("dashboard.table.product"),
                t("dashboard.table.units"),
                t("dashboard.table.revenue"),
            )
        )
        self._slow_table.set_headers(
            (
                t("dashboard.table.product"),
                t("dashboard.table.units"),
                t("dashboard.table.value"),
                t("dashboard.table.last_sale"),
            )
        )
        self._accounts_table.set_headers(
            (
                t("dashboard.table.account"),
                t("dashboard.table.currency"),
                t("dashboard.table.balance"),
                t("dashboard.table.status"),
            )
        )

        self._best_table.set_empty_state(
            t("dashboard.empty.products.title"),
            t("dashboard.empty.products.hint"),
        )
        self._slow_table.set_empty_state(
            t("dashboard.empty.attention.title"),
            t("dashboard.empty.attention.hint"),
        )
        self._accounts_table.set_empty_state(
            t("dashboard.empty.accounts.title"),
            t("dashboard.empty.accounts.hint"),
        )

        self._sales_chart.set_empty_text(
            t("dashboard.empty.sales.title"),
            t("dashboard.empty.sales.hint"),
        )
        self._revenue_chart.set_empty_text(
            t("dashboard.empty.revenue.title"),
            t("dashboard.empty.revenue.hint"),
        )
        self._product_chart.set_empty_text(
            t("dashboard.empty.products_chart.title"),
            t("dashboard.empty.products_chart.hint"),
        )

        self._sales_chart.setAccessibleName(
            t("dashboard.chart.sales.title")
        )
        self._sales_chart.setAccessibleDescription(
            t("dashboard.chart.sales.description")
        )
        self._revenue_chart.setAccessibleName(
            t("dashboard.chart.revenue.title")
        )
        self._revenue_chart.setAccessibleDescription(
            t("dashboard.chart.revenue.description")
        )
        self._product_chart.setAccessibleName(
            t("dashboard.chart.products.title")
        )
        self._product_chart.setAccessibleDescription(
            t("dashboard.chart.products.description")
        )
        self._best_table.set_accessible_name(
            t("dashboard.table.best_accessible"),
            t("dashboard.chart.products.description"),
        )
        self._slow_table.set_accessible_name(
            t("dashboard.attention.title"),
            t("dashboard.attention.description"),
        )
        self._accounts_table.set_accessible_name(
            t("dashboard.accounts.title"),
            t("dashboard.accounts.description"),
        )

        if (
            self._last_report is not None
            and self._last_performance is not None
            and self._last_charts is not None
        ):
            self._render(
                self._last_report,
                self._last_performance,
                self._last_charts,
            )


def _margin_text(value, label: str, unavailable: str) -> str:
    if value is None:
        return unavailable
    return f"{label} {float(value):.1f}%"
