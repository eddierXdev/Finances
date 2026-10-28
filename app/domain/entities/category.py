"""Product category entity."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.value_objects.text_rules import optional_text, required_text


@dataclass(frozen=True, slots=True)
class Category:
    """A non-destructive classification for products."""

    name: str
    description: str | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", required_text(self.name, "Category name"))
        object.__setattr__(
            self,
            "description",
            optional_text(self.description, "Category description"),
        )
        _validate_optional_id(self.id, "Category id")


def _validate_optional_id(value: int | None, field_name: str) -> None:
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer.")
