"""Category creation use case."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.entities.category import Category
from app.domain.repositories.category_repository import CategoryRepository


@dataclass(frozen=True, slots=True)
class CreateCategoryRequest:
    """Input for category creation."""

    name: str
    description: str | None = None


class CreateCategory:
    """Create a non-destructive product category."""

    def __init__(self, categories: CategoryRepository) -> None:
        self._categories = categories

    def execute(self, request: CreateCategoryRequest) -> Category:
        return self._categories.add(
            Category(
                name=request.name,
                description=request.description,
            )
        )
