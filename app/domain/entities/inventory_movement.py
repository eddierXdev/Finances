"""Inventory movement entity and stock sign convention."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.domain.enums.inventory_movement_type import InventoryMovementType
from app.domain.exceptions import InvalidInventoryMovementError
from app.domain.value_objects.money import Money
from app.domain.value_objects.text_rules import optional_text

_POSITIVE_TYPES = frozenset(
    {
        InventoryMovementType.PURCHASE_RECEIVED,
        InventoryMovementType.CUSTOMER_RETURN,
        InventoryMovementType.ADJUSTMENT_IN,
    }
)
_NEGATIVE_TYPES = frozenset(
    {
        InventoryMovementType.SALE,
        InventoryMovementType.SUPPLIER_RETURN,
        InventoryMovementType.ADJUSTMENT_OUT,
        InventoryMovementType.DAMAGED,
        InventoryMovementType.LOST,
    }
)


@dataclass(frozen=True, slots=True)
class InventoryMovement:
    """A signed, traceable change to sellable stock.

    Stock entering sellable inventory is positive; stock leaving is negative.
    """

    variant_id: int
    movement_type: InventoryMovementType
    quantity: int
    movement_date: datetime
    inventory_lot_id: int | None = None
    unit_cost: Money | None = None
    reference_type: str | None = None
    reference_id: int | None = None
    notes: str | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        if (
            isinstance(self.variant_id, bool)
            or not isinstance(self.variant_id, int)
            or self.variant_id <= 0
        ):
            raise InvalidInventoryMovementError(
                "InventoryMovement variant_id must be a positive integer."
            )

        if not isinstance(self.movement_type, InventoryMovementType):
            raise TypeError(
                "InventoryMovement movement_type must be an "
                "InventoryMovementType."
            )

        if (
            isinstance(self.quantity, bool)
            or not isinstance(self.quantity, int)
            or self.quantity == 0
        ):
            raise InvalidInventoryMovementError(
                "InventoryMovement quantity must be a non-zero integer."
            )
        if (
            self.movement_type in _POSITIVE_TYPES
            and self.quantity < 0
        ):
            raise InvalidInventoryMovementError(
                f"{self.movement_type.value} requires a positive quantity."
            )
        if (
            self.movement_type in _NEGATIVE_TYPES
            and self.quantity > 0
        ):
            raise InvalidInventoryMovementError(
                f"{self.movement_type.value} requires a negative quantity."
            )

        if not isinstance(self.movement_date, datetime):
            raise TypeError(
                "InventoryMovement movement_date must be a datetime."
            )
        if (
            self.movement_date.tzinfo is None
            or self.movement_date.utcoffset() is None
        ):
            raise InvalidInventoryMovementError(
                "InventoryMovement movement_date must be timezone-aware."
            )
        object.__setattr__(
            self,
            "movement_date",
            self.movement_date.astimezone(UTC),
        )

        if self.unit_cost is not None:
            if not isinstance(self.unit_cost, Money):
                raise TypeError(
                    "InventoryMovement unit_cost must be Money or None."
                )
            if self.unit_cost.is_negative:
                raise InvalidInventoryMovementError(
                    "InventoryMovement unit_cost cannot be negative."
                )

        for field_name, value in (
            ("inventory_lot_id", self.inventory_lot_id),
            ("reference_id", self.reference_id),
        ):
            if value is not None and (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value <= 0
            ):
                raise InvalidInventoryMovementError(
                    f"InventoryMovement {field_name} must be a positive "
                    "integer."
                )

        object.__setattr__(
            self,
            "reference_type",
            optional_text(
                self.reference_type, "InventoryMovement reference_type"
            ),
        )
        object.__setattr__(
            self,
            "notes",
            optional_text(self.notes, "InventoryMovement notes"),
        )

        if self.id is not None:
            if (
                isinstance(self.id, bool)
                or not isinstance(self.id, int)
                or self.id <= 0
            ):
                raise ValueError(
                    "InventoryMovement id must be a positive integer."
                )
