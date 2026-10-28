"""Supplier repository contract."""

from typing import Protocol

from app.domain.entities.supplier import Supplier


class SupplierRepository(Protocol):
    """Persistence boundary for suppliers."""

    def add(self, supplier: Supplier) -> Supplier:
        """Persist a supplier and return it with its identifier."""
        ...

    def save(self, supplier: Supplier) -> Supplier:
        """Update supplier data without deleting history."""
        ...

    def get_by_id(self, supplier_id: int) -> Supplier | None:
        """Return a supplier by identifier, if it exists."""
        ...

    def list_all(self, *, include_inactive: bool = False) -> list[Supplier]:
        """Return suppliers, optionally including inactive ones."""
        ...
