"""Inventory lot entity and remaining-quantity rules."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime

from app.domain.entities.purchase_item import PurchaseItem
from app.domain.exceptions import (
    InsufficientStockError,
    InvalidInventoryError,
    PurchaseCurrencyMismatchError,
)
from app.domain.value_objects.money import Money


def _require_positive_quantity(quantity: int, label: str) -> None:
    if (
        isinstance(quantity, bool)
        or not isinstance(quantity, int)
        or quantity <= 0
    ):
        raise InvalidInventoryError(
            f"{label} quantity must be a positive integer."
        )


@dataclass(frozen=True, slots=True)
class InventoryLot:
    """A traceable batch of stock acquired from one purchase item.

    Lots preserve their original purchase cost and are consumed in FIFO
    order by sales. Quantity changes return new immutable copies.
    """

    purchase_item: PurchaseItem
    variant_id: int
    acquired_quantity: int
    remaining_quantity: int
    unit_cost: Money
    received_at: datetime
    id: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.purchase_item, PurchaseItem):
            raise TypeError("InventoryLot requires a PurchaseItem.")

        if (
            self.purchase_item.id is None
            or self.purchase_item.purchase.id is None
        ):
            raise InvalidInventoryError(
                "InventoryLot requires a persisted purchase item."
            )

        if (
            isinstance(self.variant_id, bool)
            or not isinstance(self.variant_id, int)
            or self.variant_id <= 0
        ):
            raise InvalidInventoryError(
                "InventoryLot variant_id must be a positive integer."
            )
        if self.variant_id != self.purchase_item.variant_id:
            raise InvalidInventoryError(
                "InventoryLot variant must match its purchase item variant."
            )

        if (
            isinstance(self.acquired_quantity, bool)
            or not isinstance(self.acquired_quantity, int)
            or self.acquired_quantity <= 0
        ):
            raise InvalidInventoryError(
                "InventoryLot acquired_quantity must be a positive integer."
            )

        if (
            isinstance(self.remaining_quantity, bool)
            or not isinstance(self.remaining_quantity, int)
            or self.remaining_quantity < 0
            or self.remaining_quantity > self.acquired_quantity
        ):
            raise InvalidInventoryError(
                "InventoryLot remaining_quantity must be between zero and "
                "acquired_quantity."
            )

        if not isinstance(self.unit_cost, Money):
            raise TypeError("InventoryLot unit_cost must be Money.")
        if self.unit_cost.is_negative:
            raise InvalidInventoryError(
                "InventoryLot unit_cost cannot be negative."
            )
        if (
            self.unit_cost.currency.code
            != self.purchase_item.purchase.currency.code
        ):
            raise PurchaseCurrencyMismatchError(
                f"Unit cost currency {self.unit_cost.currency.code} does not "
                "match the purchase currency "
                f"{self.purchase_item.purchase.currency.code}."
            )

        if not isinstance(self.received_at, datetime):
            raise TypeError("InventoryLot received_at must be a datetime.")
        if (
            self.received_at.tzinfo is None
            or self.received_at.utcoffset() is None
        ):
            raise InvalidInventoryError(
                "InventoryLot received_at must be timezone-aware."
            )
        object.__setattr__(
            self, "received_at", self.received_at.astimezone(UTC)
        )

        if self.id is not None:
            if (
                isinstance(self.id, bool)
                or not isinstance(self.id, int)
                or self.id <= 0
            ):
                raise ValueError(
                    "InventoryLot id must be a positive integer."
                )

    @property
    def purchase_item_id(self) -> int | None:
        return self.purchase_item.id

    @property
    def is_exhausted(self) -> bool:
        return self.remaining_quantity == 0

    def consume(self, quantity: int) -> InventoryLot:
        """Return a copy with ``quantity`` units removed from this lot."""
        _require_positive_quantity(quantity, "Consumed")
        if quantity > self.remaining_quantity:
            raise InsufficientStockError(
                f"Cannot consume {quantity} units from lot {self.id}; only "
                f"{self.remaining_quantity} remain."
            )
        return replace(
            self, remaining_quantity=self.remaining_quantity - quantity
        )

    def restore(self, quantity: int) -> InventoryLot:
        """Return a copy with ``quantity`` units returned to this lot."""
        _require_positive_quantity(quantity, "Restored")
        restored_quantity = self.remaining_quantity + quantity
        if restored_quantity > self.acquired_quantity:
            raise InvalidInventoryError(
                f"Restoring {quantity} units would exceed the lot's "
                f"acquired quantity of {self.acquired_quantity}."
            )
        return replace(self, remaining_quantity=restored_quantity)
