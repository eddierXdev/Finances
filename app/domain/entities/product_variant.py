"""Product variant entity."""

from __future__ import annotations

from dataclasses import dataclass, replace

from app.domain.value_objects.text_rules import optional_text


@dataclass(frozen=True, slots=True)
class ProductVariant:
    """A sellable identity of a product.

    Products without explicit variants use one internal default variant with
    no SKU and no variant name.
    """

    product_id: int
    sku: str | None = None
    variant_name: str | None = None
    barcode: str | None = None
    is_active: bool = True
    id: int | None = None

    def __post_init__(self) -> None:
        if (
            isinstance(self.product_id, bool)
            or not isinstance(self.product_id, int)
            or self.product_id <= 0
        ):
            raise ValueError(
                "ProductVariant product_id must be a positive integer."
            )

        object.__setattr__(
            self, "sku", optional_text(self.sku, "ProductVariant sku")
        )
        object.__setattr__(
            self,
            "variant_name",
            optional_text(self.variant_name, "ProductVariant variant_name"),
        )
        object.__setattr__(
            self,
            "barcode",
            optional_text(self.barcode, "ProductVariant barcode"),
        )

        if not isinstance(self.is_active, bool):
            raise TypeError("ProductVariant is_active must be a boolean.")

        if self.id is not None:
            if (
                isinstance(self.id, bool)
                or not isinstance(self.id, int)
                or self.id <= 0
            ):
                raise ValueError("ProductVariant id must be a positive integer.")

    @classmethod
    def default_for(cls, product_id: int) -> ProductVariant:
        """Create the internal variant used when no variants are provided."""
        return cls(product_id=product_id)

    def deactivate(self) -> ProductVariant:
        """Return an inactive copy; the variant is never deleted."""
        return replace(self, is_active=False)

    def activate(self) -> ProductVariant:
        """Return an active copy."""
        return replace(self, is_active=True)
