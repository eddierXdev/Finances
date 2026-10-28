"""FIFO lot selection."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from app.domain.entities.inventory_lot import InventoryLot
from app.domain.exceptions import (
    InsufficientStockError,
    InvalidInventoryError,
)


@dataclass(frozen=True, slots=True)
class FifoTake:
    """A quantity selected from one inventory lot."""

    lot: InventoryLot
    quantity: int


def allocate_fifo(
    lots: Sequence[InventoryLot], quantity: int
) -> tuple[FifoTake, ...]:
    """Select ``quantity`` units from the oldest available lots.

    Lots are ordered by receipt time and then by id. Exhausted lots are
    ignored. The returned takes are a plan; callers are responsible for
    persisting the consumed lot copies and allocations.
    """
    if (
        isinstance(quantity, bool)
        or not isinstance(quantity, int)
        or quantity <= 0
    ):
        raise InvalidInventoryError(
            "FIFO quantity must be a positive integer."
        )

    available = sorted(
        (lot for lot in lots if lot.remaining_quantity > 0),
        key=lambda lot: (
            lot.received_at,
            lot.id if lot.id is not None else 0,
        ),
    )
    total_available = sum(lot.remaining_quantity for lot in available)
    if total_available < quantity:
        raise InsufficientStockError(
            f"Cannot allocate {quantity} units; only {total_available} "
            "available."
        )

    takes: list[FifoTake] = []
    pending = quantity
    for lot in available:
        take = min(lot.remaining_quantity, pending)
        takes.append(FifoTake(lot=lot, quantity=take))
        pending -= take
        if pending == 0:
            break

    return tuple(takes)
