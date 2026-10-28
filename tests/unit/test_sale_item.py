"""Sale item quantity, price and discount rules."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.domain.entities.account import Account
from app.domain.entities.currency import Currency
from app.domain.entities.sale import Sale
from app.domain.entities.sale_item import SaleItem
from app.domain.exceptions import (
    InvalidSaleError,
    SaleCurrencyMismatchError,
)
from app.domain.value_objects.money import Money

USD = Currency(code="USD", name="US Dollar", decimal_places=2, id=1)
EUR = Currency(code="EUR", name="Euro", decimal_places=2, id=2)
NOW = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)
SALE = Sale(
    account=Account(name="Cash USD", currency=USD, id=1),
    currency=USD,
    sale_date=NOW,
    id=1,
)


def _item(**kwargs) -> SaleItem:
    values = {
        "sale": SALE,
        "variant_id": 7,
        "quantity": 2,
        "unit_price": Money("10", USD),
    }
    values.update(kwargs)
    return SaleItem(**values)


def test_line_total_subtracts_the_item_discount() -> None:
    assert _item().line_total == Money("20", USD)
    assert _item(discount_amount=Money("3", USD)).line_total == Money(
        "17", USD
    )


def test_quantity_must_be_a_positive_integer() -> None:
    for quantity in (0, -1, True, "2"):
        with pytest.raises(InvalidSaleError):
            _item(quantity=quantity)


def test_unit_price_must_be_non_negative_money_in_sale_currency() -> None:
    with pytest.raises(InvalidSaleError):
        _item(unit_price=Money("-1", USD))
    with pytest.raises(SaleCurrencyMismatchError):
        _item(unit_price=Money("10", EUR))
    with pytest.raises(TypeError):
        _item(unit_price="10")


def test_item_discount_must_not_exceed_the_line_subtotal() -> None:
    with pytest.raises(InvalidSaleError):
        _item(discount_amount=Money("-1", USD))
    with pytest.raises(InvalidSaleError):
        _item(discount_amount=Money("21", USD))
    with pytest.raises(SaleCurrencyMismatchError):
        _item(discount_amount=Money("1", EUR))

    assert _item(
        discount_amount=Money("20", USD)
    ).line_total == Money("0", USD)


def test_variant_must_be_a_positive_integer() -> None:
    for variant_id in (0, -1, True, "7"):
        with pytest.raises(InvalidSaleError):
            _item(variant_id=variant_id)


def test_sale_item_requires_a_sale() -> None:
    with pytest.raises(TypeError):
        _item(sale="sale")


def test_sale_item_id_must_be_a_positive_integer_when_present() -> None:
    assert _item(id=1).id == 1

    for item_id in (0, -1, True, "1"):
        with pytest.raises(ValueError):
            _item(id=item_id)
