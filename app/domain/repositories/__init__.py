"""Domain repository contracts."""

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
from app.domain.repositories.supplier_repository import SupplierRepository
from app.domain.repositories.supplier_return_item_repository import (
    SupplierReturnItemRepository,
)
from app.domain.repositories.supplier_return_repository import (
    SupplierReturnRepository,
)

__all__ = [
    "AccountRepository",
    "AccountTransferRepository",
    "AttributeRepository",
    "AttributeValueRepository",
    "CapitalMovementRepository",
    "CategoryRepository",
    "CurrencyRepository",
    "CustomerRepository",
    "CustomerReturnItemRepository",
    "CustomerReturnRepository",
    "ExchangeRateRepository",
    "ExpenseRepository",
    "FinancialTransactionRepository",
    "InventoryLotRepository",
    "InventoryMovementRepository",
    "ProductRepository",
    "ProductVariantRepository",
    "PurchaseCostAllocationRepository",
    "PurchaseCostRepository",
    "PurchaseItemRepository",
    "PurchaseRepository",
    "ReturnLotAllocationRepository",
    "SaleItemLotAllocationRepository",
    "SaleItemRepository",
    "SaleRepository",
    "SupplierRepository",
    "SupplierReturnItemRepository",
    "SupplierReturnRepository",
]
