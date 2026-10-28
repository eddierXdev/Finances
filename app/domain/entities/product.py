"""Product entity."""

from __future__ import annotations

from dataclasses import dataclass, replace

from app.domain.value_objects.money import Money
from app.domain.value_objects.text_rules import optional_text, required_text


@dataclass(frozen=True, slots=True)
class Product:
    """A catalog product.

    Stock is not stored here. Variants hold sellable identities, and inventory
    belongs to the inventory domain.
    """

    name: str
    category_id: int | None = None
    description: str | None = None
    brand: str | None = None
    default_selling_price: Money | None = None
    is_active: bool = True
    id: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", required_text(self.name, "Product name"))
        object.__setattr__(
            self,
            "description",
            optional_text(self.description, "Product description"),
        )
        object.__setattr__(self, "brand", optional_text(self.brand, "Product brand"))

        if self.category_id is not None:
            if (
                isinstance(self.category_id, bool)
                or not isinstance(self.category_id, int)
                or self.category_id <= 0
            ):
                raise ValueError("Product category_id must be a positive integer.")

        if self.default_selling_price is not None:
            if not isinstance(self.default_selling_price, Money):
                raise TypeError(
                    "Product default_selling_price must be Money or None."
                )
            if self.default_selling_price.is_negative:
                raise ValueError(
                    "Product default_selling_price cannot be negative."
                )

        if not isinstance(self.is_active, bool):
            raise TypeError("Product is_active must be a boolean.")

        if self.id is not None:
            if (
                isinstance(self.id, bool)
                or not isinstance(self.id, int)
                or self.id <= 0
            ):
                raise ValueError("Product id must be a positive integer.")

    def deactivate(self) -> Product:
        """Return an inactive copy; the product is never deleted."""
        return replace(self, is_active=False)

    def activate(self) -> Product:
        """Return an active copy."""
        return replace(self, is_active=True)
