"""Capital contribution and withdrawal use cases."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.application.accounts import require_active_account
from app.domain.entities.capital_movement import CapitalMovement
from app.domain.entities.financial_transaction import FinancialTransaction
from app.domain.enums.capital_movement_type import CapitalMovementType
from app.domain.enums.financial_transaction_type import (
    FinancialTransactionType,
)
from app.domain.repositories.account_repository import AccountRepository
from app.domain.repositories.capital_movement_repository import (
    CapitalMovementRepository,
)
from app.domain.repositories.financial_transaction_repository import (
    FinancialTransactionRepository,
)
from app.domain.value_objects.money import Money


@dataclass(frozen=True, slots=True)
class CapitalMovementRequest:
    """Input for a capital contribution or withdrawal."""

    account_id: int
    amount: Money
    movement_date: datetime | None = None
    notes: str | None = None


def _register_capital_movement(
    accounts: AccountRepository,
    movements: CapitalMovementRepository,
    transactions: FinancialTransactionRepository,
    request: CapitalMovementRequest,
    *,
    movement_type: CapitalMovementType,
    transaction_type: FinancialTransactionType,
    description: str,
) -> CapitalMovement:
    account = require_active_account(accounts, request.account_id)
    movement_date = request.movement_date or datetime.now(UTC)

    stored = movements.add(
        CapitalMovement(
            account=account,
            movement_type=movement_type,
            amount=request.amount,
            movement_date=movement_date,
            notes=request.notes,
        )
    )
    if stored.id is None:
        raise RuntimeError("Persisted capital movement has no identifier.")

    transactions.add(
        FinancialTransaction(
            account=account,
            amount=stored.signed_amount,
            transaction_type=transaction_type,
            transaction_date=stored.movement_date,
            description=description,
            capital_movement_id=stored.id,
        )
    )
    return stored


class AddCapital:
    """Register a capital contribution and its signed ledger entry."""

    def __init__(
        self,
        accounts: AccountRepository,
        movements: CapitalMovementRepository,
        transactions: FinancialTransactionRepository,
    ) -> None:
        self._accounts = accounts
        self._movements = movements
        self._transactions = transactions

    def execute(self, request: CapitalMovementRequest) -> CapitalMovement:
        return _register_capital_movement(
            self._accounts,
            self._movements,
            self._transactions,
            request,
            movement_type=CapitalMovementType.CONTRIBUTION,
            transaction_type=FinancialTransactionType.CAPITAL_CONTRIBUTION,
            description="Capital contribution",
        )


class WithdrawCapital:
    """Register a capital withdrawal and its signed ledger entry."""

    def __init__(
        self,
        accounts: AccountRepository,
        movements: CapitalMovementRepository,
        transactions: FinancialTransactionRepository,
    ) -> None:
        self._accounts = accounts
        self._movements = movements
        self._transactions = transactions

    def execute(self, request: CapitalMovementRequest) -> CapitalMovement:
        return _register_capital_movement(
            self._accounts,
            self._movements,
            self._transactions,
            request,
            movement_type=CapitalMovementType.WITHDRAWAL,
            transaction_type=FinancialTransactionType.CAPITAL_WITHDRAWAL,
            description="Capital withdrawal",
        )
