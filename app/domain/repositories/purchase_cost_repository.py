"""Purchase cost repository contract."""

from typing import Protocol

from app.domain.entities.purchase_cost import PurchaseCost


class PurchaseCostRepository(Protocol):
    """Persistence boundary for purchase additional costs."""

    def add(self, cost: PurchaseCost) -> PurchaseCost:
        """Persist a purchase cost."""
        ...

    def get_by_id(self, cost_id: int) -> PurchaseCost | None:
        """Return a purchase cost by identifier, if it exists."""
        ...

    def list_for_purchase(self, purchase_id: int) -> list[PurchaseCost]:
        """Return a purchase's costs in creation order."""
        ...
