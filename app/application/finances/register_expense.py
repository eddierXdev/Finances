"""Register an operating expense and its ledger entry."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.application.accounts import require_active_account
from app.domain.entities.expense import Expense
from app.domain.entities.financial_transaction import FinancialTransaction
from app.domain.enums.expense_type import ExpenseType
from app.domain.enums.financial_transaction_type import (
    FinancialTransactionType,
)
from app.domain.repositories.account_repository import AccountRepository
from app.domain.repositories.expense_repository import ExpenseRepository
from app.domain.repositories.financial_transaction_repository import (
    FinancialTransactionRepository,
)
from app.domain.value_objects.money import Money


@dataclass(frozen=True, slots=True)
class RegisterExpenseRequest:
    """Input for an operating expense."""

    account_id: int
    expense_type: ExpenseType
    amount: Money
    expense_date: datetime
    description: str | None = None
    notes: str | None = None


class RegisterExpense:
    """Persist an expense and its negative ``EXPENSE`` ledger entry."""

    def __init__(
        self,
        accounts: AccountRepository,
        expenses: ExpenseRepository,
        transactions: FinancialTransactionRepository,
    ) -> None:
        self._accounts = accounts
        self._expenses = expenses
        self._transactions = transactions

    def execute(self, request: RegisterExpenseRequest) -> Expense:
        account = require_active_account(
            self._accounts, request.account_id, label="Expense account"
        )

        stored = self._expenses.add(
            Expense(
                account=account,
                expense_type=request.expense_type,
                amount=request.amount,
                expense_date=request.expense_date,
                description=request.description,
                notes=request.notes,
            )
        )
        if stored.id is None:
            raise RuntimeError("Persisted expense has no identifier.")

        self._transactions.add(
            FinancialTransaction(
                account=account,
                amount=stored.signed_amount,
                transaction_type=FinancialTransactionType.EXPENSE,
                transaction_date=stored.expense_date,
                description=(
                    stored.description
                    or f"Expense {stored.expense_type.value}"
                ),
                expense_id=stored.id,
            )
        )
        return stored
