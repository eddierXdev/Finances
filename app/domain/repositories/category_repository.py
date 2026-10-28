"""Category repository contract."""

from typing import Protocol

from app.domain.entities.category import Category


class CategoryRepository(Protocol):
    """Persistence boundary for categories."""

    def add(self, category: Category) -> Category:
        """Persist a category and return it with its identifier."""
        ...

    def get_by_id(self, category_id: int) -> Category | None:
        """Return a category by identifier, if it exists."""
        ...

    def list_all(self) -> list[Category]:
        """Return all categories ordered by name."""
        ...
