"""Create-product use case."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.entities.product import Product
from app.domain.entities.product_variant import ProductVariant
from app.domain.repositories.product_repository import ProductRepository
from app.domain.repositories.product_variant_repository import (
    ProductVariantRepository,
)
from app.domain.value_objects.money import Money


@dataclass(frozen=True, slots=True)
class ProductVariantRequest:
    """Variant data supplied while creating a product."""

    sku: str | None = None
    variant_name: str | None = None
    barcode: str | None = None
    attribute_value_ids: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class CreateProductRequest:
    """Input for product creation."""

    name: str
    category_id: int | None = None
    description: str | None = None
    brand: str | None = None
    default_selling_price: Money | None = None
    variants: tuple[ProductVariantRequest, ...] = ()


class CreateProduct:
    """Create a product and its variants.

    When no variants are supplied, an internal default variant is created.
    The caller must run this use case inside a database transaction so partial
    failures roll back the whole catalog operation.
    """

    def __init__(
        self,
        products: ProductRepository,
        variants: ProductVariantRepository,
    ) -> None:
        self._products = products
        self._variants = variants

    def execute(self, request: CreateProductRequest) -> Product:
        stored_product = self._products.add(
            Product(
                name=request.name,
                category_id=request.category_id,
                description=request.description,
                brand=request.brand,
                default_selling_price=request.default_selling_price,
            )
        )
        if stored_product.id is None:
            raise RuntimeError("Persisted product has no identifier.")

        variant_requests = request.variants or (ProductVariantRequest(),)
        for variant_request in variant_requests:
            stored_variant = self._variants.add(
                ProductVariant(
                    product_id=stored_product.id,
                    sku=variant_request.sku,
                    variant_name=variant_request.variant_name,
                    barcode=variant_request.barcode,
                )
            )
            if variant_request.attribute_value_ids:
                if stored_variant.id is None:
                    raise RuntimeError("Persisted variant has no identifier.")
                self._variants.set_attribute_values(
                    stored_variant.id,
                    variant_request.attribute_value_ids,
                )

        return stored_product
