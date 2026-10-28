"""Attribute and attribute-value entities."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.value_objects.text_rules import required_text


@dataclass(frozen=True, slots=True)
class Attribute:
    """A reusable variant dimension, such as color or size."""

    name: str
    id: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", required_text(self.name, "Attribute name"))
        if self.id is not None:
            if (
                isinstance(self.id, bool)
                or not isinstance(self.id, int)
                or self.id <= 0
            ):
                raise ValueError("Attribute id must be a positive integer.")


@dataclass(frozen=True, slots=True)
class AttributeValue:
    """A concrete value belonging to an attribute."""

    attribute_id: int
    value: str
    id: int | None = None

    def __post_init__(self) -> None:
        if (
            isinstance(self.attribute_id, bool)
            or not isinstance(self.attribute_id, int)
            or self.attribute_id <= 0
        ):
            raise ValueError(
                "AttributeValue attribute_id must be a positive integer."
            )

        object.__setattr__(
            self, "value", required_text(self.value, "AttributeValue value")
        )

        if self.id is not None:
            if (
                isinstance(self.id, bool)
                or not isinstance(self.id, int)
                or self.id <= 0
            ):
                raise ValueError("AttributeValue id must be a positive integer.")
