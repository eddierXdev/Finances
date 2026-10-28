"""Attribute-management use cases."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.entities.attribute import Attribute, AttributeValue
from app.domain.repositories.attribute_repository import AttributeRepository
from app.domain.repositories.attribute_value_repository import (
    AttributeValueRepository,
)


@dataclass(frozen=True, slots=True)
class AttributeSummary:
    """An attribute together with its selectable values."""

    attribute_id: int
    name: str
    values: tuple[AttributeValue, ...]


@dataclass(frozen=True, slots=True)
class CreateAttributeRequest:
    """Input for a reusable attribute."""

    name: str


@dataclass(frozen=True, slots=True)
class CreateAttributeValueRequest:
    """Input for a value belonging to an attribute."""

    attribute_id: int
    value: str


class ListAttributes:
    """Return attributes and their values in display order."""

    def __init__(
        self,
        attributes: AttributeRepository,
        attribute_values: AttributeValueRepository,
    ) -> None:
        self._attributes = attributes
        self._attribute_values = attribute_values

    def execute(self) -> tuple[AttributeSummary, ...]:
        rows: list[AttributeSummary] = []
        for attribute in self._attributes.list_all():
            if attribute.id is None:
                raise RuntimeError("Stored attribute has no identifier.")
            rows.append(
                AttributeSummary(
                    attribute_id=attribute.id,
                    name=attribute.name,
                    values=tuple(
                        self._attribute_values.list_for_attribute(
                            attribute.id
                        )
                    ),
                )
            )
        return tuple(rows)


class CreateAttribute:
    """Create a reusable variant dimension."""

    def __init__(self, attributes: AttributeRepository) -> None:
        self._attributes = attributes

    def execute(self, request: CreateAttributeRequest) -> Attribute:
        return self._attributes.add(Attribute(name=request.name))


class CreateAttributeValue:
    """Create a value for an existing attribute."""

    def __init__(self, attribute_values: AttributeValueRepository) -> None:
        self._attribute_values = attribute_values

    def execute(
        self, request: CreateAttributeValueRequest
    ) -> AttributeValue:
        return self._attribute_values.add(
            AttributeValue(
                attribute_id=request.attribute_id,
                value=request.value,
            )
        )


__all__ = [
    "AttributeSummary",
    "CreateAttribute",
    "CreateAttributeRequest",
    "CreateAttributeValue",
    "CreateAttributeValueRequest",
    "ListAttributes",
]
