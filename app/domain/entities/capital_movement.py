"""Capital movement entity."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.domain.entities.account import Account
from app.domain.enums.capital_movement_type import CapitalMovementType
from app.domain.exceptions import AccountCurrencyMismatchError
from app.domain.value_objects.money import Money
from app.domain.value_objects.text_rules import optional_text


@dataclass(frozen=True, slots=True)
class CapitalMovement:
    """A capital contribution or withdrawal.

    ``amount`` is always positive; the ledger sign is derived from the
    movement type so capital history stays unambiguous.
    """

    account: Account
    movement_type: CapitalMovementType
    amount: Money
    movement_date: datetime
    notes: str | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.account, Account):
            raise TypeError("CapitalMovement requires an Account.")
        if not isinstance(self.amount, Money):
            raise TypeError("CapitalMovement amount must be Money.")

        if self.amount.currency.code != self.account.currency.code:
            raise AccountCurrencyMismatchError(
                f"Capital currency {self.amount.currency.code} does not "
                f"match account currency {self.account.currency.code}."
            )

        if not self.amount.is_positive:
            raise ValueError("CapitalMovement amount must be greater than zero.")

        if not isinstance(self.movement_type, CapitalMovementType):
            raise TypeError(
                "CapitalMovement movement_type must be a CapitalMovementType."
            )

        if not isinstance(self.movement_date, datetime):
            raise TypeError("CapitalMovement date must be a datetime.")
        if (
            self.movement_date.tzinfo is None
            or self.movement_date.utcoffset() is None
        ):
            raise ValueError("CapitalMovement date must be timezone-aware.")
        object.__setattr__(
            self, "movement_date", self.movement_date.astimezone(UTC)
        )

        object.__setattr__(
            self, "notes", optional_text(self.notes, "CapitalMovement notes")
        )

        if self.id is not None:
            if (
                isinstance(self.id, bool)
                or not isinstance(self.id, int)
                or self.id <= 0
            ):
                raise ValueError(
                    "CapitalMovement id must be a positive integer."
                )

    @property
    def signed_amount(self) -> Money:
        """Return the ledger amount: positive in, negative out."""
        if self.movement_type is CapitalMovementType.CONTRIBUTION:
            return self.amount
        return -self.amount
