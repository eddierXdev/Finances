"""Product entity tests."""

from __future__ import annotations

import pytest

from app.domain.entities.currency import Currency
from app.domain.entities.product import Product
from app.domain.value_objects.money import Money

USD = Currency(code="USD", name="US Dollar", decimal_places=2)


def test_product_normalizes_text_and_defaults_to_active() -> None:
    product = Product(
        name="  T-Shirt  ",
        category_id=1,
        description="  Cotton shirt  ",
        brand="  Example  ",
        default_selling_price=Money("19.99", USD),
    )

    assert product.name == "T-Shirt"
    assert product.description == "Cotton shirt"
    assert product.brand == "Example"
    assert product.default_selling_price == Money("19.99", USD)
    assert product.is_active is True
    assert product.id is None


def test_product_name_is_required() -> None:
    with pytest.raises(ValueError):
        Product(name="   ")


def test_product_default_selling_price_cannot_be_negative() -> None:
    with pytest.raises(ValueError):
        Product(name="T-Shirt", default_selling_price=Money("-1.00", USD))


def test_product_default_selling_price_must_be_money() -> None:
    with pytest.raises(TypeError):
        Product(name="T-Shirt", default_selling_price="10.00")  # type: ignore[arg-type]


@pytest.mark.parametrize("category_id", [0, -1])
def test_category_id_must_be_positive(category_id: int) -> None:
    with pytest.raises(ValueError):
        Product(name="T-Shirt", category_id=category_id)


def test_deactivate_and_activate_return_new_states() -> None:
    product = Product(name="T-Shirt")

    inactive = product.deactivate()

    assert inactive.is_active is False
    assert product.is_active is True
    assert inactive.id == product.id
    assert inactive.activate().is_active is True
