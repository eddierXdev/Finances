"""Expense entity."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.domain.entities.account import Account
from app.domain.enums.expense_type import ExpenseType
from app.domain.exceptions import (
    AccountCurrencyMismatchError,
    InvalidExpenseError,
)
from app.domain.value_objects.money import Money
from app.domain.value_objects.text_rules import optional_text


@dataclass(frozen=True, slots=True)
class Expense:
    """An operating expense paid from one account.

    ``amount`` is always positive; the ledger sign is always negative.
    """

    account: Account
    expense_type: ExpenseType
    amount: Money
    expense_date: datetime
    description: str | None = None
    notes: str | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.account, Account):
            raise TypeError("Expense requires an Account.")
        if not isinstance(self.amount, Money):
            raise TypeError("Expense amount must be Money.")

        if self.amount.currency.code != self.account.currency.code:
            raise AccountCurrencyMismatchError(
                f"Expense currency {self.amount.currency.code} does not "
                f"match account currency {self.account.currency.code}."
            )

        if not self.amount.is_positive:
            raise InvalidExpenseError(
                "Expense amount must be greater than zero."
            )

        if not isinstance(self.expense_type, ExpenseType):
            raise TypeError(
                "Expense expense_type must be an ExpenseType."
            )

        if not isinstance(self.expense_date, datetime):
            raise TypeError("Expense date must be a datetime.")
        if (
            self.expense_date.tzinfo is None
            or self.expense_date.utcoffset() is None
        ):
            raise InvalidExpenseError(
                "Expense date must be timezone-aware."
            )
        object.__setattr__(
            self, "expense_date", self.expense_date.astimezone(UTC)
        )

        object.__setattr__(
            self,
            "description",
            optional_text(self.description, "Expense description"),
        )
        object.__setattr__(
            self, "notes", optional_text(self.notes, "Expense notes")
        )

        if self.id is not None:
            if (
                isinstance(self.id, bool)
                or not isinstance(self.id, int)
                or self.id <= 0
            ):
                raise ValueError("Expense id must be a positive integer.")

    @property
    def account_id(self) -> int | None:
        return self.account.id

    @property
    def currency_code(self) -> str:
        return self.amount.currency.code

    @property
    def signed_amount(self) -> Money:
        """Return the ledger amount: expenses are always negative."""
        return -self.amount
