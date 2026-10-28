"""Product list query for the catalog screen."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.repositories.category_repository import CategoryRepository
from app.domain.repositories.product_repository import ProductRepository
from app.domain.repositories.product_variant_repository import (
    ProductVariantRepository,
)
from app.domain.value_objects.money import Money


@dataclass(frozen=True, slots=True)
class ProductListItem:
    """One row of the product catalog."""

    product_id: int
    name: str
    brand: str | None
    category_id: int | None
    category_name: str | None
    description: str | None
    default_selling_price: Money | None
    variant_count: int
    is_active: bool


class ListProducts:
    """Return catalog products with presentation-ready descriptive data.

    The query only joins descriptive data. It does not calculate stock, FIFO or
    profit; those belong to their own use cases.
    """

    def __init__(
        self,
        products: ProductRepository,
        variants: ProductVariantRepository,
        categories: CategoryRepository,
    ) -> None:
        self._products = products
        self._variants = variants
        self._categories = categories

    def execute(
        self, *, include_inactive: bool = False
    ) -> tuple[ProductListItem, ...]:
        category_names = {
            category.id: category.name
            for category in self._categories.list_all()
            if category.id is not None
        }

        rows: list[ProductListItem] = []
        for product in self._products.list_all(
            include_inactive=include_inactive
        ):
            if product.id is None:
                raise RuntimeError("Stored product has no identifier.")

            rows.append(
                ProductListItem(
                    product_id=product.id,
                    name=product.name,
                    brand=product.brand,
                    category_id=product.category_id,
                    category_name=category_names.get(product.category_id),
                    description=product.description,
                    default_selling_price=product.default_selling_price,
                    variant_count=len(
                        self._variants.list_for_product(product.id)
                    ),
                    is_active=product.is_active,
                )
            )

        return tuple(rows)
