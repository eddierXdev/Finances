"""Register full purchase payment use case."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.application.accounts import require_active_account
from app.domain.entities.financial_transaction import FinancialTransaction
from app.domain.entities.purchase import Purchase
from app.domain.enums.financial_transaction_type import (
    FinancialTransactionType,
)
from app.domain.exceptions import (
    InvalidPurchaseError,
    PurchaseNotFoundError,
    PurchasePaymentError,
)
from app.domain.purchase_costing import purchase_total
from app.domain.repositories.account_repository import AccountRepository
from app.domain.repositories.financial_transaction_repository import (
    FinancialTransactionRepository,
)
from app.domain.repositories.purchase_cost_repository import (
    PurchaseCostRepository,
)
from app.domain.repositories.purchase_item_repository import (
    PurchaseItemRepository,
)
from app.domain.repositories.purchase_repository import PurchaseRepository


@dataclass(frozen=True, slots=True)
class RegisterPurchasePaymentRequest:
    """Input for paying a pending purchase in full."""

    purchase_id: int
    account_id: int
    payment_date: datetime | None = None


class RegisterPurchasePayment:
    """Record the single full payment allowed by V1.

    The status change and the negative ``PURCHASE`` ledger entry must be
    committed as one transaction.
    """

    def __init__(
        self,
        accounts: AccountRepository,
        purchases: PurchaseRepository,
        items: PurchaseItemRepository,
        costs: PurchaseCostRepository,
        transactions: FinancialTransactionRepository,
    ) -> None:
        self._accounts = accounts
        self._purchases = purchases
        self._items = items
        self._costs = costs
        self._transactions = transactions

    def execute(
        self, request: RegisterPurchasePaymentRequest
    ) -> Purchase:
        purchase = self._purchases.get_by_id(request.purchase_id)
        if purchase is None:
            raise PurchaseNotFoundError(
                f"Purchase {request.purchase_id} does not exist."
            )

        account = require_active_account(
            self._accounts, request.account_id
        )
        paid_purchase = purchase.register_payment(account)

        items = self._items.list_for_purchase(request.purchase_id)
        costs = self._costs.list_for_purchase(request.purchase_id)
        total = purchase_total(items, costs)
        if total.is_zero:
            raise PurchasePaymentError(
                "A fully paid purchase must have a positive total."
            )
        if paid_purchase.id is None:
            raise InvalidPurchaseError(
                "Purchase must be persisted before payment."
            )

        stored = self._purchases.save(paid_purchase)
        self._transactions.add(
            FinancialTransaction(
                account=account,
                amount=-total,
                transaction_type=FinancialTransactionType.PURCHASE,
                transaction_date=request.payment_date or datetime.now(UTC),
                description="Purchase payment",
                purchase_id=paid_purchase.id,
            )
        )
        return stored
