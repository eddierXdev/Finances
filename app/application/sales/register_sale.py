"""Register a fully collected FIFO sale atomically."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from app.domain.entities.currency import Currency
from app.domain.entities.financial_transaction import FinancialTransaction
from app.domain.entities.inventory_lot import InventoryLot
from app.domain.entities.inventory_movement import InventoryMovement
from app.domain.entities.sale import Sale
from app.domain.entities.sale_item import SaleItem
from app.domain.entities.sale_item_lot_allocation import (
    SaleItemLotAllocation,
)
from app.domain.enums.financial_transaction_type import (
    FinancialTransactionType,
)
from app.domain.enums.inventory_movement_type import InventoryMovementType
from app.domain.exceptions import (
    AccountCurrencyMismatchError,
    AccountNotFoundError,
    CustomerNotFoundError,
    InactiveAccountError,
    InvalidSaleError,
    VariantNotFoundError,
)
from app.domain.fifo import FifoTake, allocate_fifo
from app.domain.repositories.account_repository import AccountRepository
from app.domain.repositories.customer_repository import CustomerRepository
from app.domain.repositories.financial_transaction_repository import (
    FinancialTransactionRepository,
)
from app.domain.repositories.inventory_lot_repository import (
    InventoryLotRepository,
)
from app.domain.repositories.inventory_movement_repository import (
    InventoryMovementRepository,
)
from app.domain.repositories.product_variant_repository import (
    ProductVariantRepository,
)
from app.domain.repositories.sale_item_lot_allocation_repository import (
    SaleItemLotAllocationRepository,
)
from app.domain.repositories.sale_item_repository import SaleItemRepository
from app.domain.repositories.sale_repository import SaleRepository
from app.domain.sales_costing import (
    sale_cogs_by_currency,
    sale_revenue,
)
from app.domain.value_objects.money import Money

_SALE_REFERENCE = "SALE"


@dataclass(frozen=True, slots=True)
class SaleItemRequest:
    """One variant and quantity to sell at a unit price."""

    variant_id: int
    quantity: int
    unit_price: Money
    discount_amount: Money | None = None


@dataclass(frozen=True, slots=True)
class RegisterSaleRequest:
    """Input for a completed sale collected into one account."""

    account_id: int
    currency: Currency
    sale_date: datetime
    items: tuple[SaleItemRequest, ...]
    customer_id: int | None = None
    discount_amount: Money | None = None
    notes: str | None = None


@dataclass(frozen=True, slots=True)
class RegisteredSale:
    """The sale rows, stock changes and financial result."""

    sale: Sale
    items: tuple[SaleItem, ...]
    allocations: tuple[SaleItemLotAllocation, ...]
    movements: tuple[InventoryMovement, ...]
    revenue: Money
    cogs: Money | None
    gross_profit: Money | None
    cogs_by_currency: tuple[Money, ...]


class RegisterSale:
    """Create a sale, consume FIFO lots and record its cash inflow.

    FIFO availability, item totals and the sale discount are validated
    before the first write. The caller must still run this use case inside a
    database transaction so a persistence failure rolls back the sale.
    """

    def __init__(
        self,
        accounts: AccountRepository,
        customers: CustomerRepository,
        variants: ProductVariantRepository,
        sales: SaleRepository,
        items: SaleItemRepository,
        allocations: SaleItemLotAllocationRepository,
        lots: InventoryLotRepository,
        movements: InventoryMovementRepository,
        transactions: FinancialTransactionRepository,
    ) -> None:
        self._accounts = accounts
        self._customers = customers
        self._variants = variants
        self._sales = sales
        self._items = items
        self._allocations = allocations
        self._lots = lots
        self._movements = movements
        self._transactions = transactions

    def execute(self, request: RegisterSaleRequest) -> RegisteredSale:
        if not request.items:
            raise InvalidSaleError(
                "A sale requires at least one item."
            )
        if not isinstance(request.currency, Currency):
            raise TypeError(
                "Sale currency must be a Currency instance."
            )

        account = self._accounts.get_by_id(request.account_id)
        if account is None:
            raise AccountNotFoundError(
                f"Account {request.account_id} does not exist."
            )
        if not account.is_active:
            raise InactiveAccountError(
                f"Account {account.id} is inactive."
            )
        if account.currency.code != request.currency.code:
            raise AccountCurrencyMismatchError(
                f"Account currency {account.currency.code} does not match "
                f"sale currency {request.currency.code}."
            )

        sale = Sale(
            account=account,
            currency=request.currency,
            sale_date=request.sale_date,
            customer_id=request.customer_id,
            discount_amount=request.discount_amount,
            notes=request.notes,
        )

        if (
            sale.customer_id is not None
            and not self._customers.exists(sale.customer_id)
        ):
            raise CustomerNotFoundError(
                f"Customer {sale.customer_id} does not exist."
            )

        planned_items = tuple(
            SaleItem(
                sale=sale,
                variant_id=item.variant_id,
                quantity=item.quantity,
                unit_price=item.unit_price,
                discount_amount=item.discount_amount,
            )
            for item in request.items
        )
        for variant_id in {item.variant_id for item in planned_items}:
            if self._variants.get_by_id(variant_id) is None:
                raise VariantNotFoundError(
                    f"Product variant {variant_id} does not exist."
                )

        revenue = sale_revenue(sale, planned_items)
        if not revenue.is_positive:
            raise InvalidSaleError("Sale total must be positive.")

        working_lots: dict[int, list[InventoryLot]] = {}
        consumed_lots: dict[int, InventoryLot] = {}
        planned_takes: list[tuple[int, FifoTake]] = []

        for index, item in enumerate(planned_items):
            lots = working_lots.get(item.variant_id)
            if lots is None:
                lots = self._lots.list_available_by_variant(
                    item.variant_id
                )
                working_lots[item.variant_id] = lots

            takes = allocate_fifo(lots, item.quantity)
            for take in takes:
                if take.lot.id is None:
                    raise RuntimeError(
                        "A FIFO take requires a persisted lot."
                    )
                planned_takes.append((index, take))
                consumed = take.lot.consume(take.quantity)
                lots = [
                    consumed if lot.id == take.lot.id else lot
                    for lot in lots
                ]
                consumed_lots[take.lot.id] = consumed
            working_lots[item.variant_id] = lots

        persisted_sale = self._sales.add(sale)
        if persisted_sale.id is None:
            raise RuntimeError("Persisted sale has no identifier.")

        persisted_items = tuple(
            self._items.add(replace(item, sale=persisted_sale))
            for item in planned_items
        )

        for lot in consumed_lots.values():
            self._lots.save(lot)

        created_allocations: list[SaleItemLotAllocation] = []
        for item_index, take in planned_takes:
            created_allocations.append(
                self._allocations.add(
                    SaleItemLotAllocation(
                        sale_item=persisted_items[item_index],
                        inventory_lot=take.lot,
                        quantity=take.quantity,
                        unit_cost_snapshot=take.lot.unit_cost,
                    )
                )
            )

        created_movements: list[InventoryMovement] = []
        for _, take in planned_takes:
            created_movements.append(
                self._movements.add(
                    InventoryMovement(
                        variant_id=take.lot.variant_id,
                        movement_type=InventoryMovementType.SALE,
                        quantity=-take.quantity,
                        movement_date=persisted_sale.sale_date,
                        inventory_lot_id=take.lot.id,
                        unit_cost=take.lot.unit_cost,
                        reference_type=_SALE_REFERENCE,
                        reference_id=persisted_sale.id,
                        notes=persisted_sale.notes,
                    )
                )
            )

        self._transactions.add(
            FinancialTransaction(
                account=persisted_sale.account,
                amount=revenue,
                transaction_type=FinancialTransactionType.SALE,
                transaction_date=persisted_sale.sale_date,
                description=f"Sale {persisted_sale.id}",
                sale_id=persisted_sale.id,
            )
        )

        allocations = tuple(created_allocations)
        cogs_by_currency = sale_cogs_by_currency(allocations)
        cogs = (
            cogs_by_currency[0]
            if len(cogs_by_currency) == 1
            else None
        )
        gross_profit = None
        if (
            cogs is not None
            and cogs.currency.code == revenue.currency.code
        ):
            gross_profit = revenue - cogs

        return RegisteredSale(
            sale=persisted_sale,
            items=persisted_items,
            allocations=allocations,
            movements=tuple(created_movements),
            revenue=revenue,
            cogs=cogs,
            gross_profit=gross_profit,
            cogs_by_currency=cogs_by_currency,
        )
