"""FIFO allocation snapshot rules."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.domain.entities.account import Account
from app.domain.entities.currency import Currency
from app.domain.entities.inventory_lot import InventoryLot
from app.domain.entities.purchase import Purchase
from app.domain.entities.purchase_item import PurchaseItem
from app.domain.entities.sale import Sale
from app.domain.entities.sale_item import SaleItem
from app.domain.entities.sale_item_lot_allocation import (
    SaleItemLotAllocation,
)
from app.domain.exceptions import InvalidSaleError
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
ITEM = SaleItem(
    sale=SALE,
    variant_id=7,
    quantity=4,
    unit_price=Money("10", USD),
    id=20,
)
PURCHASE = Purchase(
    currency=USD,
    purchase_date=NOW,
    id=10,
)
PURCHASE_ITEM = PurchaseItem(
    purchase=PURCHASE,
    variant_id=7,
    quantity=10,
    unit_price=Money("5", USD),
    id=30,
)
LOT = InventoryLot(
    purchase_item=PURCHASE_ITEM,
    variant_id=7,
    acquired_quantity=10,
    remaining_quantity=4,
    unit_cost=Money("5", USD),
    received_at=NOW,
    id=40,
)


def _allocation(**kwargs) -> SaleItemLotAllocation:
    values = {
        "sale_item": ITEM,
        "inventory_lot": LOT,
        "quantity": 3,
        "unit_cost_snapshot": Money("5", USD),
    }
    values.update(kwargs)
    return SaleItemLotAllocation(**values)


def test_allocation_snapshots_the_lot_cost_for_historical_cogs() -> None:
    allocation = _allocation()

    assert allocation.sale_item is ITEM
    assert allocation.inventory_lot is LOT
    assert allocation.quantity == 3
    assert allocation.unit_cost_snapshot == Money("5", USD)
    assert allocation.cogs == Money("15", USD)


def test_allocation_requires_persisted_sale_item_and_lot() -> None:
    unpersisted_item = SaleItem(
        sale=SALE,
        variant_id=7,
        quantity=4,
        unit_price=Money("10", USD),
    )
    unpersisted_lot = InventoryLot(
        purchase_item=PURCHASE_ITEM,
        variant_id=7,
        acquired_quantity=10,
        remaining_quantity=10,
        unit_cost=Money("5", USD),
        received_at=NOW,
    )

    with pytest.raises(InvalidSaleError):
        _allocation(sale_item=unpersisted_item)
    with pytest.raises(InvalidSaleError):
        _allocation(inventory_lot=unpersisted_lot)
    with pytest.raises(TypeError):
        _allocation(sale_item="item")
    with pytest.raises(TypeError):
        _allocation(inventory_lot="lot")


def test_allocation_variant_must_match_the_sale_item_variant() -> None:
    other_purchase_item = PurchaseItem(
        purchase=PURCHASE,
        variant_id=8,
        quantity=10,
        unit_price=Money("5", USD),
        id=31,
    )
    other_lot = InventoryLot(
        purchase_item=other_purchase_item,
        variant_id=8,
        acquired_quantity=10,
        remaining_quantity=10,
        unit_cost=Money("5", USD),
        received_at=NOW,
        id=41,
    )

    with pytest.raises(InvalidSaleError):
        _allocation(inventory_lot=other_lot)


def test_allocation_quantity_must_be_positive_and_fit_the_lot() -> None:
    for quantity in (0, -1, True, "1"):
        with pytest.raises(InvalidSaleError):
            _allocation(quantity=quantity)

    with pytest.raises(InvalidSaleError):
        _allocation(quantity=11)


def test_unit_cost_snapshot_must_equal_the_immutable_lot_cost() -> None:
    with pytest.raises(TypeError):
        _allocation(unit_cost_snapshot="5")
    with pytest.raises(InvalidSaleError):
        _allocation(unit_cost_snapshot=Money("-1", USD))
    with pytest.raises(InvalidSaleError):
        _allocation(unit_cost_snapshot=Money("6", USD))
    with pytest.raises(InvalidSaleError):
        _allocation(unit_cost_snapshot=Money("5", EUR))


def test_allocation_id_must_be_a_positive_integer_when_present() -> None:
    assert _allocation(id=1).id == 1

    for allocation_id in (0, -1, True, "1"):
        with pytest.raises(ValueError):
            _allocation(id=allocation_id)
