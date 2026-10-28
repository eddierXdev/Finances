"""Mapping between ORM models and domain objects."""

from app.domain.entities.account import Account
from app.domain.entities.account_transfer import AccountTransfer
from app.domain.entities.attribute import Attribute, AttributeValue
from app.domain.entities.capital_movement import CapitalMovement
from app.domain.entities.category import Category
from app.domain.entities.currency import Currency
from app.domain.entities.customer_return import CustomerReturn
from app.domain.entities.customer_return_item import CustomerReturnItem
from app.domain.entities.exchange_rate import ExchangeRate
from app.domain.entities.expense import Expense
from app.domain.entities.financial_transaction import FinancialTransaction
from app.domain.entities.inventory_lot import InventoryLot
from app.domain.entities.inventory_movement import InventoryMovement
from app.domain.entities.product import Product
from app.domain.entities.product_variant import ProductVariant
from app.domain.entities.purchase import Purchase
from app.domain.entities.purchase_cost import PurchaseCost
from app.domain.entities.purchase_cost_allocation import (
    PurchaseCostAllocation,
)
from app.domain.entities.purchase_item import PurchaseItem
from app.domain.entities.return_lot_allocation import ReturnLotAllocation
from app.domain.entities.sale import Sale
from app.domain.entities.sale_item import SaleItem
from app.domain.entities.sale_item_lot_allocation import (
    SaleItemLotAllocation,
)
from app.domain.entities.supplier import Supplier
from app.domain.entities.supplier_return import SupplierReturn
from app.domain.entities.supplier_return_item import SupplierReturnItem
from app.domain.enums.allocation_method import AllocationMethod
from app.domain.enums.capital_movement_type import CapitalMovementType
from app.domain.enums.exchange_rate_source import ExchangeRateSource
from app.domain.enums.expense_type import ExpenseType
from app.domain.enums.financial_transaction_type import (
    FinancialTransactionType,
)
from app.domain.enums.inventory_movement_type import InventoryMovementType
from app.domain.enums.purchase_cost_type import PurchaseCostType
from app.domain.enums.purchase_status import PurchaseStatus
from app.domain.enums.return_condition import ReturnCondition
from app.domain.enums.sale_status import SaleStatus
from app.domain.value_objects.money import Money
from app.infrastructure.database.models import (
    AccountModel,
    AccountTransferModel,
    AttributeModel,
    AttributeValueModel,
    CapitalMovementModel,
    CategoryModel,
    CurrencyModel,
    CustomerReturnItemModel,
    CustomerReturnModel,
    ExchangeRateModel,
    ExpenseModel,
    FinancialTransactionModel,
    InventoryLotModel,
    InventoryMovementModel,
    ProductModel,
    ProductVariantModel,
    PurchaseCostAllocationModel,
    PurchaseCostModel,
    PurchaseItemModel,
    PurchaseModel,
    ReturnLotAllocationModel,
    SaleItemLotAllocationModel,
    SaleItemModel,
    SaleModel,
    SupplierModel,
    SupplierReturnItemModel,
    SupplierReturnModel,
)


def currency_to_domain(model: CurrencyModel) -> Currency:
    return Currency(
        code=model.code,
        name=model.name,
        decimal_places=model.decimal_places,
        symbol=model.symbol,
        is_enabled=model.is_enabled,
        id=model.id,
    )


def exchange_rate_to_domain(model: ExchangeRateModel) -> ExchangeRate:
    return ExchangeRate(
        base_currency=currency_to_domain(model.base_currency),
        quote_currency=currency_to_domain(model.quote_currency),
        rate=model.rate,
        source=ExchangeRateSource(model.source),
        rate_timestamp=model.rate_timestamp,
        notes=model.notes,
        id=model.id,
    )


def account_to_domain(model: AccountModel) -> Account:
    return Account(
        name=model.name,
        currency=currency_to_domain(model.currency),
        account_type=model.account_type,
        is_active=model.is_active,
        notes=model.notes,
        id=model.id,
    )


def supplier_to_domain(model: SupplierModel) -> Supplier:
    return Supplier(
        name=model.name,
        supplier_type=model.supplier_type,
        website=model.website,
        contact=model.contact,
        notes=model.notes,
        is_active=model.is_active,
        id=model.id,
    )


def purchase_to_domain(model: PurchaseModel) -> Purchase:
    return Purchase(
        currency=currency_to_domain(model.currency),
        purchase_date=model.purchase_date,
        supplier_id=model.supplier_id,
        account=(
            account_to_domain(model.account)
            if model.account is not None
            else None
        ),
        status=PurchaseStatus(model.status),
        order_number=model.order_number,
        tracking_number=model.tracking_number,
        notes=model.notes,
        id=model.id,
    )


def purchase_item_to_domain(model: PurchaseItemModel) -> PurchaseItem:
    purchase = purchase_to_domain(model.purchase)
    return PurchaseItem(
        purchase=purchase,
        variant_id=model.variant_id,
        quantity=model.quantity,
        unit_price=Money(model.unit_price, purchase.currency),
        weight=model.weight,
        id=model.id,
    )


