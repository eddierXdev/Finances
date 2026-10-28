"""Supplier return line rules."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.domain.entities.account import Account
from app.domain.entities.currency import Currency
from app.domain.entities.inventory_lot import InventoryLot
from app.domain.entities.purchase import Purchase
from app.domain.entities.purchase_item import PurchaseItem
from app.domain.entities.supplier_return import SupplierReturn
from app.domain.entities.supplier_return_item import SupplierReturnItem
from app.domain.enums.purchase_status import PurchaseStatus
from app.domain.exceptions import InvalidSupplierReturnError
from app.domain.value_objects.money import Money

USD = Currency(code="USD", name="US Dollar", decimal_places=2, id=1)
EUR = Currency(code="EUR", name="Euro", decimal_places=2, id=2)
NOW = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)
ACCOUNT = Account(name="Cash USD", currency=USD, id=1)
PURCHASE = Purchase(
    currency=USD,
    purchase_date=NOW,
    supplier_id=99,
    account=ACCOUNT,
    status=PurchaseStatus.RECEIVED,
    id=10,
)
OTHER_PURCHASE = Purchase(
    currency=USD,
    purchase_date=NOW,
    supplier_id=99,
    account=ACCOUNT,
    status=PurchaseStatus.RECEIVED,
    id=11,
)
ITEM = PurchaseItem(
    purchase=PURCHASE,
    variant_id=7,
    quantity=10,
    unit_price=Money("5", USD),
    id=20,
)
OTHER_ITEM = PurchaseItem(
    purchase=OTHER_PURCHASE,
    variant_id=7,
    quantity=5,
    unit_price=Money("5", USD),
    id=21,
)
RETURN = SupplierReturn(
    purchase=PURCHASE,
    return_date=NOW,
    supplier_id=99,
    id=5,
)
LOT = InventoryLot(
    purchase_item=ITEM,
    variant_id=7,
    acquired_quantity=10,
    remaining_quantity=6,
    unit_cost=Money("5.50", USD),
    received_at=NOW,
    id=30,
)
OTHER_LOT = InventoryLot(
    purchase_item=OTHER_ITEM,
    variant_id=7,
    acquired_quantity=5,
    remaining_quantity=5,
    unit_cost=Money("5.50", USD),
    received_at=NOW,
    id=31,
)
UNPERSISTED_LOT = InventoryLot(
    purchase_item=ITEM,
    variant_id=7,
    acquired_quantity=10,
    remaining_quantity=10,
    unit_cost=Money("5.50", USD),
    received_at=NOW,
)


def _item(**kwargs) -> SupplierReturnItem:
    values = {
        "supplier_return": RETURN,
        "purchase_item": ITEM,
        "inventory_lot": LOT,
        "quantity": 2,
        "unit_cost_snapshot": Money("5.50", USD),
    }
    values.update(kwargs)
    return SupplierReturnItem(**values)


def test_supplier_return_item_records_exact_lot_and_historical_cost() -> None:
    item = _item()

    assert item.supplier_return is RETURN
    assert item.supplier_return_id == RETURN.id
    assert item.purchase_item is ITEM
    assert item.purchase_item_id == ITEM.id
    assert item.inventory_lot is LOT
    assert item.inventory_lot_id == LOT.id
    assert item.quantity == 2
    assert item.unit_cost_snapshot == Money("5.50", USD)
    assert item.cost == Money("11.00", USD)
    assert item.id is None


def test_supplier_return_item_requires_persisted_references() -> None:
    unpersisted_item = PurchaseItem(
        purchase=PURCHASE,
        variant_id=7,
        quantity=10,
        unit_price=Money("5", USD),
    )

    with pytest.raises(InvalidSupplierReturnError):
        _item(purchase_item=unpersisted_item)
    with pytest.raises(InvalidSupplierReturnError):
        _item(inventory_lot=UNPERSISTED_LOT)
    with pytest.raises(TypeError):
        _item(purchase_item="item")
    with pytest.raises(TypeError):
        _item(inventory_lot="lot")


def test_supplier_return_item_must_belong_to_the_original_purchase() -> None:
    with pytest.raises(InvalidSupplierReturnError):
        _item(purchase_item=OTHER_ITEM, inventory_lot=OTHER_LOT)


def test_supplier_return_lot_must_belong_to_the_purchase_item() -> None:
    with pytest.raises(InvalidSupplierReturnError):
        _item(inventory_lot=OTHER_LOT)


def test_supplier_return_item_quantity_must_be_positive_and_available() -> None:
    for quantity in (0, -1, True, "1"):
        with pytest.raises(InvalidSupplierReturnError):
            _item(quantity=quantity)

    with pytest.raises(InvalidSupplierReturnError):
        _item(quantity=11)

    # The entity preserves historical data; the use case is responsible for
    # checking the lot's current remaining quantity before writing.
    assert _item(quantity=10).quantity == 10


def test_supplier_return_item_must_preserve_the_lot_unit_cost() -> None:
    with pytest.raises(InvalidSupplierReturnError):
        _item(unit_cost_snapshot=Money("5.00", USD))

    with pytest.raises(InvalidSupplierReturnError):
        _item(unit_cost_snapshot=Money("5.50", EUR))

    with pytest.raises(TypeError):
        _item(unit_cost_snapshot="5.50")


def test_supplier_return_item_id_must_be_a_positive_integer() -> None:
    assert _item(id=1).id == 1

    for item_id in (0, -1, True, "1"):
        with pytest.raises(ValueError):
            _item(id=item_id)
