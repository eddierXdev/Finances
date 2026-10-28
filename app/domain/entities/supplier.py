"""Supplier entity."""

from __future__ import annotations

from dataclasses import dataclass, replace

from app.domain.value_objects.text_rules import optional_text, required_text


@dataclass(frozen=True, slots=True)
class Supplier:
    """A vendor or platform from which purchases are made."""

    name: str
    supplier_type: str | None = None
    website: str | None = None
    contact: str | None = None
    notes: str | None = None
    is_active: bool = True
    id: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "name", required_text(self.name, "Supplier name")
        )
        object.__setattr__(
            self,
            "supplier_type",
            optional_text(self.supplier_type, "Supplier supplier_type"),
        )
        object.__setattr__(
            self, "website", optional_text(self.website, "Supplier website")
        )
        object.__setattr__(
            self, "contact", optional_text(self.contact, "Supplier contact")
        )
        object.__setattr__(
            self, "notes", optional_text(self.notes, "Supplier notes")
        )

        if not isinstance(self.is_active, bool):
            raise TypeError("Supplier is_active must be a boolean.")

        if self.id is not None:
            if (
                isinstance(self.id, bool)
                or not isinstance(self.id, int)
                or self.id <= 0
            ):
                raise ValueError("Supplier id must be a positive integer.")

    def deactivate(self) -> Supplier:
        """Return an inactive copy; the supplier is never deleted."""
        return replace(self, is_active=False)

    def activate(self) -> Supplier:
        """Return an active copy."""
        return replace(self, is_active=True)
