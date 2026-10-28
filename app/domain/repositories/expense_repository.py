"""Expense repository contract."""

from typing import Protocol

from app.domain.entities.expense import Expense


class ExpenseRepository(Protocol):
    """Persistence boundary for operating expenses."""

    def add(self, expense: Expense) -> Expense:
        """Persist an expense."""
        ...

    def get_by_id(self, expense_id: int) -> Expense | None:
        """Return an expense by identifier, if it exists."""
        ...

    def list_all(self) -> list[Expense]:
        """Return expenses, newest first."""
        ...

    def list_for_account(self, account_id: int) -> list[Expense]:
        """Return an account's expenses, oldest first."""
        ...
