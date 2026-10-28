"""Category repository tests against a migrated database."""

from __future__ import annotations

from app.domain.entities.category import Category
from app.infrastructure.database.repositories import SqlAlchemyCategoryRepository


def test_category_is_stored_and_queried(db_session) -> None:
    repository = SqlAlchemyCategoryRepository(db_session)

    stored = repository.add(Category(name="Electronics", description="Devices"))

    assert stored.id is not None
    assert repository.get_by_id(stored.id) == stored


def test_categories_are_listed_alphabetically(db_session) -> None:
    repository = SqlAlchemyCategoryRepository(db_session)
    repository.add(Category(name="Toys"))
    repository.add(Category(name="Electronics"))

    categories = repository.list_all()

    assert [category.name for category in categories] == ["Electronics", "Toys"]


def test_unknown_category_returns_none(db_session) -> None:
    repository = SqlAlchemyCategoryRepository(db_session)

    assert repository.get_by_id(999) is None
