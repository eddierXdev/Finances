"""Inventory lot entity and quantity rules."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.domain.entities.currency import Currency
from app.domain.entities.inventory_lot import InventoryLot
from app.domain.entities.purchase import Purchase
from app.domain.entities.purchase_item import PurchaseItem
from app.domain.enums.purchase_status import PurchaseStatus
from app.domain.exceptions import (
    InsufficientStockError,
    InvalidInventoryError,
    PurchaseCurrencyMismatchError,
)
from app.domain.value_objects.money import Money

USD = Currency(code="USD", name="US Dollar", decimal_places=2, id=1)
EUR = Currency(code="EUR", name="Euro", decimal_places=2, id=2)
NOW = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)

PURCHASE = Purchase(
    currency=USD,
    purchase_date=NOW,
    status=PurchaseStatus.PENDING,
    id=10,
)
ITEM = PurchaseItem(
    purchase=PURCHASE,
    variant_id=7,
    quantity=10,
    unit_price=Money("5", USD),
    id=20,
)


def _lot(**kwargs) -> InventoryLot:
    values = {
        "purchase_item": ITEM,
        "variant_id": 7,
        "acquired_quantity": 10,
        "remaining_quantity": 10,
        "unit_cost": Money("5", USD),
        "received_at": NOW,
    }
    values.update(kwargs)
    return InventoryLot(**values)


def test_lot_tracks_remaining_quantity_and_cost() -> None:
    lot = _lot()

    assert lot.purchase_item is ITEM
    assert lot.variant_id == 7
    assert lot.acquired_quantity == 10
    assert lot.remaining_quantity == 10
    assert lot.unit_cost == Money("5", USD)
    assert lot.received_at == NOW
    assert lot.is_exhausted is False


def test_lot_requires_a_persisted_purchase_item() -> None:
    unpersisted_item = PurchaseItem(
        purchase=PURCHASE,
        variant_id=7,
        quantity=10,
        unit_price=Money("5", USD),
    )

    with pytest.raises(InvalidInventoryError):
        _lot(purchase_item=unpersisted_item)

    with pytest.raises(TypeError):
        _lot(purchase_item="item")


def test_acquired_quantity_must_be_a_positive_integer() -> None:
    for quantity in (0, -1, True, "10"):
        with pytest.raises(InvalidInventoryError):
            _lot(acquired_quantity=quantity)


def test_remaining_quantity_must_fit_inside_acquired_quantity() -> None:
    for quantity in (-1, 11, True, "10"):
        with pytest.raises(InvalidInventoryError):
            _lot(remaining_quantity=quantity)

    assert _lot(remaining_quantity=0).is_exhausted is True


def test_unit_cost_must_be_non_negative_money_in_purchase_currency() -> None:
    with pytest.raises(InvalidInventoryError):
        _lot(unit_cost=Money("-1", USD))

    with pytest.raises(PurchaseCurrencyMismatchError):
        _lot(unit_cost=Money("5", EUR))

    with pytest.raises(TypeError):
        _lot(unit_cost="5")


def test_variant_must_match_the_purchase_item_variant() -> None:
    with pytest.raises(InvalidInventoryError):
        _lot(variant_id=8)

    for variant_id in (0, -1, True, "7"):
        with pytest.raises(InvalidInventoryError):
            _lot(variant_id=variant_id)


def test_received_at_is_normalized_to_utc() -> None:
    local_time = datetime(
        2026, 10, 27, 7, 0, tzinfo=timezone(timedelta(hours=-5))
    )

    lot = _lot(received_at=local_time)

    assert lot.received_at == NOW
    assert lot.received_at.tzinfo is UTC


def test_received_at_must_be_timezone_aware() -> None:
    with pytest.raises(InvalidInventoryError):
        _lot(received_at=datetime(2026, 10, 27, 12, 0))


def test_consume_returns_a_reduced_copy() -> None:
    lot = _lot()

    consumed = lot.consume(4)

    assert consumed.remaining_quantity == 6
    assert lot.remaining_quantity == 10
    assert consumed.acquired_quantity == 10
    assert consumed.unit_cost == lot.unit_cost


def test_consume_rejects_invalid_or_excessive_quantities() -> None:
    lot = _lot(remaining_quantity=3)

    for quantity in (0, -1, True, "1"):
        with pytest.raises(InvalidInventoryError):
            lot.consume(quantity)

    with pytest.raises(InsufficientStockError):
        lot.consume(4)


def test_restore_returns_an_increased_copy_without_exceeding_acquired() -> None:
    lot = _lot(remaining_quantity=6)

    restored = lot.restore(4)

    assert restored.remaining_quantity == 10
    assert lot.remaining_quantity == 6
    with pytest.raises(InvalidInventoryError):
        restored.restore(1)


def test_restore_rejects_non_positive_quantities() -> None:
    lot = _lot(remaining_quantity=6)

    for quantity in (0, -1, True, "1"):
        with pytest.raises(InvalidInventoryError):
            lot.restore(quantity)


def test_lot_id_must_be_a_positive_integer_when_present() -> None:
    assert _lot(id=1).id == 1

    for lot_id in (0, -1, True, "1"):
        with pytest.raises(ValueError):
            _lot(id=lot_id)
