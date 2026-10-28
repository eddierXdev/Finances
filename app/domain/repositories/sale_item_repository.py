"""Sale item repository contract."""

from typing import Protocol

from app.domain.entities.sale_item import SaleItem


class SaleItemRepository(Protocol):
    """Persistence boundary for sale items."""

    def add(self, item: SaleItem) -> SaleItem:
        """Persist a sale item."""
        ...

    def get_by_id(self, item_id: int) -> SaleItem | None:
        """Return a sale item by identifier, if it exists."""
        ...

    def list_for_sale(self, sale_id: int) -> list[SaleItem]:
        """Return a sale's items in creation order."""
        ...
