"""Update-product use case."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.entities.product import Product
from app.domain.exceptions import ProductNotFoundError
from app.domain.repositories.product_repository import ProductRepository
from app.domain.value_objects.money import Money


@dataclass(frozen=True, slots=True)
class UpdateProductRequest:
    """Editable product fields. Activation is changed separately."""

    product_id: int
    name: str
    category_id: int | None = None
    description: str | None = None
    brand: str | None = None
    default_selling_price: Money | None = None


class UpdateProduct:
    """Update descriptive product data without touching variants or stock."""

    def __init__(self, products: ProductRepository) -> None:
        self._products = products

    def execute(self, request: UpdateProductRequest) -> Product:
        existing = self._products.get_by_id(request.product_id)
        if existing is None:
            raise ProductNotFoundError(
                f"Product {request.product_id} does not exist."
            )

        return self._products.save(
            Product(
                name=request.name,
                category_id=request.category_id,
                description=request.description,
                brand=request.brand,
                default_selling_price=request.default_selling_price,
                is_active=existing.is_active,
                id=existing.id,
            )
        )
