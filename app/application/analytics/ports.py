"""Read-model repository contract for analytics."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from app.application.analytics.models import (
    AnalyticsFilters,
    AnalyticsPeriod,
    CustomerReturnAllocationRecord,
    ExpenseRecord,
    InventoryLotRecord,
    LastSaleRecord,
    SaleAllocationRecord,
    SupplierReturnItemRecord,
)


class AnalyticsRepository(Protocol):
    """Persistence boundary for flat analytics records.

    Implementations may join tables for efficiency, but they must return
    application read models rather than ORM objects. Money remains ``Decimal``
    until the application layer wraps it in ``Money``.
    """

    def list_sale_allocations(
        self,
        period: AnalyticsPeriod,
        filters: AnalyticsFilters,
    ) -> list[SaleAllocationRecord]:
        """Return one row per FIFO allocation for non-cancelled sales."""
        ...

    def list_customer_return_allocations(
        self,
        period: AnalyticsPeriod,
        filters: AnalyticsFilters,
    ) -> list[CustomerReturnAllocationRecord]:
        """Return one row per reversed FIFO allocation in the period."""
        ...

    def list_supplier_return_items(
        self,
        period: AnalyticsPeriod,
        filters: AnalyticsFilters,
    ) -> list[SupplierReturnItemRecord]:
        """Return supplier return lines recorded in the period."""
        ...

    def list_expenses(
        self,
        period: AnalyticsPeriod,
        filters: AnalyticsFilters,
    ) -> list[ExpenseRecord]:
        """Return operating expenses recorded in the period."""
        ...

    def list_inventory_lots(
        self,
        as_of: datetime,
        filters: AnalyticsFilters,
    ) -> list[InventoryLotRecord]:
        """Return current lots with remaining stock."""
        ...

    def list_last_sale_dates(
        self,
        as_of: datetime,
        filters: AnalyticsFilters,
    ) -> list[LastSaleRecord]:
        """Return the latest non-cancelled sale date per variant."""
        ...
