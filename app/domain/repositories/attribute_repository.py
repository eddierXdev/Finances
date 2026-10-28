"""Attribute repository contract."""

from typing import Protocol

from app.domain.entities.attribute import Attribute


class AttributeRepository(Protocol):
    """Persistence boundary for attributes."""

    def add(self, attribute: Attribute) -> Attribute:
        """Persist an attribute and return it with its identifier."""
        ...

    def get_by_id(self, attribute_id: int) -> Attribute | None:
        """Return an attribute by identifier, if it exists."""
        ...

    def list_all(self) -> list[Attribute]:
        """Return all attributes ordered by name."""
        ...
