"""Product-variant use cases."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.entities.attribute import AttributeValue
from app.domain.entities.product_variant import ProductVariant
from app.domain.exceptions import VariantNotFoundError
from app.domain.repositories.attribute_repository import AttributeRepository
from app.domain.repositories.attribute_value_repository import (
    AttributeValueRepository,
)
from app.domain.repositories.product_variant_repository import (
    ProductVariantRepository,
)


@dataclass(frozen=True, slots=True)
class VariantListItem:
    """One sellable variant with descriptive attribute labels."""

    variant_id: int
    product_id: int
    sku: str | None
    variant_name: str | None
    barcode: str | None
    is_active: bool
    attribute_value_ids: tuple[int, ...]
    attribute_labels: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CreateVariantRequest:
    """Input for a new product variant."""

    product_id: int
    sku: str | None = None
    variant_name: str | None = None
    barcode: str | None = None
    attribute_value_ids: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class UpdateVariantRequest:
    """Editable variant fields. Activation is changed separately."""

    variant_id: int
    sku: str | None = None
    variant_name: str | None = None
    barcode: str | None = None
    attribute_value_ids: tuple[int, ...] = ()


class ListProductVariants:
    """Return a product's variants with their assigned attribute labels."""

    def __init__(
        self,
        variants: ProductVariantRepository,
        attribute_values: AttributeValueRepository,
        attributes: AttributeRepository,
    ) -> None:
        self._variants = variants
        self._attribute_values = attribute_values
        self._attributes = attributes

    def execute(
        self, product_id: int, *, include_inactive: bool = False
    ) -> tuple[VariantListItem, ...]:
        attribute_names = {
            attribute.id: attribute.name
            for attribute in self._attributes.list_all()
            if attribute.id is not None
        }
        value_cache: dict[int, AttributeValue | None] = {}

        rows: list[VariantListItem] = []
        for variant in self._variants.list_for_product(
            product_id, include_inactive=include_inactive
        ):
            if variant.id is None:
                raise RuntimeError("Stored variant has no identifier.")

            value_ids = tuple(
                self._variants.get_attribute_value_ids(variant.id)
            )
            labels: list[str] = []
            for value_id in value_ids:
                if value_id not in value_cache:
                    value_cache[value_id] = (
                        self._attribute_values.get_by_id(value_id)
                    )
                value = value_cache[value_id]
                if value is None:
                    continue
                attribute_name = attribute_names.get(
                    value.attribute_id, "Attribute"
                )
                labels.append(f"{attribute_name}: {value.value}")

            rows.append(
                VariantListItem(
                    variant_id=variant.id,
                    product_id=variant.product_id,
                    sku=variant.sku,
                    variant_name=variant.variant_name,
                    barcode=variant.barcode,
                    is_active=variant.is_active,
                    attribute_value_ids=value_ids,
                    attribute_labels=tuple(labels),
                )
            )

        return tuple(rows)


class CreateVariant:
    """Create a variant and assign its attribute values atomically."""

    def __init__(self, variants: ProductVariantRepository) -> None:
        self._variants = variants

    def execute(self, request: CreateVariantRequest) -> ProductVariant:
        stored = self._variants.add(
            ProductVariant(
                product_id=request.product_id,
                sku=request.sku,
                variant_name=request.variant_name,
                barcode=request.barcode,
            )
        )
        if stored.id is None:
            raise RuntimeError("Stored variant has no identifier.")

        if request.attribute_value_ids:
            self._variants.set_attribute_values(
                stored.id, request.attribute_value_ids
            )
        return stored


class UpdateVariant:
    """Update descriptive variant data and replace its attribute values."""

    def __init__(self, variants: ProductVariantRepository) -> None:
        self._variants = variants

    def execute(self, request: UpdateVariantRequest) -> ProductVariant:
        existing = self._variants.get_by_id(request.variant_id)
        if existing is None:
            raise VariantNotFoundError(
                f"Variant {request.variant_id} does not exist."
            )

        saved = self._variants.save(
            ProductVariant(
                product_id=existing.product_id,
                sku=request.sku,
                variant_name=request.variant_name,
                barcode=request.barcode,
                is_active=existing.is_active,
                id=existing.id,
            )
        )
        if saved.id is None:
            raise RuntimeError("Stored variant has no identifier.")

        self._variants.set_attribute_values(
            saved.id, request.attribute_value_ids
        )
        return saved


class SetVariantActive:
    """Activate or deactivate a variant without deleting it."""

    def __init__(self, variants: ProductVariantRepository) -> None:
        self._variants = variants

    def execute(self, variant_id: int, *, is_active: bool) -> ProductVariant:
        if not isinstance(is_active, bool):
            raise TypeError("is_active must be a boolean.")

        existing = self._variants.get_by_id(variant_id)
        if existing is None:
            raise VariantNotFoundError(
                f"Variant {variant_id} does not exist."
            )

        updated = existing.activate() if is_active else existing.deactivate()
        return self._variants.save(updated)


__all__ = [
    "CreateVariant",
    "CreateVariantRequest",
    "ListProductVariants",
    "SetVariantActive",
    "UpdateVariant",
    "UpdateVariantRequest",
    "VariantListItem",
]
