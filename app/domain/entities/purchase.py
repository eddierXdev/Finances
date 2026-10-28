"""Purchase entity and lifecycle rules."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime

from app.domain.entities.account import Account
from app.domain.entities.currency import Currency
from app.domain.enums.purchase_status import PurchaseStatus
from app.domain.exceptions import (
    AccountCurrencyMismatchError,
    InactiveAccountError,
    InvalidPurchaseError,
    InvalidPurchaseTransitionError,
    PurchasePaymentError,
)
from app.domain.value_objects.text_rules import optional_text

_PAID_STATUSES = frozenset(
    {
        PurchaseStatus.PURCHASED,
        PurchaseStatus.SHIPPED,
        PurchaseStatus.IN_TRANSIT,
        PurchaseStatus.PARTIALLY_RECEIVED,
        PurchaseStatus.RECEIVED,
    }
)
_UNPAID_STATUSES = frozenset(
    {PurchaseStatus.PENDING, PurchaseStatus.CANCELLED}
)

_ALLOWED_TRANSITIONS: dict[PurchaseStatus, frozenset[PurchaseStatus]] = {
    PurchaseStatus.PENDING: frozenset(
        {PurchaseStatus.PURCHASED, PurchaseStatus.CANCELLED}
    ),
    PurchaseStatus.PURCHASED: frozenset(
        {PurchaseStatus.SHIPPED, PurchaseStatus.IN_TRANSIT}
    ),
    PurchaseStatus.SHIPPED: frozenset({PurchaseStatus.IN_TRANSIT}),
    PurchaseStatus.IN_TRANSIT: frozenset(
        {PurchaseStatus.PARTIALLY_RECEIVED, PurchaseStatus.RECEIVED}
    ),
    PurchaseStatus.PARTIALLY_RECEIVED: frozenset(
        {PurchaseStatus.PARTIALLY_RECEIVED, PurchaseStatus.RECEIVED}
    ),
    PurchaseStatus.RECEIVED: frozenset(),
    PurchaseStatus.CANCELLED: frozenset(),
}


@dataclass(frozen=True, slots=True)
class Purchase:
    """A purchase header.

    A purchase may exist unpaid while its account is unknown. Once paid, the
    paying account is mandatory and its native currency must match the
    purchase currency.
    """

    currency: Currency
    purchase_date: datetime
    supplier_id: int | None = None
    account: Account | None = None
    status: PurchaseStatus = PurchaseStatus.PENDING
    order_number: str | None = None
    tracking_number: str | None = None
    notes: str | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.currency, Currency):
            raise TypeError("Purchase currency must be a Currency instance.")

        if not isinstance(self.purchase_date, datetime):
            raise TypeError("Purchase date must be a datetime.")
        if (
            self.purchase_date.tzinfo is None
            or self.purchase_date.utcoffset() is None
        ):
            raise InvalidPurchaseError(
                "Purchase date must be timezone-aware."
            )
        object.__setattr__(
            self, "purchase_date", self.purchase_date.astimezone(UTC)
        )

        if self.supplier_id is not None:
            if (
                isinstance(self.supplier_id, bool)
                or not isinstance(self.supplier_id, int)
                or self.supplier_id <= 0
            ):
                raise InvalidPurchaseError(
                    "Purchase supplier_id must be a positive integer."
                )

        if not isinstance(self.status, PurchaseStatus):
            raise TypeError(
                "Purchase status must be a PurchaseStatus instance."
            )

        if self.account is not None:
            if not isinstance(self.account, Account):
                raise TypeError("Purchase account must be an Account or None.")
            if self.account.id is None:
                raise InvalidPurchaseError(
                    "Purchase account must be persisted."
                )
            if self.account.currency.code != self.currency.code:
                raise AccountCurrencyMismatchError(
                    f"Account currency {self.account.currency.code} does "
                    f"not match purchase currency {self.currency.code}."
                )

        if self.status in _PAID_STATUSES and self.account is None:
            raise InvalidPurchaseError(
                f"Purchase status {self.status.value} requires a paying "
                "account."
            )
        if self.status in _UNPAID_STATUSES and self.account is not None:
            raise InvalidPurchaseError(
                f"Purchase status {self.status.value} cannot have a paying "
                "account."
            )

        object.__setattr__(
            self,
            "order_number",
            optional_text(self.order_number, "Purchase order_number"),
        )
        object.__setattr__(
            self,
            "tracking_number",
            optional_text(
                self.tracking_number, "Purchase tracking_number"
            ),
        )
        object.__setattr__(
            self, "notes", optional_text(self.notes, "Purchase notes")
        )

        if self.id is not None:
            if (
                isinstance(self.id, bool)
                or not isinstance(self.id, int)
                or self.id <= 0
            ):
                raise ValueError("Purchase id must be a positive integer.")

    @property
    def account_id(self) -> int | None:
        return self.account.id if self.account is not None else None

    @property
    def is_paid(self) -> bool:
        return self.account is not None

    @property
    def allowed_logistics_transitions(self) -> tuple[PurchaseStatus, ...]:
        """Return targets that only change logistics, never money or stock."""
        order = (
            PurchaseStatus.SHIPPED,
            PurchaseStatus.IN_TRANSIT,
            PurchaseStatus.CANCELLED,
        )
        return tuple(
            status
            for status in order
            if status in _ALLOWED_TRANSITIONS[self.status]
        )

    def register_payment(self, account: Account) -> Purchase:
        """Return a fully paid copy of this purchase."""
        if self.status is not PurchaseStatus.PENDING:
            raise PurchasePaymentError(
                "Only a pending purchase can register its full payment."
            )
        if self.account is not None:
            raise PurchasePaymentError("Purchase payment is already recorded.")
        if not isinstance(account, Account):
            raise TypeError("Payment account must be an Account.")
        if not account.is_active:
            raise InactiveAccountError(
                f"Account {account.id} is inactive."
            )
        if account.currency.code != self.currency.code:
            raise AccountCurrencyMismatchError(
                f"Account currency {account.currency.code} does not match "
                f"purchase currency {self.currency.code}."
            )

        return replace(self, account=account, status=PurchaseStatus.PURCHASED)

    def transition_to(self, status: PurchaseStatus) -> Purchase:
        """Return a copy with a validated logistics status transition."""
        if not isinstance(status, PurchaseStatus):
            raise TypeError("Target status must be a PurchaseStatus.")
        if status not in _ALLOWED_TRANSITIONS[self.status]:
            raise InvalidPurchaseTransitionError(
                f"Cannot transition purchase from {self.status.value} to "
                f"{status.value}."
            )
        return replace(self, status=status)
