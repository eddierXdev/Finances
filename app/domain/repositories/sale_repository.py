"""Sale repository contract."""

from typing import Protocol

from app.domain.entities.sale import Sale


class SaleRepository(Protocol):
    """Persistence boundary for sale headers."""

    def add(self, sale: Sale) -> Sale:
        """Persist a sale."""
        ...

    def save(self, sale: Sale) -> Sale:
        """Update a sale's status; header data is immutable."""
        ...

    def get_by_id(self, sale_id: int) -> Sale | None:
        """Return a sale by identifier, if it exists."""
        ...

    def list_all(self) -> list[Sale]:
        """Return sales, newest first."""
        ...

    def list_by_customer(self, customer_id: int) -> list[Sale]:
        """Return a customer's sales, newest first."""
        ...
