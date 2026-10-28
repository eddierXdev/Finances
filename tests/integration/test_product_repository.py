"""Product repository tests against a migrated database."""

from __future__ import annotations

import pytest

from app.domain.entities.category import Category
from app.domain.entities.currency import Currency
from app.domain.entities.product import Product
from app.domain.exceptions import CategoryNotFoundError, CurrencyNotFoundError
from app.domain.value_objects.money import Money
from app.infrastructure.database.repositories import (
    SqlAlchemyCategoryRepository,
    SqlAlchemyCurrencyRepository,
    SqlAlchemyProductRepository,
)


def _usd(db_session) -> Currency:
    currency = SqlAlchemyCurrencyRepository(db_session).get_by_code("USD")
    assert currency is not None
    return currency


def _category(db_session) -> Category:
    return SqlAlchemyCategoryRepository(db_session).add(
        Category(name="Electronics")
    )


def test_product_is_stored_and_queried_with_category_and_price(db_session) -> None:
    category = _category(db_session)
    usd = _usd(db_session)
    repository = SqlAlchemyProductRepository(db_session)

    stored = repository.add(
        Product(
            name="Wireless Mouse",
            category_id=category.id,
            brand="Example",
            default_selling_price=Money("29.99", usd),
        )
    )

    assert stored.id is not None
    fetched = repository.get_by_id(stored.id)
    assert fetched == stored
    assert fetched is not None
    assert fetched.category_id == category.id
    assert fetched.default_selling_price == Money("29.99", usd)


def test_product_can_be_updated_without_changing_its_identity(db_session) -> None:
    repository = SqlAlchemyProductRepository(db_session)
    stored = repository.add(Product(name="Old Name"))

    updated = repository.save(
        Product(id=stored.id, name="New Name", brand="New Brand")
    )

    assert updated.id == stored.id
    assert updated.name == "New Name"
    assert updated.brand == "New Brand"
    assert repository.get_by_id(stored.id) == updated


def test_deactivated_products_are_excluded_from_active_listing(db_session) -> None:
    repository = SqlAlchemyProductRepository(db_session)
    stored = repository.add(Product(name="Discontinued"))

    repository.save(stored.deactivate())

    assert repository.list_all() == []
    inactive_products = repository.list_all(include_inactive=True)
    assert [product.name for product in inactive_products] == ["Discontinued"]
    fetched = repository.get_by_id(stored.id)
    assert fetched is not None
    assert fetched.is_active is False


def test_unknown_category_is_rejected(db_session) -> None:
    repository = SqlAlchemyProductRepository(db_session)

    with pytest.raises(CategoryNotFoundError):
        repository.add(Product(name="Orphan", category_id=999))


def test_unregistered_selling_currency_is_rejected(db_session) -> None:
    repository = SqlAlchemyProductRepository(db_session)
    unknown_currency = Currency(code="XYZ", name="Unknown", decimal_places=2)

    with pytest.raises(CurrencyNotFoundError):
        repository.add(
            Product(
                name="Imported Product",
                default_selling_price=Money("10.00", unknown_currency),
            )
        )
