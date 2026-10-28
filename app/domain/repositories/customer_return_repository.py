"""Customer return repository contract."""

from typing import Protocol

from app.domain.entities.customer_return import CustomerReturn


class CustomerReturnRepository(Protocol):
    """Persistence boundary for customer return headers."""

    def add(self, customer_return: CustomerReturn) -> CustomerReturn:
        """Persist a customer return."""
        ...

    def get_by_id(self, return_id: int) -> CustomerReturn | None:
        """Return a customer return by identifier, if it exists."""
        ...

    def list_all(self) -> list[CustomerReturn]:
        """Return customer returns, newest first."""
        ...

    def list_for_sale(self, sale_id: int) -> list[CustomerReturn]:
        """Return the returns of one sale in creation order."""
        ...
