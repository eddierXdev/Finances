"""Purchase item repository contract."""

from typing import Protocol

from app.domain.entities.purchase_item import PurchaseItem


class PurchaseItemRepository(Protocol):
    """Persistence boundary for purchase items."""

    def add(self, item: PurchaseItem) -> PurchaseItem:
        """Persist a purchase item."""
        ...

    def get_by_id(self, item_id: int) -> PurchaseItem | None:
        """Return a purchase item by identifier, if it exists."""
        ...

    def list_for_purchase(self, purchase_id: int) -> list[PurchaseItem]:
        """Return a purchase's items in creation order."""
        ...
