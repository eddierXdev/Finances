"""Dashboard V2, chart and shell component tests (headless)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import QLabel, QTableView, QTabWidget

from app.application.analytics.dashboard_charts import (
    ChartAmount,
    ChartQuantity,
    DashboardChartData,
    SalesEvolutionPoint,
)
from app.domain.entities.currency import Currency
from app.domain.value_objects.money import Money
from app.presentation.desktop.components.filter_bar import PeriodFilter
from app.presentation.desktop.i18n.translator import Translator
from app.presentation.desktop.navigation import NAVIGATION_ITEMS
from app.presentation.desktop.navigation.sidebar import Sidebar
from app.presentation.desktop.themes.theme_manager import ThemeManager
from app.presentation.desktop.views.dashboard import DashboardPage

NOW = datetime(2026, 10, 28, 12, 0, tzinfo=UTC)


def _currency(code: str = "USD") -> Currency:
    return Currency(code, code, 2)


def _dashboard_fake(*, empty: bool = False):
    usd = _currency()
    eur = _currency("EUR")

    if empty:
        report = SimpleNamespace(
            period=SimpleNamespace(start=None, end=None),
            base_currency=usd,
            as_of=NOW,
            revenue=Money("0.00", usd),
            cogs=Money("0.00", usd),
            gross_profit=Money("0.00", usd),
            expenses=Money("0.00", usd),
            net_profit=Money("0.00", usd),
            inventory_value=Money("0.00", usd),
            available_capital=Money("0.00", usd),
            invested_capital=Money("0.00", usd),
            gross_margin=None,
            net_margin=None,
            roi=None,
            roi_average_capital=Money("0.00", usd),
            missing_rates=(),
            is_complete=True,
            native_inventory=SimpleNamespace(total_units=0),
            native_accounts=SimpleNamespace(accounts=()),
        )
        performance = SimpleNamespace(best_sellers=(), slow_moving=())
        charts = DashboardChartData(
            sales_evolution=(),
            granularity="day",
            revenue_expenses=(),
            top_products=(),
        )
    else:
        report = SimpleNamespace(
            period=SimpleNamespace(
                start=NOW - timedelta(days=90),
                end=NOW,
            ),
            base_currency=usd,
            as_of=NOW,
            revenue=Money("2840.00", usd),
            cogs=Money("1580.00", usd),
            gross_profit=Money("1260.00", usd),
            expenses=Money("630.00", usd),
            net_profit=Money("630.00", usd),
            inventory_value=Money("1220.00", usd),
            available_capital=Money("880.00", usd),
            invested_capital=Money("1220.00", usd),
            gross_margin=Decimal("44.3662"),
            net_margin=Decimal("22.1831"),
            roi=Decimal("12.5000"),
            roi_average_capital=Money("900.00", usd),
            missing_rates=(),
            is_complete=True,
            native_inventory=SimpleNamespace(total_units=42),
            native_accounts=SimpleNamespace(
                accounts=(
                    SimpleNamespace(
                        account_name="Cash USD",
                        currency=usd,
                        balance=Money("600.00", usd),
                        is_active=True,
                    ),
                    SimpleNamespace(
                        account_name="Bank EUR",
                        currency=eur,
                        balance=Money("280.00", eur),
                        is_active=True,
                    ),
                )
            ),
        )
        performance = SimpleNamespace(
            best_sellers=tuple(
                SimpleNamespace(
                    product_name=f"Product {index}",
                    net_quantity=12 - index,
                    revenue=(Money(f"{(12 - index) * 12}.00", usd),),
                )
                for index in range(1, 7)
            ),
            slow_moving=(
                SimpleNamespace(
                    product_name="Old Phone",
                    remaining_quantity=4,
                    inventory_value=(Money("120.00", usd),),
                    last_sale_date=NOW - timedelta(days=45),
                ),
                SimpleNamespace(
                    product_name="Spare Case",
                    remaining_quantity=9,
                    inventory_value=(Money("45.00", usd),),
                    last_sale_date=None,
                ),
                SimpleNamespace(
                    product_name="Vintage Camera",
                    remaining_quantity=2,
                    inventory_value=(Money("320.00", usd),),
                    last_sale_date=NOW - timedelta(days=120),
                ),
            ),
        )
        charts = DashboardChartData(
            sales_evolution=tuple(
                SalesEvolutionPoint(
                    period_start=NOW - timedelta(days=90 - index),
                    revenue=Money(str(100 + index * 22), usd),
                )
                for index in range(0, 90, 5)
            ),
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
                for product in performance.best_sellers
            ),
        )

    class FakeAnalytics:
        def dashboard_overview(self, period, filters=None, *, limit=8):
            return SimpleNamespace(
                report=report,
                performance=performance,
                charts=charts,
            )

    return FakeAnalytics()


def test_dashboard_renders_charts_tables_and_retranslates(qapp) -> None:
    translator = Translator("en")
    manager = ThemeManager("light")
    manager.apply(qapp)
    page = DashboardPage(
        _dashboard_fake(),
        base_currency="USD",
        translator=translator,
        theme_manager=manager,
    )
    page.resize(1120, 1250)
    page.show()
    qapp.processEvents()

    title = page.findChild(QLabel, "pageTitle")
    assert title is not None
    assert title.text() == "Dashboard"
    assert len(page.findChildren(QLabel, "metricValue")) == 6

    best = page.findChild(QTableView, "dashboardBestSellersTable")
    slow = page.findChild(QTableView, "dashboardSlowMovingTable")
    accounts = page.findChild(QTableView, "dashboardAccountsTable")
    assert best is not None
    assert slow is not None
    assert accounts is not None
    assert best.model().rowCount() == 6
    assert slow.model().rowCount() == 3
    assert accounts.model().rowCount() == 2
    assert best.model().headerData(0, Qt.Orientation.Horizontal) == "Product"

    tabs = page.findChild(QTabWidget, "dashboardProductsTabs")
    assert tabs is not None
    assert tabs.count() == 2
    assert tabs.tabText(0) == "Chart"
    assert page._sales_chart.toolTip()
    assert page._sales_chart.chart_palette.accent == "#2563eb"

    shot = page.grab()
    assert not shot.isNull()

    manager.set_theme("dark")
    qapp.processEvents()
    assert page._sales_chart.chart_palette.accent == "#60a5fa"
    assert page._revenue_chart.chart_palette.accent == "#60a5fa"

    translator.set_language("es")
    qapp.processEvents()
    assert title.text() == "Panel"
    assert best.model().headerData(0, Qt.Orientation.Horizontal) == "Producto"
    assert tabs.tabText(0) == "Gráfico"
    assert slow.model().index(1, 3).data() == "Nunca"

    manager.set_theme("light")
    page.close()


def test_dashboard_shows_empty_states(qapp) -> None:
    translator = Translator("en")
    page = DashboardPage(
        _dashboard_fake(empty=True),
        base_currency="USD",
        translator=translator,
    )
    page.show()
    qapp.processEvents()

    assert page._sales_chart.toolTip().startswith("No sales in this period")
    assert page._revenue_chart.toolTip().startswith("No financial data")
    assert page._best_table.empty_state.title_label.text() == (
        "No product sales in this period"
    )
    assert page._slow_table.empty_state.title_label.text() == (
        "No slow-moving stock"
    )
    assert page._accounts_table.empty_state.title_label.text() == (
        "No accounts yet"
    )
    assert not page.grab().isNull()
    page.close()


def test_period_filter_presets_custom_range_and_retranslation(qapp) -> None:
    translator = Translator("en")
    period_filter = PeriodFilter(translator)
    period_filter.show()
    qapp.processEvents()

    emitted = []
    period_filter.period_changed.connect(emitted.append)
    assert period_filter.combo.itemText(0) == "All time"

    period_filter.combo.setCurrentIndex(1)
    assert len(emitted) == 1
    assert emitted[0].start is not None
    assert emitted[0].end is not None

    period_filter.combo.setCurrentIndex(4)
    assert not period_filter.start_date.isHidden()
    period_filter.start_date.setDate(QDate(2026, 1, 1))
    period_filter.end_date.setDate(QDate(2026, 1, 31))
    period_filter.apply_button.click()
    assert len(emitted) == 2
    assert emitted[-1].start == datetime(2026, 1, 1, tzinfo=UTC)
    assert emitted[-1].end == datetime(
        2026, 1, 31, 23, 59, 59, tzinfo=UTC
    )

    translator.set_language("es")
    assert period_filter.combo.itemText(0) == "Todo el historial"
    assert period_filter.apply_button.text() == "Aplicar"
    assert period_filter.combo.accessibleName() == "Período del panel"
    period_filter.close()


def test_sidebar_retranslates_navigation_and_accessibility(qapp) -> None:
    translator = Translator("en")
    sidebar = Sidebar(
        NAVIGATION_ITEMS,
        app_name="Resale Manager",
        base_currency="USD",
        translator=translator,
    )

    assert sidebar.navigation.count() == len(NAVIGATION_ITEMS)
    assert sidebar.navigation.item(0).data(Qt.ItemDataRole.UserRole) == (
        "dashboard"
    )
    assert sidebar.navigation.focusPolicy() == Qt.FocusPolicy.StrongFocus
    assert sidebar.navigation.accessibleName() == "Main navigation"
    assert sidebar.navigation.item(0).toolTip() == (
        "Business overview, capital and profit at a glance."
    )

    translator.set_language("es")
    assert sidebar.navigation.item(0).text() == "Panel"
    assert sidebar.navigation.item(0).toolTip() == (
        "Resumen del negocio, capital y ganancias de un vistazo."
    )
    assert sidebar.status_badge.text() == "Modo sin conexión"
    assert sidebar.currency_label.text() == "Moneda base: USD"
    assert sidebar.brand_subtitle.text() == "Operaciones de reventa"
