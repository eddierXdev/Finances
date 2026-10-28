"""Sale FIFO allocation repository contract."""

from typing import Protocol

from app.domain.entities.sale_item_lot_allocation import (
    SaleItemLotAllocation,
)


class SaleItemLotAllocationRepository(Protocol):
    """Persistence boundary for historical FIFO allocations."""

    def add(
        self, allocation: SaleItemLotAllocation
    ) -> SaleItemLotAllocation:
        """Persist one immutable allocation snapshot."""
        ...

    def get_by_id(
        self, allocation_id: int
    ) -> SaleItemLotAllocation | None:
        """Return an allocation by identifier, if it exists."""
        ...

    def list_for_sale_item(
        self, sale_item_id: int
    ) -> list[SaleItemLotAllocation]:
        """Return one sale item's allocations in creation order."""
        ...

    def list_for_sale(
        self, sale_id: int
    ) -> list[SaleItemLotAllocation]:
        """Return every allocation of a sale in creation order."""
        ...

    def list_for_lot(
        self, lot_id: int
    ) -> list[SaleItemLotAllocation]:
        """Return the allocations that consumed one lot."""
        ...
