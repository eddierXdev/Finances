"""Product-variant repository contract."""

from collections.abc import Iterable
from typing import Protocol

from app.domain.entities.product_variant import ProductVariant


class ProductVariantRepository(Protocol):
    """Persistence boundary for variants and their attribute values."""

    def add(self, variant: ProductVariant) -> ProductVariant:
        """Persist a variant and return it with its identifier."""
        ...

    def save(self, variant: ProductVariant) -> ProductVariant:
        """Update mutable variant fields, including its active state."""
        ...

    def get_by_id(self, variant_id: int) -> ProductVariant | None:
        """Return a variant by identifier, if it exists."""
        ...

    def get_by_sku(self, sku: str) -> ProductVariant | None:
        """Return a variant by SKU, if it exists."""
        ...

    def list_for_product(
        self, product_id: int, *, include_inactive: bool = False
    ) -> list[ProductVariant]:
        """Return variants of a product, oldest first."""
        ...

    def set_attribute_values(
        self, variant_id: int, attribute_value_ids: Iterable[int]
    ) -> None:
        """Replace the variant's assigned attribute values."""
        ...

    def get_attribute_value_ids(self, variant_id: int) -> list[int]:
        """Return the variant's attribute-value identifiers."""
        ...
