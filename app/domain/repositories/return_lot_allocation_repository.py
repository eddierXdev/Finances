"""Return lot allocation repository contract."""

from typing import Protocol

from app.domain.entities.return_lot_allocation import ReturnLotAllocation


class ReturnLotAllocationRepository(Protocol):
    """Persistence boundary for historical return reversals."""

    def add(
        self, allocation: ReturnLotAllocation
    ) -> ReturnLotAllocation:
        """Persist one immutable return allocation."""
        ...

    def get_by_id(
        self, allocation_id: int
    ) -> ReturnLotAllocation | None:
        """Return a return allocation by identifier, if it exists."""
        ...

    def list_for_return_item(
        self, item_id: int
    ) -> list[ReturnLotAllocation]:
        """Return one return line's reversals in creation order."""
        ...

    def list_for_sale(self, sale_id: int) -> list[ReturnLotAllocation]:
        """Return every return allocation of a sale in creation order."""
        ...

    def list_for_sale_item_lot_allocation(
        self, sale_allocation_id: int
    ) -> list[ReturnLotAllocation]:
        """Return the reversals of one original FIFO allocation."""
        ...
