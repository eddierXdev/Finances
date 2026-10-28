"""Register a supplier return atomically."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from app.application.accounts import require_active_account
from app.domain.entities.account import Account
from app.domain.entities.financial_transaction import FinancialTransaction
from app.domain.entities.inventory_lot import InventoryLot
from app.domain.entities.inventory_movement import InventoryMovement
from app.domain.entities.purchase import Purchase
from app.domain.entities.purchase_item import PurchaseItem
from app.domain.entities.supplier_return import SupplierReturn
from app.domain.entities.supplier_return_item import SupplierReturnItem
from app.domain.enums.financial_transaction_type import (
    FinancialTransactionType,
)
from app.domain.enums.inventory_movement_type import InventoryMovementType
from app.domain.exceptions import (
    AccountCurrencyMismatchError,
    ExcessSupplierReturnError,
    InvalidSupplierReturnError,
    InvalidSupplierReturnLotError,
    InventoryLotNotFoundError,
    PurchaseCurrencyMismatchError,
    PurchaseItemNotFoundError,
    PurchaseNotFoundError,
    SupplierRefundError,
)
from app.domain.repositories.account_repository import AccountRepository
from app.domain.repositories.financial_transaction_repository import (
    FinancialTransactionRepository,
)
from app.domain.repositories.inventory_lot_repository import (
    InventoryLotRepository,
)
from app.domain.repositories.inventory_movement_repository import (
    InventoryMovementRepository,
)
from app.domain.repositories.purchase_item_repository import (
    PurchaseItemRepository,
)
from app.domain.repositories.purchase_repository import PurchaseRepository
from app.domain.repositories.supplier_return_item_repository import (
    SupplierReturnItemRepository,
)
from app.domain.repositories.supplier_return_repository import (
    SupplierReturnRepository,
)
from app.domain.value_objects.money import Money

_RETURN_REFERENCE = "SUPPLIER_RETURN"


@dataclass(frozen=True, slots=True)
class SupplierReturnItemRequest:
    """One purchase item and the exact lot quantity being returned."""

    purchase_item_id: int
    inventory_lot_id: int
    quantity: int


@dataclass(frozen=True, slots=True)
class RegisterSupplierReturnRequest:
    """Input for a return against an original purchase."""

    purchase_id: int
    return_date: datetime
    items: tuple[SupplierReturnItemRequest, ...]
    account_id: int | None = None
    refund_amount: Money | None = None
    notes: str | None = None


@dataclass(frozen=True, slots=True)
class RegisteredSupplierReturn:
    """The return rows, stock changes and financial result."""

    supplier_return: SupplierReturn
    items: tuple[SupplierReturnItem, ...]
    movements: tuple[InventoryMovement, ...]
    refund: FinancialTransaction | None
    purchase: Purchase
    total_refunded: Money


class RegisterSupplierReturn:
    """Create a supplier return and remove stock from exact inventory lots.

    Every validation and stock change is computed before the first write.
    The caller must run this use case inside a database transaction so a
    persistence failure rolls back the whole return.
    """

    def __init__(
        self,
        accounts: AccountRepository,
        purchases: PurchaseRepository,
        purchase_items: PurchaseItemRepository,
        lots: InventoryLotRepository,
        supplier_returns: SupplierReturnRepository,
        return_items: SupplierReturnItemRepository,
        movements: InventoryMovementRepository,
        transactions: FinancialTransactionRepository,
    ) -> None:
        self._accounts = accounts
        self._purchases = purchases
        self._purchase_items = purchase_items
        self._lots = lots
        self._supplier_returns = supplier_returns
        self._return_items = return_items
        self._movements = movements
        self._transactions = transactions

    def execute(
        self, request: RegisterSupplierReturnRequest
    ) -> RegisteredSupplierReturn:
        if not request.items:
            raise InvalidSupplierReturnError(
                "A supplier return requires at least one item."
            )
        if (
            isinstance(request.purchase_id, bool)
            or not isinstance(request.purchase_id, int)
            or request.purchase_id <= 0
        ):
            raise InvalidSupplierReturnError(
                "Purchase id must be a positive integer."
            )

        purchase = self._purchases.get_by_id(request.purchase_id)
        if purchase is None:
            raise PurchaseNotFoundError(
                f"Purchase {request.purchase_id} does not exist."
            )
        if purchase.id is None:
            raise RuntimeError("A persisted purchase has no identifier.")

        purchase_items = self._purchase_items.list_for_purchase(
            purchase.id
        )
        if not purchase_items:
            raise InvalidSupplierReturnError(
                "The original purchase has no items to return."
            )
        purchase_items_by_id = {
            item.id: item
            for item in purchase_items
            if item.id is not None
        }

        lots_by_id = self._validate_request_lines(
            request, purchase_items_by_id
        )

        previous_returns = self._supplier_returns.list_for_purchase(
            purchase.id
        )
        account, total_refunded = self._validate_refund(
            request, purchase, previous_returns
        )

        supplier_return = SupplierReturn(
            purchase=purchase,
            return_date=request.return_date,
            supplier_id=purchase.supplier_id,
            account=account,
            refund_amount=request.refund_amount,
            notes=request.notes,
        )
        planned_items = tuple(
            SupplierReturnItem(
                supplier_return=supplier_return,
                purchase_item=purchase_items_by_id[
                    line.purchase_item_id
                ],
                inventory_lot=lots_by_id[line.inventory_lot_id],
                quantity=line.quantity,
                unit_cost_snapshot=lots_by_id[
                    line.inventory_lot_id
                ].unit_cost,
            )
            for line in request.items
        )

        persisted_return = self._supplier_returns.add(supplier_return)
        if persisted_return.id is None:
            raise RuntimeError("Persisted supplier return has no id.")

        persisted_items = tuple(
            self._return_items.add(
                replace(item, supplier_return=persisted_return)
            )
            for item in planned_items
        )

        updated_lots, created_movements = self._remove_sellable_stock(
            persisted_items, persisted_return
        )

        for lot in updated_lots:
            self._lots.save(lot)
        for movement in created_movements:
            self._movements.add(movement)

        refund = None
        if persisted_return.refund_amount is not None:
            if persisted_return.account is None:
                raise RuntimeError(
                    "A persisted supplier refund has no refund account."
                )
            refund = self._transactions.add(
                FinancialTransaction(
                    account=persisted_return.account,
                    amount=persisted_return.refund_amount,
                    transaction_type=(
                        FinancialTransactionType.SUPPLIER_REFUND
                    ),
                    transaction_date=persisted_return.return_date,
                    description=(
                        f"Supplier return {persisted_return.id}"
                    ),
                    supplier_return_id=persisted_return.id,
                )
            )

        return RegisteredSupplierReturn(
            supplier_return=persisted_return,
            items=persisted_items,
            movements=tuple(created_movements),
            refund=refund,
            purchase=purchase,
            total_refunded=total_refunded,
        )

    def _validate_request_lines(
        self,
        request: RegisterSupplierReturnRequest,
        purchase_items_by_id: dict[int, PurchaseItem],
    ) -> dict[int, InventoryLot]:
        lots_by_id: dict[int, InventoryLot] = {}
        requested_by_lot: dict[int, int] = {}

        for line in request.items:
            if not isinstance(line, SupplierReturnItemRequest):
                raise TypeError(
                    "Supplier return items must be "
                    "SupplierReturnItemRequest instances."
                )
            if (
                isinstance(line.purchase_item_id, bool)
                or not isinstance(line.purchase_item_id, int)
                or line.purchase_item_id <= 0
            ):
                raise InvalidSupplierReturnError(
                    "Return purchase_item_id must be a positive integer."
                )
            if (
                isinstance(line.inventory_lot_id, bool)
                or not isinstance(line.inventory_lot_id, int)
                or line.inventory_lot_id <= 0
            ):
                raise InvalidSupplierReturnError(
                    "Return inventory_lot_id must be a positive integer."
                )
            if (
                isinstance(line.quantity, bool)
                or not isinstance(line.quantity, int)
                or line.quantity <= 0
            ):
                raise InvalidSupplierReturnError(
                    "Return quantities must be positive integers."
                )

            purchase_item = purchase_items_by_id.get(
                line.purchase_item_id
            )
            if purchase_item is None:
                if (
                    self._purchase_items.get_by_id(
                        line.purchase_item_id
                    )
                    is None
                ):
                    raise PurchaseItemNotFoundError(
                        f"Purchase item {line.purchase_item_id} does not "
                        "exist."
                    )
                raise InvalidSupplierReturnError(
                    "A returned item must belong to the original purchase."
                )

            lot = self._lots.get_by_id(line.inventory_lot_id)
            if lot is None:
                raise InventoryLotNotFoundError(
                    f"Inventory lot {line.inventory_lot_id} does not exist."
                )
            if lot.id is None:
                raise RuntimeError("A persisted lot has no identifier.")

            if (
                lot.purchase_item_id != purchase_item.id
                or lot.variant_id != purchase_item.variant_id
            ):
                raise InvalidSupplierReturnLotError(
                    "A supplier return lot must belong to the original "
                    "purchase item."
                )

            lots_by_id[lot.id] = lot
            requested_by_lot[lot.id] = (
                requested_by_lot.get(lot.id, 0) + line.quantity
            )

        for lot_id, requested in requested_by_lot.items():
            lot = lots_by_id[lot_id]
            if requested > lot.remaining_quantity:
                raise ExcessSupplierReturnError(
                    f"Cannot return {requested} units from lot {lot_id}; "
                    f"only {lot.remaining_quantity} remain."
                )

        return lots_by_id

    def _validate_refund(
        self,
        request: RegisterSupplierReturnRequest,
        purchase: Purchase,
        previous_returns: list[SupplierReturn],
    ) -> tuple[Account | None, Money]:
        total_refunded = Money.zero(purchase.currency)
        for previous in previous_returns:
            if previous.refund_amount is not None:
                total_refunded = total_refunded + previous.refund_amount

        if request.refund_amount is None:
            if request.account_id is not None:
                raise InvalidSupplierReturnError(
                    "A refund account requires a refund amount."
                )
            return None, total_refunded

        if not isinstance(request.refund_amount, Money):
            raise TypeError("Refund amount must be Money or None.")
        if not request.refund_amount.is_positive:
            raise SupplierRefundError(
                "Supplier refund amount must be positive."
            )
        if request.refund_amount.currency.code != purchase.currency.code:
            raise PurchaseCurrencyMismatchError(
                f"Refund currency "
                f"{request.refund_amount.currency.code} does not match "
                f"purchase currency {purchase.currency.code}."
            )
        if request.account_id is None:
            raise InvalidSupplierReturnError(
                "A supplier refund requires an account."
            )
        if (
            isinstance(request.account_id, bool)
            or not isinstance(request.account_id, int)
            or request.account_id <= 0
        ):
            raise InvalidSupplierReturnError(
                "Refund account_id must be a positive integer."
            )

        account = require_active_account(
            self._accounts,
            request.account_id,
            label="Refund account",
        )
        if account.currency.code != purchase.currency.code:
            raise AccountCurrencyMismatchError(
                f"Account currency {account.currency.code} does not match "
                f"refund currency {purchase.currency.code}."
            )

        total_refunded = total_refunded + request.refund_amount
        return account, total_refunded

    def _remove_sellable_stock(
        self,
        persisted_items: tuple[SupplierReturnItem, ...],
        persisted_return: SupplierReturn,
    ) -> tuple[list[InventoryLot], list[InventoryMovement]]:
        updated_lots: dict[int, InventoryLot] = {}
        movements: list[InventoryMovement] = []

        for item in persisted_items:
            lot = item.inventory_lot
            if lot.id is None:
                raise RuntimeError(
                    "A supplier return requires a persisted lot."
                )
            current = updated_lots.get(lot.id, lot)
            updated_lots[lot.id] = current.consume(item.quantity)
            movements.append(
                InventoryMovement(
                    variant_id=lot.variant_id,
                    movement_type=InventoryMovementType.SUPPLIER_RETURN,
                    quantity=-item.quantity,
                    movement_date=persisted_return.return_date,
                    inventory_lot_id=lot.id,
                    unit_cost=item.unit_cost_snapshot,
                    reference_type=_RETURN_REFERENCE,
                    reference_id=persisted_return.id,
                    notes=persisted_return.notes,
                )
            )

        return list(updated_lots.values()), movements
