"""Supplier return item repository contract."""

from typing import Protocol

from app.domain.entities.supplier_return_item import SupplierReturnItem


class SupplierReturnItemRepository(Protocol):
    """Persistence boundary for supplier return lines."""

    def add(self, item: SupplierReturnItem) -> SupplierReturnItem:
        """Persist one supplier return line."""
        ...

    def get_by_id(self, item_id: int) -> SupplierReturnItem | None:
        """Return a supplier return line by identifier, if it exists."""
        ...

    def list_for_return(
        self, return_id: int
    ) -> list[SupplierReturnItem]:
        """Return one return's lines in creation order."""
        ...

    def list_for_purchase(
        self, purchase_id: int
    ) -> list[SupplierReturnItem]:
        """Return every line belonging to a purchase in creation order."""
        ...
