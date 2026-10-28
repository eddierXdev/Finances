"""Attribute-value repository contract."""

from typing import Protocol

from app.domain.entities.attribute import AttributeValue


class AttributeValueRepository(Protocol):
    """Persistence boundary for attribute values."""

    def add(self, attribute_value: AttributeValue) -> AttributeValue:
        """Persist an attribute value and return it with its identifier."""
        ...

    def get_by_id(self, attribute_value_id: int) -> AttributeValue | None:
        """Return an attribute value by identifier, if it exists."""
        ...

    def list_for_attribute(self, attribute_id: int) -> list[AttributeValue]:
        """Return the values of an attribute ordered by value."""
        ...
