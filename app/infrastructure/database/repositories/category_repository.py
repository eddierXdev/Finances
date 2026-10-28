"""SQLAlchemy category repository."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.category import Category
from app.infrastructure.database.models import CategoryModel
from app.infrastructure.database.repositories.mapping import category_to_domain


class SqlAlchemyCategoryRepository:
    """Category persistence using SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, category: Category) -> Category:
        model = CategoryModel(
            name=category.name,
            description=category.description,
        )
        self._session.add(model)
        self._session.flush()
        return category_to_domain(model)

    def get_by_id(self, category_id: int) -> Category | None:
        model = self._session.get(CategoryModel, category_id)
        return category_to_domain(model) if model is not None else None

    def list_all(self) -> list[Category]:
        statement = select(CategoryModel).order_by(CategoryModel.name)
        return [
            category_to_domain(model)
            for model in self._session.scalars(statement)
        ]
