"""Analytics application use cases and read models."""

from app.application.analytics.account_balances import GetAccountBalances
from app.application.analytics.business_summary import GetBusinessSummary
from app.application.analytics.consolidated_report import (
    GetConsolidatedReport,
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
    "ConsolidatedReport",
    "CurrencyMargin",
    "CustomerReturnAllocationRecord",
    "ExpenseRecord",
    "GetAccountBalances",
    "GetBusinessSummary",
    "GetConsolidatedReport",
    "GetInventoryValue",
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
    "SlowMovingProduct",
    "SupplierProfitability",
    "SupplierProfitabilityReport",
    "SupplierReturnItemRecord",
]
