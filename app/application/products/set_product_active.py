"""Product activation use case."""

from __future__ import annotations

from app.domain.entities.product import Product
from app.domain.exceptions import ProductNotFoundError
from app.domain.repositories.product_repository import ProductRepository


class SetProductActive:
    """Activate or deactivate a product without deleting it."""

    def __init__(self, products: ProductRepository) -> None:
        self._products = products

    def execute(self, product_id: int, *, is_active: bool) -> Product:
        if not isinstance(is_active, bool):
            raise TypeError("is_active must be a boolean.")

        existing = self._products.get_by_id(product_id)
        if existing is None:
            raise ProductNotFoundError(
                f"Product {product_id} does not exist."
            )

        updated = existing.activate() if is_active else existing.deactivate()
        return self._products.save(updated)
