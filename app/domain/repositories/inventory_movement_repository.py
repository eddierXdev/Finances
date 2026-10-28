"""Inventory movement repository contract."""

from typing import Protocol

from app.domain.entities.inventory_movement import InventoryMovement


class InventoryMovementRepository(Protocol):
    """Persistence boundary for inventory movement history."""

    def add(self, movement: InventoryMovement) -> InventoryMovement:
        """Persist one movement."""
        ...

    def get_by_id(self, movement_id: int) -> InventoryMovement | None:
        """Return a movement by identifier, if it exists."""
        ...

    def list_by_variant(self, variant_id: int) -> list[InventoryMovement]:
        """Return a variant's movements in chronological order."""
        ...

    def list_for_lot(self, lot_id: int) -> list[InventoryMovement]:
        """Return the movements that reference one lot."""
        ...
