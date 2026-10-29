"""Application services for Dashboard and Analytics screens."""

from __future__ import annotations

from dataclasses import dataclass

from app.application.analytics.account_balances import GetAccountBalances
from app.application.analytics.business_summary import GetBusinessSummary
from app.application.analytics.consolidated_report import (
    GetConsolidatedReport,
)
from app.application.analytics.dashboard_charts import (
    ChartAmount,
    ChartQuantity,
    DashboardChartData,
    GetSalesEvolution,
)
from app.application.analytics.inventory_value import GetInventoryValue
from app.application.analytics.models import (
    AnalyticsFilters,
    AnalyticsPeriod,
    ConsolidatedReport,
    ProductPerformanceReport,
    SupplierProfitabilityReport,
)
from app.application.analytics.product_performance import (
    GetProductPerformance,
)
from app.application.analytics.supplier_profitability import (
    GetSupplierProfitability,
)
from app.application.unit_of_work import UnitOfWorkFactory


@dataclass(frozen=True, slots=True)
class DashboardSnapshot:
    """Base-currency overview plus product highlights."""

    report: ConsolidatedReport
    performance: ProductPerformanceReport


@dataclass(frozen=True, slots=True)
class DashboardOverview:
    """Dashboard read models plus prepared chart series."""

    report: ConsolidatedReport
    performance: ProductPerformanceReport
    charts: DashboardChartData


@dataclass(frozen=True, slots=True)
class AnalyticsSnapshot:
    """Full analytics result for a selected period."""

    report: ConsolidatedReport
    performance: ProductPerformanceReport
    suppliers: SupplierProfitabilityReport


class AnalyticsService:
    """Run analytics use cases within explicit unit-of-work boundaries."""

    def __init__(
        self,
        unit_of_work: UnitOfWorkFactory,
        *,
        base_currency: str,
        slow_moving_days: int = 30,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._base_currency = base_currency
        self._slow_moving_days = slow_moving_days

    def dashboard(self) -> DashboardSnapshot:
        period = AnalyticsPeriod()
        with self._unit_of_work.unit_of_work() as uow:
            report = self._consolidated(uow, period)
            performance = GetProductPerformance(
                uow.analytics,
                slow_moving_days=self._slow_moving_days,
            ).execute(period, limit=8)
            return DashboardSnapshot(
                report=report, performance=performance
            )

    def dashboard_overview(
        self,
        period: AnalyticsPeriod | None = None,
        filters: AnalyticsFilters | None = None,
        *,
        limit: int = 8,
    ) -> DashboardOverview:
        """Return the Dashboard snapshot with presentation-ready chart data."""
        period = period or AnalyticsPeriod()
        with self._unit_of_work.unit_of_work() as uow:
            report = self._consolidated(uow, period, filters)
            performance = GetProductPerformance(
                uow.analytics,
                slow_moving_days=self._slow_moving_days,
            ).execute(period, filters, limit=limit)
            evolution = GetSalesEvolution(
                uow.analytics,
                uow.exchange_rates,
            ).execute(
                period,
                filters,
                as_of=report.as_of,
                base_currency=report.base_currency,
            )
            charts = DashboardChartData(
                sales_evolution=evolution.points,
                granularity=evolution.granularity,
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
                    if product.net_quantity > 0
                ),
            )
            return DashboardOverview(
                report=report,
                performance=performance,
                charts=charts,
            )

    def analytics(
        self,
        period: AnalyticsPeriod,
        filters: AnalyticsFilters | None = None,
        *,
        limit: int = 10,
    ) -> AnalyticsSnapshot:
        with self._unit_of_work.unit_of_work() as uow:
            report = self._consolidated(uow, period, filters)
            performance = GetProductPerformance(
                uow.analytics,
                slow_moving_days=self._slow_moving_days,
            ).execute(period, filters, limit=limit)
            suppliers = GetSupplierProfitability(uow.analytics).execute(
                period, filters
            )
            return AnalyticsSnapshot(
                report=report,
                performance=performance,
                suppliers=suppliers,
            )

    def _consolidated(
        self,
        uow,
        period: AnalyticsPeriod,
        filters: AnalyticsFilters | None = None,
    ) -> ConsolidatedReport:
        return GetConsolidatedReport(
            summary=GetBusinessSummary(uow.analytics),
            inventory=GetInventoryValue(uow.analytics),
            accounts=GetAccountBalances(
                uow.accounts, uow.transactions
            ),
            currencies=uow.currencies,
            exchange_rates=uow.exchange_rates,
            capital_movements=uow.capital_movements,
            base_currency=self._base_currency,
        ).execute(period, filters)
