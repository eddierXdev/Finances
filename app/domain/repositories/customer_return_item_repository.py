"""Customer return item repository contract."""

from typing import Protocol

from app.domain.entities.customer_return_item import CustomerReturnItem


class CustomerReturnItemRepository(Protocol):
    """Persistence boundary for customer return lines."""

    def add(self, item: CustomerReturnItem) -> CustomerReturnItem:
        """Persist one customer return line."""
        ...

    def get_by_id(self, item_id: int) -> CustomerReturnItem | None:
        """Return a customer return line by identifier, if it exists."""
        ...

    def list_for_return(
        self, return_id: int
    ) -> list[CustomerReturnItem]:
        """Return one return's lines in creation order."""
        ...

    def list_for_sale(self, sale_id: int) -> list[CustomerReturnItem]:
        """Return every line belonging to a sale in creation order."""
        ...
