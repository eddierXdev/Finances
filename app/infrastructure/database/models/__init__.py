"""ORM models.

Importing this module registers every model on ``Base.metadata`` for Alembic.
"""

from app.infrastructure.database.models.account import AccountModel
from app.infrastructure.database.models.account_transfer import (
    AccountTransferModel,
)
from app.infrastructure.database.models.attribute import (
    AttributeModel,
    AttributeValueModel,
)
from app.infrastructure.database.models.capital_movement import (
    CapitalMovementModel,
)
from app.infrastructure.database.models.category import CategoryModel
from app.infrastructure.database.models.currency import CurrencyModel
from app.infrastructure.database.models.customer import CustomerModel
from app.infrastructure.database.models.customer_return import (
    CustomerReturnModel,
)
from app.infrastructure.database.models.customer_return_item import (
    CustomerReturnItemModel,
)
from app.infrastructure.database.models.exchange_rate import ExchangeRateModel
from app.infrastructure.database.models.expense import ExpenseModel
from app.infrastructure.database.models.financial_transaction import (
    FinancialTransactionModel,
)
from app.infrastructure.database.models.inventory_lot import InventoryLotModel
from app.infrastructure.database.models.inventory_movement import (
    InventoryMovementModel,
)
from app.infrastructure.database.models.product import ProductModel
from app.infrastructure.database.models.product_variant import ProductVariantModel
from app.infrastructure.database.models.purchase import PurchaseModel
from app.infrastructure.database.models.purchase_cost import PurchaseCostModel
from app.infrastructure.database.models.purchase_cost_allocation import (
    PurchaseCostAllocationModel,
)
from app.infrastructure.database.models.purchase_item import PurchaseItemModel
from app.infrastructure.database.models.sale import SaleModel
from app.infrastructure.database.models.sale_item import SaleItemModel
from app.infrastructure.database.models.setting import SettingModel
from app.infrastructure.database.models.return_lot_allocation import (
    ReturnLotAllocationModel,
)
from app.infrastructure.database.models.sale_item_lot_allocation import (
    SaleItemLotAllocationModel,
)
from app.infrastructure.database.models.supplier import SupplierModel
from app.infrastructure.database.models.supplier_return import (
    SupplierReturnModel,
)
from app.infrastructure.database.models.supplier_return_item import (
    SupplierReturnItemModel,
)
from app.infrastructure.database.models.variant_attribute_value import (
    VariantAttributeValueModel,
)

__all__ = [
    "AccountModel",
    "AccountTransferModel",
    "AttributeModel",
    "AttributeValueModel",
    "CapitalMovementModel",
    "CategoryModel",
    "CurrencyModel",
    "CustomerModel",
    "CustomerReturnItemModel",
    "CustomerReturnModel",
    "ExchangeRateModel",
    "ExpenseModel",
    "FinancialTransactionModel",
    "InventoryLotModel",
    "InventoryMovementModel",
    "ProductModel",
    "ProductVariantModel",
    "PurchaseCostAllocationModel",
    "PurchaseCostModel",
    "PurchaseItemModel",
    "PurchaseModel",
    "ReturnLotAllocationModel",
    "SaleItemLotAllocationModel",
    "SaleItemModel",
    "SaleModel",
    "SettingModel",
    "SupplierModel",
    "SupplierReturnItemModel",
    "SupplierReturnModel",
    "VariantAttributeValueModel",
]
