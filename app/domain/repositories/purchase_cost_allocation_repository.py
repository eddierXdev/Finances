"""Purchase cost allocation repository contract."""

from typing import Protocol

from app.domain.entities.purchase_cost_allocation import (
    PurchaseCostAllocation,
)


class PurchaseCostAllocationRepository(Protocol):
    """Persistence boundary for normalized cost allocations."""

    def add(
        self, allocation: PurchaseCostAllocation
    ) -> PurchaseCostAllocation:
        """Persist one cost allocation."""
        ...

    def list_for_cost(
        self, cost_id: int
    ) -> list[PurchaseCostAllocation]:
        """Return the allocations of one cost."""
        ...

    def list_for_item(
        self, item_id: int
    ) -> list[PurchaseCostAllocation]:
        """Return the allocations assigned to one item."""
        ...

    def list_for_purchase(
        self, purchase_id: int
    ) -> list[PurchaseCostAllocation]:
        """Return every allocation of a purchase."""
        ...
