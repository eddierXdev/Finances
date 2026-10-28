"""Sale header entity."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime

from app.domain.entities.account import Account
from app.domain.entities.currency import Currency
from app.domain.enums.sale_status import SaleStatus
from app.domain.exceptions import (
    AccountCurrencyMismatchError,
    InvalidSaleError,
    InvalidSaleTransitionError,
    SaleCurrencyMismatchError,
)
from app.domain.value_objects.money import Money
from app.domain.value_objects.text_rules import optional_text

_ALLOWED_TRANSITIONS: dict[SaleStatus, frozenset[SaleStatus]] = {
    SaleStatus.COMPLETED: frozenset(
        {SaleStatus.PARTIALLY_REFUNDED, SaleStatus.REFUNDED}
    ),
    SaleStatus.PARTIALLY_REFUNDED: frozenset({SaleStatus.REFUNDED}),
    SaleStatus.REFUNDED: frozenset(),
    SaleStatus.CANCELLED: frozenset(),
}


@dataclass(frozen=True, slots=True)
class Sale:
    """A fully collected sale whose account matches its currency."""

    account: Account
    currency: Currency
    sale_date: datetime
    customer_id: int | None = None
    status: SaleStatus = SaleStatus.COMPLETED
    discount_amount: Money | None = None
    notes: str | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.account, Account):
            raise TypeError("Sale account must be an Account.")
        if self.account.id is None:
            raise InvalidSaleError("Sale account must be persisted.")

        if not isinstance(self.currency, Currency):
            raise TypeError("Sale currency must be a Currency instance.")

        if self.account.currency.code != self.currency.code:
            raise AccountCurrencyMismatchError(
                f"Account currency {self.account.currency.code} does not "
                f"match sale currency {self.currency.code}."
            )

        if not isinstance(self.sale_date, datetime):
            raise TypeError("Sale date must be a datetime.")
        if (
            self.sale_date.tzinfo is None
            or self.sale_date.utcoffset() is None
        ):
            raise InvalidSaleError("Sale date must be timezone-aware.")
        object.__setattr__(
            self, "sale_date", self.sale_date.astimezone(UTC)
        )

        if self.customer_id is not None:
            if (
                isinstance(self.customer_id, bool)
                or not isinstance(self.customer_id, int)
                or self.customer_id <= 0
            ):
                raise InvalidSaleError(
                    "Sale customer_id must be a positive integer."
                )

        if not isinstance(self.status, SaleStatus):
            raise TypeError("Sale status must be a SaleStatus instance.")

        if self.discount_amount is not None:
            if not isinstance(self.discount_amount, Money):
                raise TypeError("Sale discount_amount must be Money.")
            if self.discount_amount.is_negative:
                raise InvalidSaleError(
                    "Sale discount_amount cannot be negative."
                )
            if self.discount_amount.currency.code != self.currency.code:
                raise SaleCurrencyMismatchError(
                    f"Discount currency "
                    f"{self.discount_amount.currency.code} does not match "
                    f"sale currency {self.currency.code}."
                )

        object.__setattr__(
            self, "notes", optional_text(self.notes, "Sale notes")
        )

        if self.id is not None:
            if (
                isinstance(self.id, bool)
                or not isinstance(self.id, int)
                or self.id <= 0
            ):
                raise ValueError("Sale id must be a positive integer.")

    @property
    def account_id(self) -> int | None:
        return self.account.id

    def transition_to(self, status: SaleStatus) -> Sale:
        """Return a copy with a validated refund-status transition."""
        if not isinstance(status, SaleStatus):
            raise TypeError("Sale status must be a SaleStatus instance.")
        if status not in _ALLOWED_TRANSITIONS[self.status]:
            raise InvalidSaleTransitionError(
                f"Sale status cannot change from {self.status.value} to "
                f"{status.value}."
            )
        return replace(self, status=status)
