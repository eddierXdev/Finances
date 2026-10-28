"""Supplier return header entity."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.domain.entities.account import Account
from app.domain.entities.purchase import Purchase
from app.domain.exceptions import (
    AccountCurrencyMismatchError,
    InvalidSupplierReturnError,
    PurchaseCurrencyMismatchError,
    SupplierRefundError,
)
from app.domain.value_objects.money import Money
from app.domain.value_objects.text_rules import optional_text


@dataclass(frozen=True, slots=True)
class SupplierReturn:
    """A return against an original purchase, optionally with a refund.

    A return may be recorded without money moving, for example when the
    supplier replaces the merchandise. When a refund is present, its account
    and currency are fixed by the original purchase.
    """

    purchase: Purchase
    return_date: datetime
    supplier_id: int | None = None
    account: Account | None = None
    refund_amount: Money | None = None
    notes: str | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.purchase, Purchase):
            raise TypeError("SupplierReturn requires a Purchase.")
        if self.purchase.id is None:
            raise InvalidSupplierReturnError(
                "SupplierReturn requires a persisted purchase."
            )

        if not isinstance(self.return_date, datetime):
            raise TypeError("SupplierReturn return_date must be a datetime.")
        if (
            self.return_date.tzinfo is None
            or self.return_date.utcoffset() is None
        ):
            raise InvalidSupplierReturnError(
                "SupplierReturn return_date must be timezone-aware."
            )
        object.__setattr__(
            self,
            "return_date",
            self.return_date.astimezone(UTC),
        )

        if self.supplier_id is not None:
            if (
                isinstance(self.supplier_id, bool)
                or not isinstance(self.supplier_id, int)
                or self.supplier_id <= 0
            ):
                raise InvalidSupplierReturnError(
                    "SupplierReturn supplier_id must be a positive integer."
                )
            if (
                self.purchase.supplier_id is None
                or self.supplier_id != self.purchase.supplier_id
            ):
                raise InvalidSupplierReturnError(
                    "A supplier return must reference the original "
                    "purchase supplier."
                )

        if self.refund_amount is None:
            if self.account is not None:
                raise InvalidSupplierReturnError(
                    "A refund account requires a refund amount."
                )
        else:
            if not isinstance(self.refund_amount, Money):
                raise TypeError(
                    "SupplierReturn refund_amount must be Money or None."
                )
            if not self.refund_amount.is_positive:
                raise SupplierRefundError(
                    "Supplier refund amount must be positive."
                )
            if (
                self.refund_amount.currency.code
                != self.purchase.currency.code
            ):
                raise PurchaseCurrencyMismatchError(
                    f"Refund currency "
                    f"{self.refund_amount.currency.code} does not match "
                    f"purchase currency {self.purchase.currency.code}."
                )

            if self.account is None:
                raise InvalidSupplierReturnError(
                    "A supplier refund requires an account."
                )
            if not isinstance(self.account, Account):
                raise TypeError(
                    "SupplierReturn account must be an Account or None."
                )
            if self.account.id is None:
                raise InvalidSupplierReturnError(
                    "SupplierReturn refund account must be persisted."
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
            self, "notes", optional_text(self.notes, "SupplierReturn notes")
        )

        if self.id is not None:
            if (
                isinstance(self.id, bool)
                or not isinstance(self.id, int)
                or self.id <= 0
            ):
                raise ValueError(
                    "SupplierReturn id must be a positive integer."
                )

    @property
    def purchase_id(self) -> int | None:
        return self.purchase.id

    @property
    def account_id(self) -> int | None:
        return self.account.id if self.account is not None else None

    @property
    def has_refund(self) -> bool:
        return self.refund_amount is not None
