"""Purchase item invariants."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.domain.entities.currency import Currency
from app.domain.entities.purchase import Purchase
from app.domain.entities.purchase_item import PurchaseItem
from app.domain.exceptions import PurchaseCurrencyMismatchError
from app.domain.value_objects.money import Money

USD = Currency(code="USD", name="US Dollar", decimal_places=2, id=1)
EUR = Currency(code="EUR", name="Euro", decimal_places=2, id=2)
NOW = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)
PURCHASE = Purchase(currency=USD, purchase_date=NOW, id=10)


def _item(
    *,
    quantity: int = 2,
    unit_price: Money | None = None,
    weight: Decimal | None = None,
) -> PurchaseItem:
    return PurchaseItem(
        purchase=PURCHASE,
        variant_id=5,
        quantity=quantity,
        unit_price=unit_price or Money("10.00", USD),
        weight=weight,
    )


def test_item_computes_its_line_total() -> None:
    item = _item()

    assert item.purchase_id == 10
    assert item.line_total == Money("20.00", USD)
    assert item.weight is None


def test_weight_is_kept_at_six_decimal_places() -> None:
    item = _item(weight=Decimal("1.23456789"))

    assert item.weight == Decimal("1.234568")


@pytest.mark.parametrize("quantity", [0, -1])
def test_quantity_must_be_positive(quantity: int) -> None:
    with pytest.raises(ValueError):
        _item(quantity=quantity)


def test_unit_price_must_be_non_negative_money() -> None:
    with pytest.raises(ValueError):
        _item(unit_price=Money("-0.01", USD))

    with pytest.raises(TypeError):
        _item(unit_price=Decimal("10.00"))


def test_item_currency_must_match_the_purchase() -> None:
    with pytest.raises(PurchaseCurrencyMismatchError):
        _item(unit_price=Money("10.00", EUR))


def test_weight_must_be_positive_when_present() -> None:
    with pytest.raises(ValueError):
        _item(weight=Decimal("0"))
