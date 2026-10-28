"""Application-level transaction boundary.

Use cases only flush changes. The caller opens a unit of work, runs one or more
use cases and explicitly commits. Infrastructure supplies the implementation.
"""

from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Protocol

from app.domain.repositories.account_repository import AccountRepository
from app.domain.repositories.attribute_repository import AttributeRepository
from app.domain.repositories.attribute_value_repository import (
    AttributeValueRepository,
)
from app.domain.repositories.category_repository import CategoryRepository
from app.domain.repositories.currency_repository import CurrencyRepository
from app.domain.repositories.exchange_rate_repository import (
    ExchangeRateRepository,
)
from app.domain.repositories.financial_transaction_repository import (
    FinancialTransactionRepository,
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
from app.domain.repositories.supplier_repository import SupplierRepository


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
