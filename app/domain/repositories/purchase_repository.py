"""Purchase repository contract."""

from typing import Protocol

from app.domain.entities.purchase import Purchase


class PurchaseRepository(Protocol):
    """Persistence boundary for purchases."""

    def add(self, purchase: Purchase) -> Purchase:
        """Persist a purchase."""
        ...

    def save(self, purchase: Purchase) -> Purchase:
        """Update mutable purchase fields; the currency is immutable."""
        ...

    def get_by_id(self, purchase_id: int) -> Purchase | None:
        """Return a purchase by identifier, if it exists."""
        ...

    def list_all(self) -> list[Purchase]:
        """Return purchases, newest first."""
        ...

    def list_by_supplier(self, supplier_id: int) -> list[Purchase]:
        """Return a supplier's purchases, newest first."""
        ...
