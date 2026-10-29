"""Application-level transaction boundary.

Use cases only flush changes. The caller opens a unit of work, runs one or more
use cases and explicitly commits. Infrastructure supplies the implementation.
"""

from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Protocol

from app.application.analytics.ports import AnalyticsRepository
from app.domain.repositories.account_repository import AccountRepository
from app.domain.repositories.account_transfer_repository import (
    AccountTransferRepository,
)
from app.domain.repositories.attribute_repository import AttributeRepository
from app.domain.repositories.attribute_value_repository import (
    AttributeValueRepository,
)
from app.domain.repositories.capital_movement_repository import (
    CapitalMovementRepository,
)
from app.domain.repositories.category_repository import CategoryRepository
from app.domain.repositories.currency_repository import CurrencyRepository
from app.domain.repositories.customer_repository import CustomerRepository
from app.domain.repositories.customer_return_item_repository import (
    CustomerReturnItemRepository,
)
from app.domain.repositories.customer_return_repository import (
    CustomerReturnRepository,
)
from app.domain.repositories.exchange_rate_repository import (
    ExchangeRateRepository,
)
from app.domain.repositories.expense_repository import ExpenseRepository
from app.domain.repositories.financial_transaction_repository import (
    FinancialTransactionRepository,
)
from app.domain.repositories.inventory_lot_repository import (
    InventoryLotRepository,
)
from app.domain.repositories.inventory_movement_repository import (
    InventoryMovementRepository,
)
from app.domain.repositories.product_repository import ProductRepository
from app.domain.repositories.product_variant_repository import (
    ProductVariantRepository,
)
from app.domain.repositories.purchase_cost_allocation_repository import (
    PurchaseCostAllocationRepository,
)
from app.domain.repositories.purchase_cost_repository import (
    PurchaseCostRepository,
)
from app.domain.repositories.purchase_item_repository import (
    PurchaseItemRepository,
)
from app.domain.repositories.purchase_repository import PurchaseRepository
from app.domain.repositories.return_lot_allocation_repository import (
    ReturnLotAllocationRepository,
)
from app.domain.repositories.sale_item_lot_allocation_repository import (
    SaleItemLotAllocationRepository,
)
from app.domain.repositories.sale_item_repository import SaleItemRepository
from app.domain.repositories.sale_repository import SaleRepository
from app.domain.repositories.settings_repository import SettingsRepository
from app.domain.repositories.supplier_repository import SupplierRepository
from app.domain.repositories.supplier_return_item_repository import (
    SupplierReturnItemRepository,
)
from app.domain.repositories.supplier_return_repository import (
    SupplierReturnRepository,
)


class UnitOfWork(Protocol):
    """Repositories and commit control for one business operation."""

    products: ProductRepository
    variants: ProductVariantRepository
    categories: CategoryRepository
    currencies: CurrencyRepository
    attributes: AttributeRepository
    attribute_values: AttributeValueRepository
    accounts: AccountRepository
    transactions: FinancialTransactionRepository
    suppliers: SupplierRepository
    purchases: PurchaseRepository
    purchase_items: PurchaseItemRepository
    purchase_costs: PurchaseCostRepository
    purchase_allocations: PurchaseCostAllocationRepository
    exchange_rates: ExchangeRateRepository
    inventory_lots: InventoryLotRepository
    inventory_movements: InventoryMovementRepository
    customers: CustomerRepository
    sales: SaleRepository
    sale_items: SaleItemRepository
    sale_allocations: SaleItemLotAllocationRepository
    customer_returns: CustomerReturnRepository
    customer_return_items: CustomerReturnItemRepository
    return_allocations: ReturnLotAllocationRepository
    supplier_returns: SupplierReturnRepository
    supplier_return_items: SupplierReturnItemRepository
    expenses: ExpenseRepository
    capital_movements: CapitalMovementRepository
    transfers: AccountTransferRepository
    analytics: AnalyticsRepository
    settings: SettingsRepository

    def commit(self) -> None:
        """Persist the current operation."""
        ...

    def rollback(self) -> None:
        """Discard the current operation."""
        ...


class UnitOfWorkFactory(Protocol):
    """Create a unit of work that closes its resources on exit."""

    def unit_of_work(self) -> AbstractContextManager[UnitOfWork]:
        """Return a context-managed unit of work."""
        ...
