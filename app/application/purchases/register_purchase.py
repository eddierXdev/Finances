"""Register-purchase use case."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from app.application.accounts import require_active_account
from app.domain.entities.account import Account
from app.domain.entities.currency import Currency
from app.domain.entities.financial_transaction import FinancialTransaction
from app.domain.entities.purchase import Purchase
from app.domain.entities.purchase_cost import PurchaseCost
from app.domain.entities.purchase_cost_allocation import (
    PurchaseCostAllocation,
)
from app.domain.entities.purchase_item import PurchaseItem
from app.domain.enums.allocation_method import AllocationMethod
from app.domain.enums.financial_transaction_type import (
    FinancialTransactionType,
)
from app.domain.enums.purchase_cost_type import PurchaseCostType
from app.domain.enums.purchase_status import PurchaseStatus
from app.domain.exceptions import (
    AccountCurrencyMismatchError,
    ExchangeRateNotFoundError,
    InvalidCostAllocationError,
    InvalidPurchaseError,
    PurchasePaymentError,
)
from app.domain.purchase_costing import (
    allocate_purchase_cost,
    purchase_total,
)
from app.domain.repositories.account_repository import AccountRepository
from app.domain.repositories.exchange_rate_repository import (
    ExchangeRateRepository,
)
from app.domain.repositories.financial_transaction_repository import (
    FinancialTransactionRepository,
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
from app.domain.value_objects.money import Money


@dataclass(frozen=True, slots=True)
class PurchaseItemRequest:
    """One ordered variant in a purchase registration."""

    variant_id: int
    quantity: int
    unit_price: Money
    weight: Decimal | None = None


@dataclass(frozen=True, slots=True)
class PurchaseCostRequest:
    """One optional acquisition cost.

    ``manual_allocations`` maps zero-based item positions in the registration
    request to purchase-currency amounts. It is required only for ``MANUAL``.
    """

    cost_type: PurchaseCostType
    amount: Money
    allocation_method: AllocationMethod
    exchange_rate_id: int | None = None
    description: str | None = None
    manual_allocations: Mapping[int, Money] | None = None


@dataclass(frozen=True, slots=True)
class RegisterPurchaseRequest:
    """Input for registering a purchase and its optional costs."""

    currency: Currency
    purchase_date: datetime
    items: tuple[PurchaseItemRequest, ...]
    costs: tuple[PurchaseCostRequest, ...] = ()
    supplier_id: int | None = None
    account_id: int | None = None
    order_number: str | None = None
    tracking_number: str | None = None
    notes: str | None = None
    payment_date: datetime | None = None


@dataclass(frozen=True, slots=True)
class RegisteredPurchase:
    """The persisted purchase aggregate returned by registration."""

    purchase: Purchase
    items: tuple[PurchaseItem, ...]
    costs: tuple[PurchaseCost, ...]
    allocations: tuple[PurchaseCostAllocation, ...]
    total: Money


class RegisterPurchase:
    """Persist a purchase, its items, costs and normalized allocations.

    If ``account_id`` is supplied, V1 full payment is registered immediately
    and a negative ``PURCHASE`` ledger entry is created. The caller must run
    this use case inside a database transaction so a partial failure rolls
    back every inserted row.
    """

    def __init__(
        self,
        accounts: AccountRepository,
        purchases: PurchaseRepository,
        items: PurchaseItemRepository,
        costs: PurchaseCostRepository,
        allocations: PurchaseCostAllocationRepository,
        exchange_rates: ExchangeRateRepository,
        transactions: FinancialTransactionRepository,
    ) -> None:
        self._accounts = accounts
        self._purchases = purchases
        self._items = items
        self._costs = costs
        self._allocations = allocations
        self._exchange_rates = exchange_rates
        self._transactions = transactions

    def execute(
        self, request: RegisterPurchaseRequest
    ) -> RegisteredPurchase:
        if not request.items:
            raise InvalidPurchaseError(
                "A purchase requires at least one item."
            )

        account: Account | None = None
        if request.account_id is not None:
            account = require_active_account(
                self._accounts, request.account_id
            )
            if account.currency.code != request.currency.code:
                raise AccountCurrencyMismatchError(
                    f"Account currency {account.currency.code} does not "
                    f"match purchase currency {request.currency.code}."
                )

        stored_purchase = self._purchases.add(
            Purchase(
                currency=request.currency,
                purchase_date=request.purchase_date,
                supplier_id=request.supplier_id,
                account=account,
                status=(
                    PurchaseStatus.PURCHASED
                    if account is not None
                    else PurchaseStatus.PENDING
                ),
                order_number=request.order_number,
                tracking_number=request.tracking_number,
                notes=request.notes,
            )
        )
        if stored_purchase.id is None:
            raise RuntimeError("Persisted purchase has no identifier.")

        stored_items = tuple(
            self._items.add(
                PurchaseItem(
                    purchase=stored_purchase,
                    variant_id=item.variant_id,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    weight=item.weight,
                )
            )
            for item in request.items
        )

        stored_costs: list[PurchaseCost] = []
        for cost_request in request.costs:
            exchange_rate = None
            if cost_request.exchange_rate_id is not None:
                exchange_rate = self._exchange_rates.get_by_id(
                    cost_request.exchange_rate_id
                )
                if exchange_rate is None:
                    raise ExchangeRateNotFoundError(
                        f"Exchange rate {cost_request.exchange_rate_id} "
                        "does not exist."
                    )
            stored_costs.append(
                self._costs.add(
                    PurchaseCost(
                        purchase=stored_purchase,
                        cost_type=cost_request.cost_type,
                        amount=cost_request.amount,
                        allocation_method=(
                            cost_request.allocation_method
                        ),
                        exchange_rate=exchange_rate,
                        description=cost_request.description,
                    )
                )
            )

        total = purchase_total(stored_items, stored_costs)
        if account is not None and total.is_zero:
            raise PurchasePaymentError(
                "A fully paid purchase must have a positive total."
            )

        stored_allocations: list[PurchaseCostAllocation] = []
        for cost_request, stored_cost in zip(
            request.costs, stored_costs, strict=True
        ):
            manual_allocations = self._manual_allocations(
                cost_request, stored_items
            )
            generated = allocate_purchase_cost(
                stored_cost, stored_items, manual_allocations
            )
            stored_allocations.extend(
                self._allocations.add(allocation)
                for allocation in generated
            )

        if account is not None:
            self._transactions.add(
                FinancialTransaction(
                    account=account,
                    amount=-total,
                    transaction_type=FinancialTransactionType.PURCHASE,
                    transaction_date=(
                        request.payment_date or datetime.now(UTC)
                    ),
                    description="Purchase payment",
                    purchase_id=stored_purchase.id,
                )
            )

        return RegisteredPurchase(
            purchase=stored_purchase,
            items=stored_items,
            costs=tuple(stored_costs),
            allocations=tuple(stored_allocations),
            total=total,
        )

    @staticmethod
    def _manual_allocations(
        request: PurchaseCostRequest,
        items: tuple[PurchaseItem, ...],
    ) -> Mapping[int, Money] | None:
        if request.manual_allocations is None:
            return None

        mapped: dict[int, Money] = {}
        for index, amount in request.manual_allocations.items():
            if index < 0 or index >= len(items):
                raise InvalidCostAllocationError(
                    f"Manual allocation item index {index} is out of range."
                )
            item_id = items[index].id
            if item_id is None:
                raise RuntimeError("Persisted purchase item has no identifier.")
            mapped[item_id] = amount
        return mapped
