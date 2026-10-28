"""Return lot allocation rules."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.domain.entities.account import Account
from app.domain.entities.currency import Currency
from app.domain.entities.customer_return import CustomerReturn
from app.domain.entities.customer_return_item import CustomerReturnItem
from app.domain.entities.inventory_lot import InventoryLot
from app.domain.entities.purchase import Purchase
from app.domain.entities.purchase_item import PurchaseItem
from app.domain.entities.return_lot_allocation import ReturnLotAllocation
from app.domain.entities.sale import Sale
from app.domain.entities.sale_item import SaleItem
from app.domain.entities.sale_item_lot_allocation import (
    SaleItemLotAllocation,
)
from app.domain.enums.return_condition import ReturnCondition
from app.domain.exceptions import InvalidCustomerReturnError
from app.domain.value_objects.money import Money

USD = Currency(code="USD", name="US Dollar", decimal_places=2, id=1)
EUR = Currency(code="EUR", name="Euro", decimal_places=2, id=2)
NOW = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)
SALE = Sale(
    account=Account(name="Cash USD", currency=USD, id=1),
    currency=USD,
    sale_date=NOW,
    id=10,
)
ITEM = SaleItem(
    sale=SALE,
    variant_id=7,
    quantity=4,
    unit_price=Money("10", USD),
    id=20,
)
OTHER_ITEM = SaleItem(
    sale=SALE,
    variant_id=7,
    quantity=4,
    unit_price=Money("10", USD),
    id=21,
)
PURCHASE = Purchase(currency=USD, purchase_date=NOW, id=30)
PURCHASE_ITEM = PurchaseItem(
    purchase=PURCHASE,
    variant_id=7,
    quantity=10,
    unit_price=Money("5", USD),
    id=40,
)
LOT = InventoryLot(
    purchase_item=PURCHASE_ITEM,
    variant_id=7,
    acquired_quantity=10,
    remaining_quantity=4,
    unit_cost=Money("5", USD),
    received_at=NOW,
    id=50,
)
ORIGINAL = SaleItemLotAllocation(
    sale_item=ITEM,
    inventory_lot=LOT,
    quantity=3,
    unit_cost_snapshot=Money("5", USD),
    id=60,
)
RETURN = CustomerReturn(sale=SALE, return_date=NOW, id=70)
RETURN_ITEM = CustomerReturnItem(
    customer_return=RETURN,
    sale_item=ITEM,
    quantity=3,
    condition=ReturnCondition.SELLABLE,
    id=80,
)


def _allocation(**kwargs) -> ReturnLotAllocation:
    values = {
        "customer_return_item": RETURN_ITEM,
        "sale_item_lot_allocation": ORIGINAL,
        "quantity": 2,
        "unit_cost_snapshot": Money("5", USD),
    }
    values.update(kwargs)
    return ReturnLotAllocation(**values)


def test_return_allocation_preserves_historical_cost_and_lot() -> None:
    allocation = _allocation()

    assert allocation.customer_return_item is RETURN_ITEM
    assert allocation.customer_return_item_id == RETURN_ITEM.id
    assert allocation.sale_item_lot_allocation is ORIGINAL
    assert allocation.sale_item_lot_allocation_id == ORIGINAL.id
    assert allocation.inventory_lot_id == LOT.id
    assert allocation.quantity == 2
    assert allocation.unit_cost_snapshot == Money("5", USD)
    assert allocation.cost == Money("10", USD)
    assert allocation.id is None


def test_return_allocation_requires_persisted_rows() -> None:
    unpersisted_item = CustomerReturnItem(
        customer_return=RETURN,
        sale_item=ITEM,
        quantity=3,
        condition=ReturnCondition.SELLABLE,
    )
    unpersisted_original = SaleItemLotAllocation(
        sale_item=ITEM,
        inventory_lot=LOT,
        quantity=3,
        unit_cost_snapshot=Money("5", USD),
    )

    with pytest.raises(InvalidCustomerReturnError):
        _allocation(customer_return_item=unpersisted_item)
    with pytest.raises(InvalidCustomerReturnError):
        _allocation(sale_item_lot_allocation=unpersisted_original)
    with pytest.raises(TypeError):
        _allocation(customer_return_item="item")
    with pytest.raises(TypeError):
        _allocation(sale_item_lot_allocation="allocation")


def test_return_allocation_must_match_the_original_sale_item() -> None:
    other_original = SaleItemLotAllocation(
        sale_item=OTHER_ITEM,
        inventory_lot=LOT,
        quantity=3,
        unit_cost_snapshot=Money("5", USD),
        id=61,
    )

    with pytest.raises(InvalidCustomerReturnError):
        _allocation(sale_item_lot_allocation=other_original)


def test_return_allocation_quantity_must_be_positive_and_fit_the_original() -> None:
    for quantity in (0, -1, True, "1"):
        with pytest.raises(InvalidCustomerReturnError):
            _allocation(quantity=quantity)

    with pytest.raises(InvalidCustomerReturnError):
        _allocation(quantity=4)


def test_return_allocation_cost_snapshot_must_equal_the_original() -> None:
    with pytest.raises(TypeError):
        _allocation(unit_cost_snapshot="5")
    with pytest.raises(InvalidCustomerReturnError):
        _allocation(unit_cost_snapshot=Money("-1", USD))
    with pytest.raises(InvalidCustomerReturnError):
        _allocation(unit_cost_snapshot=Money("6", USD))
    with pytest.raises(InvalidCustomerReturnError):
        _allocation(unit_cost_snapshot=Money("5", EUR))


def test_return_allocation_id_must_be_a_positive_integer() -> None:
    assert _allocation(id=1).id == 1

    for allocation_id in (0, -1, True, "1"):
        with pytest.raises(ValueError):
            _allocation(id=allocation_id)
