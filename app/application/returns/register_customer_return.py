"""Register a customer return atomically."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from app.application.accounts import require_active_account
from app.domain.entities.account import Account
from app.domain.entities.customer_return import CustomerReturn
from app.domain.entities.customer_return_item import CustomerReturnItem
from app.domain.entities.financial_transaction import FinancialTransaction
from app.domain.entities.inventory_lot import InventoryLot
from app.domain.entities.inventory_movement import InventoryMovement
from app.domain.entities.return_lot_allocation import ReturnLotAllocation
from app.domain.entities.sale import Sale
from app.domain.entities.sale_item import SaleItem
from app.domain.entities.sale_item_lot_allocation import (
    SaleItemLotAllocation,
)
from app.domain.enums.financial_transaction_type import (
    FinancialTransactionType,
)
from app.domain.enums.inventory_movement_type import InventoryMovementType
from app.domain.enums.return_condition import ReturnCondition
from app.domain.enums.sale_status import SaleStatus
from app.domain.exceptions import (
    AccountCurrencyMismatchError,
    CustomerRefundError,
    ExcessReturnError,
    InvalidCustomerReturnError,
    SaleCurrencyMismatchError,
    SaleItemNotFoundError,
    SaleNotFoundError,
)
from app.domain.repositories.account_repository import AccountRepository
from app.domain.repositories.customer_return_item_repository import (
    CustomerReturnItemRepository,
)
from app.domain.repositories.customer_return_repository import (
    CustomerReturnRepository,
)
from app.domain.repositories.financial_transaction_repository import (
    FinancialTransactionRepository,
)
from app.domain.repositories.inventory_lot_repository import (
    InventoryLotRepository,
)
from app.domain.repositories.inventory_movement_repository import (
    InventoryMovementRepository,
)
from app.domain.repositories.return_lot_allocation_repository import (
    ReturnLotAllocationRepository,
)
from app.domain.repositories.sale_item_lot_allocation_repository import (
    SaleItemLotAllocationRepository,
)
from app.domain.repositories.sale_item_repository import SaleItemRepository
from app.domain.repositories.sale_repository import SaleRepository
from app.domain.returns import (
    PlannedReturnAllocation,
    ReturnLine,
    plan_return_allocations,
)
from app.domain.sales_costing import sale_revenue
from app.domain.value_objects.money import Money

_RETURN_REFERENCE = "CUSTOMER_RETURN"


@dataclass(frozen=True, slots=True)
class CustomerReturnItemRequest:
    """One original sale item and the quantity being returned."""

    sale_item_id: int
    quantity: int
    condition: ReturnCondition


@dataclass(frozen=True, slots=True)
class RegisterCustomerReturnRequest:
    """Input for a return against an original sale."""

    sale_id: int
    return_date: datetime
    items: tuple[CustomerReturnItemRequest, ...]
    account_id: int | None = None
    refund_amount: Money | None = None
    notes: str | None = None


@dataclass(frozen=True, slots=True)
class RegisteredCustomerReturn:
    """The return rows, stock changes and financial result."""

    customer_return: CustomerReturn
    items: tuple[CustomerReturnItem, ...]
    allocations: tuple[ReturnLotAllocation, ...]
    movements: tuple[InventoryMovement, ...]
    refund: FinancialTransaction | None
    sale: Sale
    total_refunded: Money


class RegisterCustomerReturn:
    """Create a customer return and reverse its historical sale allocations.

    Every validation and reversal plan is computed before the first write.
    The caller must run this use case inside a database transaction so a
    persistence failure rolls back the whole return.
    """

    def __init__(
        self,
        accounts: AccountRepository,
        sales: SaleRepository,
        sale_items: SaleItemRepository,
        sale_allocations: SaleItemLotAllocationRepository,
        customer_returns: CustomerReturnRepository,
        return_items: CustomerReturnItemRepository,
        return_allocations: ReturnLotAllocationRepository,
        lots: InventoryLotRepository,
        movements: InventoryMovementRepository,
        transactions: FinancialTransactionRepository,
    ) -> None:
        self._accounts = accounts
        self._sales = sales
        self._sale_items = sale_items
        self._sale_allocations = sale_allocations
        self._customer_returns = customer_returns
        self._return_items = return_items
        self._return_allocations = return_allocations
        self._lots = lots
        self._movements = movements
        self._transactions = transactions

    def execute(
        self, request: RegisterCustomerReturnRequest
    ) -> RegisteredCustomerReturn:
        if not request.items:
            raise InvalidCustomerReturnError(
                "A customer return requires at least one item."
            )

        sale = self._sales.get_by_id(request.sale_id)
        if sale is None:
            raise SaleNotFoundError(
                f"Sale {request.sale_id} does not exist."
            )
        if sale.id is None:
            raise RuntimeError("A persisted sale has no identifier.")
        if sale.status in (SaleStatus.CANCELLED, SaleStatus.REFUNDED):
            raise InvalidCustomerReturnError(
                f"Sale {sale.id} cannot receive more returns in status "
                f"{sale.status.value}."
            )

        sale_items = self._sale_items.list_for_sale(sale.id)
        if not sale_items:
            raise InvalidCustomerReturnError(
                "The original sale has no items to return."
            )
        sale_items_by_id = {
            item.id: item for item in sale_items if item.id is not None
        }

        self._validate_request_lines(request, sale_items_by_id)

        previous_returns = self._customer_returns.list_for_sale(sale.id)
        previous_items = self._return_items.list_for_sale(sale.id)
        previous_allocations = self._return_allocations.list_for_sale(
            sale.id
        )

        self._validate_returned_quantities(
            request, sale_items_by_id, previous_items
        )

        original_sale = sale
        account, total_refunded = self._validate_refund(
            request, sale, sale_items, previous_returns
        )
        sale = self._next_sale_status(
            request, sale, sale_items, total_refunded
        )

        customer_return = CustomerReturn(
            sale=sale,
            return_date=request.return_date,
            account=account,
            refund_amount=request.refund_amount,
            notes=request.notes,
        )
        planned_items = tuple(
            CustomerReturnItem(
                customer_return=customer_return,
                sale_item=sale_items_by_id[line.sale_item_id],
                quantity=line.quantity,
                condition=line.condition,
            )
            for line in request.items
        )

        planned_by_line = self._plan_reversals(
            request,
            sale_items_by_id,
            previous_allocations,
        )

        if sale.status is not original_sale.status:
            sale = self._sales.save(sale)

        persisted_return = self._customer_returns.add(customer_return)
        if persisted_return.id is None:
            raise RuntimeError("Persisted customer return has no id.")

        persisted_items = tuple(
            self._return_items.add(
                replace(item, customer_return=persisted_return)
            )
            for item in planned_items
        )

        created_allocations = self._persist_return_allocations(
            planned_by_line, persisted_items
        )
        restored_lots, created_movements = self._restore_sellable_stock(
            planned_by_line, persisted_return
        )

        for lot in restored_lots:
            self._lots.save(lot)
        for movement in created_movements:
            self._movements.add(movement)

        refund = None
        if persisted_return.refund_amount is not None:
            if persisted_return.account is None:
                raise RuntimeError(
                    "A persisted refund has no refund account."
                )
            refund = self._transactions.add(
                FinancialTransaction(
                    account=persisted_return.account,
                    amount=-persisted_return.refund_amount,
                    transaction_type=(
                        FinancialTransactionType.CUSTOMER_REFUND
                    ),
                    transaction_date=persisted_return.return_date,
                    description=(
                        f"Customer return {persisted_return.id}"
                    ),
                    customer_return_id=persisted_return.id,
                )
            )

        return RegisteredCustomerReturn(
            customer_return=persisted_return,
            items=persisted_items,
            allocations=tuple(created_allocations),
            movements=tuple(created_movements),
            refund=refund,
            sale=sale,
            total_refunded=total_refunded,
        )

    def _validate_request_lines(
        self,
        request: RegisterCustomerReturnRequest,
        sale_items_by_id: dict[int, SaleItem],
    ) -> None:
        for line in request.items:
            if not isinstance(line, CustomerReturnItemRequest):
                raise TypeError(
                    "Return items must be CustomerReturnItemRequest "
                    "instances."
                )
            if (
                isinstance(line.sale_item_id, bool)
                or not isinstance(line.sale_item_id, int)
                or line.sale_item_id <= 0
            ):
                raise InvalidCustomerReturnError(
                    "Return sale_item_id must be a positive integer."
                )
            if (
                isinstance(line.quantity, bool)
                or not isinstance(line.quantity, int)
                or line.quantity <= 0
            ):
                raise InvalidCustomerReturnError(
                    "Return quantities must be positive integers."
                )
            if not isinstance(line.condition, ReturnCondition):
                raise TypeError(
                    "Return conditions must be ReturnCondition instances."
                )

            if line.sale_item_id not in sale_items_by_id:
                if self._sale_items.get_by_id(line.sale_item_id) is None:
                    raise SaleItemNotFoundError(
                        f"Sale item {line.sale_item_id} does not exist."
                    )
                raise InvalidCustomerReturnError(
                    "A returned item must belong to the original sale."
                )

    def _validate_returned_quantities(
        self,
        request: RegisterCustomerReturnRequest,
        sale_items_by_id: dict[int, SaleItem],
        previous_items: list[CustomerReturnItem],
    ) -> None:
        previous_by_item: dict[int, int] = {}
        for item in previous_items:
            if item.sale_item_id is None:
                raise RuntimeError(
                    "A persisted return item has no sale item id."
                )
            previous_by_item[item.sale_item_id] = (
                previous_by_item.get(item.sale_item_id, 0)
                + item.quantity
            )

        requested_by_item: dict[int, int] = {}
        for line in request.items:
            requested_by_item[line.sale_item_id] = (
                requested_by_item.get(line.sale_item_id, 0)
                + line.quantity
            )

        for item_id, requested in requested_by_item.items():
            sale_item = sale_items_by_id[item_id]
            already_returned = previous_by_item.get(item_id, 0)
            if already_returned + requested > sale_item.quantity:
                raise ExcessReturnError(
                    f"Cannot return {already_returned + requested} units of "
                    f"sale item {item_id}; only {sale_item.quantity} were "
                    "sold."
                )

    def _validate_refund(
        self,
        request: RegisterCustomerReturnRequest,
        sale: Sale,
        sale_items: list[SaleItem],
        previous_returns: list[CustomerReturn],
    ) -> tuple[Account | None, Money]:
        total_refunded = Money.zero(sale.currency)
        for previous in previous_returns:
            if previous.refund_amount is not None:
                total_refunded = total_refunded + previous.refund_amount

        if request.refund_amount is None:
            if request.account_id is not None:
                raise InvalidCustomerReturnError(
                    "A refund account requires a refund amount."
                )
            return None, total_refunded

        if not isinstance(request.refund_amount, Money):
            raise TypeError("Refund amount must be Money or None.")
        if not request.refund_amount.is_positive:
            raise CustomerRefundError(
                "Customer refund amount must be positive."
            )
        if request.refund_amount.currency.code != sale.currency.code:
            raise SaleCurrencyMismatchError(
                f"Refund currency "
                f"{request.refund_amount.currency.code} does not match "
                f"sale currency {sale.currency.code}."
            )
        if request.account_id is None:
            raise InvalidCustomerReturnError(
                "A customer refund requires an account."
            )
        if (
            isinstance(request.account_id, bool)
            or not isinstance(request.account_id, int)
            or request.account_id <= 0
        ):
            raise InvalidCustomerReturnError(
                "Refund account_id must be a positive integer."
            )

        account = require_active_account(
            self._accounts,
            request.account_id,
            label="Refund account",
        )
        if account.currency.code != sale.currency.code:
            raise AccountCurrencyMismatchError(
                f"Account currency {account.currency.code} does not match "
                f"refund currency {sale.currency.code}."
            )

        total_refunded = total_refunded + request.refund_amount
        revenue = sale_revenue(sale, sale_items)
        if total_refunded > revenue:
            raise CustomerRefundError(
                f"Cumulative refunds {total_refunded} cannot exceed sale "
                f"revenue {revenue}."
            )

        return account, total_refunded

    def _next_sale_status(
        self,
        request: RegisterCustomerReturnRequest,
        sale: Sale,
        sale_items: list[SaleItem],
        total_refunded: Money,
    ) -> Sale:
        if request.refund_amount is None:
            return sale

        revenue = sale_revenue(sale, sale_items)
        target = (
            SaleStatus.REFUNDED
            if total_refunded >= revenue
            else SaleStatus.PARTIALLY_REFUNDED
        )
        if target is sale.status:
            return sale
        return sale.transition_to(target)

    def _plan_reversals(
        self,
        request: RegisterCustomerReturnRequest,
        sale_items_by_id: dict[int, SaleItem],
        previous_allocations: list[ReturnLotAllocation],
    ) -> list[list[PlannedReturnAllocation]]:
        allocations_by_item: dict[
            int, list[SaleItemLotAllocation]
        ] = {}
        for allocation in self._sale_allocations.list_for_sale(
            request.sale_id
        ):
            if allocation.sale_item.id is None:
                raise RuntimeError(
                    "A persisted sale allocation has no sale item id."
                )
            allocations_by_item.setdefault(
                allocation.sale_item.id, []
            ).append(allocation)

        reversed_by_allocation: dict[int, int] = {}
        for allocation in previous_allocations:
            original_id = allocation.sale_item_lot_allocation_id
            if original_id is None:
                raise RuntimeError(
                    "A persisted return allocation has no original id."
                )
            reversed_by_allocation[original_id] = (
                reversed_by_allocation.get(original_id, 0)
                + allocation.quantity
            )

        planned_by_line: list[list[PlannedReturnAllocation]] = [
            [] for _ in request.items
        ]
        working_reversed = dict(reversed_by_allocation)
        for index, line in enumerate(request.items):
            original_allocations = allocations_by_item.get(
                line.sale_item_id
            )
            if not original_allocations:
                raise InvalidCustomerReturnError(
                    "The original sale has no FIFO allocations for this "
                    "item."
                )
            planned = plan_return_allocations(
                sale_items_by_id[line.sale_item_id],
                original_allocations,
                working_reversed,
                (ReturnLine(line.quantity, line.condition),),
            )
            planned_by_line[index].extend(planned)
            for entry in planned:
                allocation_id = entry.allocation.id
                if allocation_id is None:
                    raise RuntimeError(
                        "A planned allocation has no original id."
                    )
                working_reversed[allocation_id] = (
                    working_reversed.get(allocation_id, 0)
                    + entry.quantity
                )

        return planned_by_line

    def _persist_return_allocations(
        self,
        planned_by_line: list[list[PlannedReturnAllocation]],
        persisted_items: tuple[CustomerReturnItem, ...],
    ) -> list[ReturnLotAllocation]:
        created: list[ReturnLotAllocation] = []
        for index, entries in enumerate(planned_by_line):
            for entry in entries:
                created.append(
                    self._return_allocations.add(
                        ReturnLotAllocation(
                            customer_return_item=persisted_items[index],
                            sale_item_lot_allocation=entry.allocation,
                            quantity=entry.quantity,
                            unit_cost_snapshot=(
                                entry.allocation.unit_cost_snapshot
                            ),
                        )
                    )
                )
        return created

    def _restore_sellable_stock(
        self,
        planned_by_line: list[list[PlannedReturnAllocation]],
        persisted_return: CustomerReturn,
    ) -> tuple[list[InventoryLot], list[InventoryMovement]]:
        restored_lots: dict[int, InventoryLot] = {}
        movements: list[InventoryMovement] = []

        for entries in planned_by_line:
            for entry in entries:
                if entry.condition is not ReturnCondition.SELLABLE:
                    continue

                lot = entry.allocation.inventory_lot
                if lot.id is None:
                    raise RuntimeError(
                        "A sellable return requires a persisted lot."
                    )
                current = restored_lots.get(lot.id, lot)
                restored_lots[lot.id] = current.restore(entry.quantity)
                movements.append(
                    InventoryMovement(
                        variant_id=lot.variant_id,
                        movement_type=(
                            InventoryMovementType.CUSTOMER_RETURN
                        ),
                        quantity=entry.quantity,
                        movement_date=persisted_return.return_date,
                        inventory_lot_id=lot.id,
                        unit_cost=entry.allocation.unit_cost_snapshot,
                        reference_type=_RETURN_REFERENCE,
                        reference_id=persisted_return.id,
                        notes=persisted_return.notes,
                    )
                )

        return list(restored_lots.values()), movements