def purchase_cost_to_domain(model: PurchaseCostModel) -> PurchaseCost:
    return PurchaseCost(
        purchase=purchase_to_domain(model.purchase),
        cost_type=PurchaseCostType(model.cost_type),
        amount=Money(model.amount, currency_to_domain(model.currency)),
        allocation_method=AllocationMethod(model.allocation_method),
        exchange_rate=(
            exchange_rate_to_domain(model.exchange_rate)
            if model.exchange_rate is not None
            else None
        ),
        description=model.description,
        id=model.id,
    )


def purchase_cost_allocation_to_domain(
    model: PurchaseCostAllocationModel,
) -> PurchaseCostAllocation:
    cost = purchase_cost_to_domain(model.purchase_cost)
    item = purchase_item_to_domain(model.purchase_item)
    return PurchaseCostAllocation(
        purchase_cost=cost,
        purchase_item=item,
        allocated_original_amount=Money(
            model.allocated_original_amount, cost.amount.currency
        ),
        allocated_purchase_currency_amount=Money(
            model.allocated_purchase_currency_amount,
            cost.purchase.currency,
        ),
        id=model.id,
    )


def inventory_lot_to_domain(model: InventoryLotModel) -> InventoryLot:
    return InventoryLot(
        purchase_item=purchase_item_to_domain(model.purchase_item),
        variant_id=model.variant_id,
        acquired_quantity=model.acquired_quantity,
        remaining_quantity=model.remaining_quantity,
        unit_cost=Money(
            model.unit_cost, currency_to_domain(model.currency)
        ),
        received_at=model.received_at,
        id=model.id,
    )


def inventory_movement_to_domain(
    model: InventoryMovementModel,
) -> InventoryMovement:
    unit_cost = None
    if model.unit_cost is not None:
        if model.currency is None:
            raise ValueError(
                "An inventory movement with unit cost has no currency."
            )
        unit_cost = Money(
            model.unit_cost, currency_to_domain(model.currency)
        )

    return InventoryMovement(
        variant_id=model.variant_id,
        movement_type=InventoryMovementType(model.movement_type),
        quantity=model.quantity,
        movement_date=model.movement_date,
        inventory_lot_id=model.inventory_lot_id,
        unit_cost=unit_cost,
        reference_type=model.reference_type,
        reference_id=model.reference_id,
        notes=model.notes,
        id=model.id,
    )


def sale_to_domain(model: SaleModel) -> Sale:
    currency = currency_to_domain(model.currency)
    return Sale(
        account=account_to_domain(model.account),
        currency=currency,
        sale_date=model.sale_date,
        customer_id=model.customer_id,
        status=SaleStatus(model.status),
        discount_amount=(
            Money(model.discount_amount, currency)
            if model.discount_amount is not None
            else None
        ),
        notes=model.notes,
        id=model.id,
    )


def sale_item_to_domain(model: SaleItemModel) -> SaleItem:
    sale = sale_to_domain(model.sale)
    return SaleItem(
        sale=sale,
        variant_id=model.variant_id,
        quantity=model.quantity,
        unit_price=Money(model.unit_price, sale.currency),
        discount_amount=(
            Money(model.discount_amount, sale.currency)
            if model.discount_amount is not None
            else None
        ),
        id=model.id,
    )


def sale_item_lot_allocation_to_domain(
    model: SaleItemLotAllocationModel,
) -> SaleItemLotAllocation:
    item = sale_item_to_domain(model.sale_item)
    lot = inventory_lot_to_domain(model.inventory_lot)
    return SaleItemLotAllocation(
        sale_item=item,
        inventory_lot=lot,
        quantity=model.quantity,
        unit_cost_snapshot=Money(
            model.unit_cost_snapshot, lot.unit_cost.currency
        ),
        id=model.id,
    )


def customer_return_to_domain(
    model: CustomerReturnModel,
) -> CustomerReturn:
    sale = sale_to_domain(model.sale)
    account = (
        account_to_domain(model.account)
        if model.account is not None
        else None
    )
    refund_amount = None
    if model.refund_amount is not None:
        if model.refund_currency is None:
            raise ValueError(
                "A customer return with a refund has no refund currency."
            )
        refund_amount = Money(
            model.refund_amount,
            currency_to_domain(model.refund_currency),
        )

    return CustomerReturn(
        sale=sale,
        return_date=model.return_date,
        account=account,
        refund_amount=refund_amount,
        notes=model.notes,
        id=model.id,
    )


def customer_return_item_to_domain(
    model: CustomerReturnItemModel,
) -> CustomerReturnItem:
    return CustomerReturnItem(
        customer_return=customer_return_to_domain(model.customer_return),
        sale_item=sale_item_to_domain(model.sale_item),
        quantity=model.quantity,
        condition=ReturnCondition(model.condition),
        id=model.id,
    )


