"""Customer return item rules."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.domain.entities.account import Account
from app.domain.entities.currency import Currency
from app.domain.entities.customer_return import CustomerReturn
from app.domain.entities.customer_return_item import CustomerReturnItem
from app.domain.entities.sale import Sale
from app.domain.entities.sale_item import SaleItem
from app.domain.enums.return_condition import ReturnCondition
from app.domain.exceptions import InvalidCustomerReturnError
from app.domain.value_objects.money import Money

USD = Currency(code="USD", name="US Dollar", decimal_places=2, id=1)
NOW = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)
SALE = Sale(
    account=Account(name="Cash USD", currency=USD, id=1),
    currency=USD,
    sale_date=NOW,
    id=10,
)
OTHER_SALE = Sale(
    account=Account(name="Cash USD", currency=USD, id=1),
    currency=USD,
    sale_date=NOW,
    id=11,
)
RETURN = CustomerReturn(sale=SALE, return_date=NOW, id=5)
ITEM = SaleItem(
    sale=SALE,
    variant_id=7,
    quantity=4,
    unit_price=Money("10", USD),
    id=20,
)


def _item(**kwargs) -> CustomerReturnItem:
    values = {
        "customer_return": RETURN,
        "sale_item": ITEM,
        "quantity": 2,
        "condition": ReturnCondition.SELLABLE,
    }
    values.update(kwargs)
    return CustomerReturnItem(**values)


def test_customer_return_item_records_quantity_and_condition() -> None:
    item = _item()

    assert item.customer_return is RETURN
    assert item.customer_return_id == RETURN.id
    assert item.sale_item is ITEM
    assert item.sale_item_id == ITEM.id
    assert item.quantity == 2
    assert item.condition is ReturnCondition.SELLABLE
    assert item.id is None


def test_customer_return_item_requires_a_persisted_sale_item() -> None:
    unpersisted_item = SaleItem(
        sale=SALE,
        variant_id=7,
        quantity=4,
        unit_price=Money("10", USD),
    )

    with pytest.raises(InvalidCustomerReturnError):
        _item(sale_item=unpersisted_item)
    with pytest.raises(TypeError):
        _item(sale_item="item")


def test_customer_return_item_must_belong_to_the_return_sale() -> None:
    other_item = SaleItem(
        sale=OTHER_SALE,
        variant_id=7,
        quantity=4,
        unit_price=Money("10", USD),
        id=21,
    )

    with pytest.raises(InvalidCustomerReturnError):
        _item(sale_item=other_item)


def test_customer_return_item_quantity_must_be_positive() -> None:
    for quantity in (0, -1, True, "1"):
        with pytest.raises(InvalidCustomerReturnError):
            _item(quantity=quantity)


def test_customer_return_item_condition_must_be_a_return_condition() -> None:
    assert _item(condition=ReturnCondition.DAMAGED).condition is (
        ReturnCondition.DAMAGED
    )

    with pytest.raises(TypeError):
        _item(condition="SELLABLE")


def test_customer_return_item_id_must_be_a_positive_integer() -> None:
    assert _item(id=1).id == 1

    for item_id in (0, -1, True, "1"):
        with pytest.raises(ValueError):
            _item(id=item_id)
