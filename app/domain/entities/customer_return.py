"""Customer return header entity."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.domain.entities.account import Account
from app.domain.entities.sale import Sale
from app.domain.exceptions import (
    AccountCurrencyMismatchError,
    CustomerRefundError,
    InvalidCustomerReturnError,
    SaleCurrencyMismatchError,
)
from app.domain.value_objects.money import Money
from app.domain.value_objects.text_rules import optional_text


@dataclass(frozen=True, slots=True)
class CustomerReturn:
    """A return against an original sale, optionally with a refund.

    A return may be recorded without money moving, for example when the
    customer receives an exchange or the item is damaged. When a refund is
    present, its account and currency are fixed by the original sale.
    """

    sale: Sale
    return_date: datetime
    account: Account | None = None
    refund_amount: Money | None = None
    notes: str | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.sale, Sale):
            raise TypeError("CustomerReturn requires a Sale.")
        if self.sale.id is None:
            raise InvalidCustomerReturnError(
                "CustomerReturn requires a persisted sale."
            )

        if not isinstance(self.return_date, datetime):
            raise TypeError("CustomerReturn return_date must be a datetime.")
        if (
            self.return_date.tzinfo is None
            or self.return_date.utcoffset() is None
        ):
            raise InvalidCustomerReturnError(
                "CustomerReturn return_date must be timezone-aware."
            )
        object.__setattr__(
            self,
            "return_date",
            self.return_date.astimezone(UTC),
        )

        if self.refund_amount is None:
            if self.account is not None:
                raise InvalidCustomerReturnError(
                    "A refund account requires a refund amount."
                )
        else:
            if not isinstance(self.refund_amount, Money):
                raise TypeError(
                    "CustomerReturn refund_amount must be Money or None."
                )
            if not self.refund_amount.is_positive:
                raise CustomerRefundError(
                    "Customer refund amount must be positive."
                )
            if (
                self.refund_amount.currency.code
                != self.sale.currency.code
            ):
                raise SaleCurrencyMismatchError(
                    f"Refund currency "
                    f"{self.refund_amount.currency.code} does not match "
                    f"sale currency {self.sale.currency.code}."
                )

            if self.account is None:
                raise InvalidCustomerReturnError(
                    "A customer refund requires an account."
                )
            if not isinstance(self.account, Account):
                raise TypeError(
                    "CustomerReturn account must be an Account or None."
                )
            if self.account.id is None:
                raise InvalidCustomerReturnError(
                    "CustomerReturn refund account must be persisted."
                )
            if (
                self.account.currency.code
                != self.refund_amount.currency.code
            ):
                raise AccountCurrencyMismatchError(
                    f"Account currency {self.account.currency.code} does "
                    f"not match refund currency "
                    f"{self.refund_amount.currency.code}."
                )

        object.__setattr__(
            self, "notes", optional_text(self.notes, "CustomerReturn notes")
        )

        if self.id is not None:
            if (
                isinstance(self.id, bool)
                or not isinstance(self.id, int)
                or self.id <= 0
            ):
                raise ValueError(
                    "CustomerReturn id must be a positive integer."
                )

    @property
    def sale_id(self) -> int | None:
        return self.sale.id

    @property
    def account_id(self) -> int | None:
        return self.account.id if self.account is not None else None

    @property
    def has_refund(self) -> bool:
        return self.refund_amount is not None