def return_lot_allocation_to_domain(
    model: ReturnLotAllocationModel,
) -> ReturnLotAllocation:
    allocation = sale_item_lot_allocation_to_domain(
        model.sale_item_lot_allocation
    )
    return ReturnLotAllocation(
        customer_return_item=customer_return_item_to_domain(
            model.customer_return_item
        ),
        sale_item_lot_allocation=allocation,
        quantity=model.quantity,
        unit_cost_snapshot=Money(
            model.unit_cost_snapshot,
            allocation.unit_cost_snapshot.currency,
        ),
        id=model.id,
    )


def supplier_return_to_domain(model: SupplierReturnModel) -> SupplierReturn:
    purchase = purchase_to_domain(model.purchase)
    account = (
        account_to_domain(model.account)
        if model.account is not None
        else None
    )
    refund_amount = None
    if model.refund_amount is not None:
        if model.refund_currency is None:
            raise ValueError(
                "A supplier return with a refund has no refund currency."
            )
        refund_amount = Money(
            model.refund_amount,
            currency_to_domain(model.refund_currency),
        )

    return SupplierReturn(
        purchase=purchase,
        return_date=model.return_date,
        supplier_id=model.supplier_id,
        account=account,
        refund_amount=refund_amount,
        notes=model.notes,
        id=model.id,
    )


def supplier_return_item_to_domain(
    model: SupplierReturnItemModel,
) -> SupplierReturnItem:
    lot = inventory_lot_to_domain(model.inventory_lot)
    return SupplierReturnItem(
        supplier_return=supplier_return_to_domain(model.supplier_return),
        purchase_item=purchase_item_to_domain(model.purchase_item),
        inventory_lot=lot,
        quantity=model.quantity,
        unit_cost_snapshot=Money(
            model.unit_cost_snapshot, lot.unit_cost.currency
        ),
        id=model.id,
    )


def financial_transaction_to_domain(
    model: FinancialTransactionModel,
) -> FinancialTransaction:
    return FinancialTransaction(
        account=account_to_domain(model.account),
        amount=Money(model.amount, currency_to_domain(model.currency)),
        transaction_type=FinancialTransactionType(model.transaction_type),
        transaction_date=model.transaction_date,
        description=model.description,
        purchase_id=model.purchase_id,
        sale_id=model.sale_id,
        expense_id=model.expense_id,
        customer_return_id=model.customer_return_id,
        supplier_return_id=model.supplier_return_id,
        capital_movement_id=model.capital_movement_id,
        account_transfer_id=model.account_transfer_id,
        exchange_rate_id=model.exchange_rate_id,
        id=model.id,
    )


def expense_to_domain(model: ExpenseModel) -> Expense:
    return Expense(
        account=account_to_domain(model.account),
        expense_type=ExpenseType(model.expense_type),
        amount=Money(model.amount, currency_to_domain(model.currency)),
        expense_date=model.expense_date,
        description=model.description,
        notes=model.notes,
        id=model.id,
    )


def capital_movement_to_domain(
    model: CapitalMovementModel,
) -> CapitalMovement:
    return CapitalMovement(
        account=account_to_domain(model.account),
        movement_type=CapitalMovementType(model.movement_type),
        amount=Money(model.amount, currency_to_domain(model.currency)),
        movement_date=model.movement_date,
        notes=model.notes,
        id=model.id,
    )


def account_transfer_to_domain(
    model: AccountTransferModel,
) -> AccountTransfer:
    source_account = account_to_domain(model.source_account)
    destination_account = account_to_domain(model.destination_account)
    exchange_rate = (
        exchange_rate_to_domain(model.exchange_rate)
        if model.exchange_rate is not None
        else None
    )

    return AccountTransfer(
        source_account=source_account,
        destination_account=destination_account,
        source_amount=Money(model.source_amount, source_account.currency),
        destination_amount=Money(
            model.destination_amount, destination_account.currency
        ),
        transfer_date=model.transfer_date,
        exchange_rate=exchange_rate,
        notes=model.notes,
        id=model.id,
    )


def category_to_domain(model: CategoryModel) -> Category:
    return Category(
        name=model.name,
        description=model.description,
        id=model.id,
    )


def product_to_domain(model: ProductModel) -> Product:
    default_selling_price = None
    if model.default_selling_price is not None:
        if model.selling_currency is None:
            raise ValueError(
                "Product has a default selling price but no selling currency."
            )
        default_selling_price = Money(
            model.default_selling_price,
            currency_to_domain(model.selling_currency),
        )

    return Product(
        name=model.name,
        category_id=model.category_id,
        description=model.description,
        brand=model.brand,
        default_selling_price=default_selling_price,
        is_active=model.is_active,
        id=model.id,
    )


def product_variant_to_domain(model: ProductVariantModel) -> ProductVariant:
    return ProductVariant(
        product_id=model.product_id,
        sku=model.sku,
        variant_name=model.variant_name,
        barcode=model.barcode,
        is_active=model.is_active,
        id=model.id,
    )


def attribute_to_domain(model: AttributeModel) -> Attribute:
    return Attribute(name=model.name, id=model.id)


def attribute_value_to_domain(model: AttributeValueModel) -> AttributeValue:
    return AttributeValue(
        attribute_id=model.attribute_id,
        value=model.value,
        id=model.id,
    )
