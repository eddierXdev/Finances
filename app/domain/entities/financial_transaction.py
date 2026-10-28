"""Financial transaction entity and ledger sign rules."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.domain.entities.account import Account
from app.domain.enums.financial_transaction_type import FinancialTransactionType
from app.domain.exceptions import (
    AccountCurrencyMismatchError,
    InvalidLedgerEntryError,
)
from app.domain.value_objects.money import Money
from app.domain.value_objects.text_rules import optional_text

# Types whose direction is fixed by business meaning: 1 means inflow,
# -1 means outflow. TRANSFER, CURRENCY_EXCHANGE and ADJUSTMENT may use
# either sign depending on which side of the operation they represent.
_FIXED_DIRECTIONS: dict[FinancialTransactionType, int] = {
    FinancialTransactionType.CAPITAL_CONTRIBUTION: 1,
    FinancialTransactionType.CAPITAL_WITHDRAWAL: -1,
    FinancialTransactionType.PURCHASE: -1,
    FinancialTransactionType.SALE: 1,
    FinancialTransactionType.EXPENSE: -1,
    FinancialTransactionType.CUSTOMER_REFUND: -1,
    FinancialTransactionType.SUPPLIER_REFUND: 1,
}


@dataclass(frozen=True, slots=True)
class FinancialTransaction:
    """A single signed movement in the financial ledger.

    Money entering an account is positive; money leaving is negative.
    """

    account: Account
    amount: Money
    transaction_type: FinancialTransactionType
    transaction_date: datetime
    description: str | None = None
    purchase_id: int | None = None
    sale_id: int | None = None
    expense_id: int | None = None
    customer_return_id: int | None = None
    supplier_return_id: int | None = None
    capital_movement_id: int | None = None
    account_transfer_id: int | None = None
    exchange_rate_id: int | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.account, Account):
            raise TypeError("FinancialTransaction requires an Account.")

        if not isinstance(self.amount, Money):
            raise TypeError("FinancialTransaction amount must be Money.")

        if self.amount.currency.code != self.account.currency.code:
            raise AccountCurrencyMismatchError(
                f"Transaction currency {self.amount.currency.code} does not "
                f"match account currency {self.account.currency.code}."
            )

        if self.amount.is_zero:
            raise InvalidLedgerEntryError(
                "Financial transactions cannot have a zero amount."
            )

        if not isinstance(self.transaction_type, FinancialTransactionType):
            raise TypeError(
                "FinancialTransaction transaction_type must be a "
                "FinancialTransactionType."
            )

        expected_direction = _FIXED_DIRECTIONS.get(self.transaction_type)
        if expected_direction == 1 and not self.amount.is_positive:
            raise InvalidLedgerEntryError(
                f"{self.transaction_type.value} requires a positive amount."
            )
        if expected_direction == -1 and not self.amount.is_negative:
            raise InvalidLedgerEntryError(
                f"{self.transaction_type.value} requires a negative amount."
            )

        if not isinstance(self.transaction_date, datetime):
            raise TypeError("FinancialTransaction date must be a datetime.")
        if (
            self.transaction_date.tzinfo is None
            or self.transaction_date.utcoffset() is None
        ):
            raise InvalidLedgerEntryError(
                "FinancialTransaction date must be timezone-aware."
            )
        object.__setattr__(
            self,
            "transaction_date",
            self.transaction_date.astimezone(UTC),
        )

        source_ids = (
            self.purchase_id,
            self.sale_id,
            self.expense_id,
            self.customer_return_id,
            self.supplier_return_id,
            self.capital_movement_id,
            self.account_transfer_id,
        )
        populated_sources = [
            source_id for source_id in source_ids if source_id is not None
        ]
        if len(populated_sources) > 1:
            raise InvalidLedgerEntryError(
                "A financial transaction can reference at most one "
                "business source."
            )
        for source_id in populated_sources:
            if (
                isinstance(source_id, bool)
                or not isinstance(source_id, int)
                or source_id <= 0
            ):
                raise InvalidLedgerEntryError(
                    "Business source ids must be positive integers."
                )

        if self.exchange_rate_id is not None:
            if (
                isinstance(self.exchange_rate_id, bool)
                or not isinstance(self.exchange_rate_id, int)
                or self.exchange_rate_id <= 0
            ):
                raise InvalidLedgerEntryError(
                    "FinancialTransaction exchange_rate_id must be a "
                    "positive integer."
                )

        object.__setattr__(
            self,
            "description",
            optional_text(self.description, "FinancialTransaction description"),
        )

        if self.id is not None:
            if (
                isinstance(self.id, bool)
                or not isinstance(self.id, int)
                or self.id <= 0
            ):
                raise ValueError(
                    "FinancialTransaction id must be a positive integer."
                )

    @property
    def account_id(self) -> int | None:
        return self.account.id

    @property
    def currency_code(self) -> str:
        return self.amount.currency.code
