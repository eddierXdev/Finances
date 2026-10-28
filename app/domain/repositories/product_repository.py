"""Product repository contract."""

from typing import Protocol

from app.domain.entities.product import Product


class ProductRepository(Protocol):
    """Persistence boundary for products."""

    def add(self, product: Product) -> Product:
        """Persist a product and return it with its identifier."""
        ...

    def save(self, product: Product) -> Product:
        """Update an existing product, including its active state."""
        ...

    def get_by_id(self, product_id: int) -> Product | None:
        """Return a product by identifier, if it exists."""
        ...

    def list_all(self, *, include_inactive: bool = False) -> list[Product]:
        """Return products, optionally including inactive ones."""
        ...
