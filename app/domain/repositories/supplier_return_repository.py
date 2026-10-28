"""Supplier return repository contract."""

from typing import Protocol

from app.domain.entities.supplier_return import SupplierReturn


class SupplierReturnRepository(Protocol):
    """Persistence boundary for supplier return headers."""

    def add(self, supplier_return: SupplierReturn) -> SupplierReturn:
        """Persist a supplier return."""
        ...

    def get_by_id(self, return_id: int) -> SupplierReturn | None:
        """Return a supplier return by identifier, if it exists."""
        ...

    def list_all(self) -> list[SupplierReturn]:
        """Return supplier returns, newest first."""
        ...

    def list_for_purchase(
        self, purchase_id: int
    ) -> list[SupplierReturn]:
        """Return the returns of one purchase in creation order."""
        ...
