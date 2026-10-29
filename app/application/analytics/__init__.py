"""Analytics application use cases and read models."""

from app.application.analytics.account_balances import GetAccountBalances
from app.application.analytics.business_summary import GetBusinessSummary
from app.application.analytics.consolidated_report import (
    GetConsolidatedReport,
)
from app.application.analytics.dashboard_charts import (
    ChartAmount,
    ChartGranularity,
    ChartQuantity,
    DashboardChartData,
    GetSalesEvolution,
    SalesEvolution,
    SalesEvolutionPoint,
)
from app.application.analytics.inventory_value import GetInventoryValue
from app.application.analytics.models import (
    AccountBalance,
    AccountBalancesReport,
    AnalyticsFilters,
    AnalyticsPeriod,
    BusinessSummary,
    ConsolidatedReport,
    CurrencyMargin,
    CustomerReturnAllocationRecord,
    ExpenseRecord,
    InventoryLotRecord,
    InventoryValueReport,
    LastSaleRecord,
    MissingExchangeRate,
    ProductPerformance,
    ProductPerformanceReport,
    ProductProfitability,
    SaleAllocationRecord,
    SlowMovingProduct,
    SupplierProfitability,
    SupplierProfitabilityReport,
    SupplierReturnItemRecord,
)
from app.application.analytics.ports import AnalyticsRepository
from app.application.analytics.product_performance import (
    GetProductPerformance,
)
from app.application.analytics.supplier_profitability import (
    GetSupplierProfitability,
)

__all__ = [
    "AccountBalance",
    "AccountBalancesReport",
    "AnalyticsFilters",
    "AnalyticsPeriod",
    "AnalyticsRepository",
    "BusinessSummary",
    "ChartAmount",
    "ChartGranularity",
    "ChartQuantity",
    "ConsolidatedReport",
    "CurrencyMargin",
    "CustomerReturnAllocationRecord",
    "DashboardChartData",
    "ExpenseRecord",
    "GetAccountBalances",
    "GetBusinessSummary",
    "GetConsolidatedReport",
    "GetInventoryValue",
    "GetSalesEvolution",
    "GetProductPerformance",
    "GetSupplierProfitability",
    "InventoryLotRecord",
    "InventoryValueReport",
    "LastSaleRecord",
    "MissingExchangeRate",
    "ProductPerformance",
    "ProductPerformanceReport",
    "ProductProfitability",
    "SaleAllocationRecord",
    "SalesEvolution",
    "SalesEvolutionPoint",
    "SlowMovingProduct",
    "SupplierProfitability",
    "SupplierProfitabilityReport",
    "SupplierReturnItemRecord",
]
