"""Inventory lot repository contract."""

from typing import Protocol

from app.domain.entities.inventory_lot import InventoryLot


class InventoryLotRepository(Protocol):
    """Persistence boundary for inventory lots."""

    def add(self, lot: InventoryLot) -> InventoryLot:
        """Persist a new lot."""
        ...

    def save(self, lot: InventoryLot) -> InventoryLot:
        """Update a lot's remaining quantity; acquisition data is immutable."""
        ...

    def get_by_id(self, lot_id: int) -> InventoryLot | None:
        """Return a lot by identifier, if it exists."""
        ...

    def list_by_variant(self, variant_id: int) -> list[InventoryLot]:
        """Return every lot of a variant in FIFO order."""
        ...

    def list_available_by_variant(
        self, variant_id: int
    ) -> list[InventoryLot]:
        """Return non-exhausted lots of a variant in FIFO order."""
        ...

    def list_for_purchase_item(
        self, purchase_item_id: int
    ) -> list[InventoryLot]:
        """Return the lots created by one purchase item."""
        ...

    def list_for_purchase(self, purchase_id: int) -> list[InventoryLot]:
        """Return every lot created by a purchase."""
        ...

    def total_remaining_by_variant(self, variant_id: int) -> int:
        """Return the current sellable stock of a variant."""
        ...
