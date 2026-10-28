"""Create-supplier use case."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.entities.supplier import Supplier
from app.domain.repositories.supplier_repository import SupplierRepository


@dataclass(frozen=True, slots=True)
class CreateSupplierRequest:
    """Input for supplier creation."""

    name: str
    supplier_type: str | None = None
    website: str | None = None
    contact: str | None = None
    notes: str | None = None


class CreateSupplier:
    """Create a supplier."""

    def __init__(self, suppliers: SupplierRepository) -> None:
        self._suppliers = suppliers

    def execute(self, request: CreateSupplierRequest) -> Supplier:
        return self._suppliers.add(
            Supplier(
                name=request.name,
                supplier_type=request.supplier_type,
                website=request.website,
                contact=request.contact,
                notes=request.notes,
            )
        )
