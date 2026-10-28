"""FIFO lot selection rules."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.domain.entities.currency import Currency
from app.domain.entities.inventory_lot import InventoryLot
from app.domain.entities.purchase import Purchase
from app.domain.entities.purchase_item import PurchaseItem
from app.domain.exceptions import (
    InsufficientStockError,
    InvalidInventoryError,
)
from app.domain.fifo import allocate_fifo
from app.domain.value_objects.money import Money

USD = Currency(code="USD", name="US Dollar", decimal_places=2, id=1)
NOW = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)
PURCHASE = Purchase(currency=USD, purchase_date=NOW, id=10)
ITEM = PurchaseItem(
    purchase=PURCHASE,
    variant_id=7,
    quantity=100,
    unit_price=Money("5", USD),
    id=20,
)


def _lot(
    *,
    lot_id: int,
    acquired: int = 10,
    remaining: int | None = None,
    unit_cost: str = "5",
    received_at: datetime = NOW,
) -> InventoryLot:
    return InventoryLot(
        purchase_item=ITEM,
        variant_id=7,
        acquired_quantity=acquired,
        remaining_quantity=acquired if remaining is None else remaining,
        unit_cost=Money(unit_cost, USD),
        received_at=received_at,
        id=lot_id,
    )


def test_one_lot_sale_takes_the_requested_quantity() -> None:
    lot = _lot(lot_id=1)

    takes = allocate_fifo([lot], 4)

    assert len(takes) == 1
    assert takes[0].lot is lot
    assert takes[0].quantity == 4


def test_multi_lot_sale_consumes_oldest_lots_first() -> None:
    older = _lot(lot_id=1, unit_cost="5")
    newer = _lot(lot_id=2, unit_cost="7", received_at=NOW + timedelta(days=1))

    takes = allocate_fifo([newer, older], 12)

    assert [(take.lot.id, take.quantity) for take in takes] == [
        (1, 10),
        (2, 2),
    ]


def test_fifo_uses_lot_id_to_break_received_at_ties() -> None:
    second = _lot(lot_id=2)
    first = _lot(lot_id=1)

    takes = allocate_fifo([second, first], 12)

    assert [(take.lot.id, take.quantity) for take in takes] == [
        (1, 10),
        (2, 2),
    ]


def test_exact_exhaustion_returns_only_the_available_lots() -> None:
    first = _lot(lot_id=1, acquired=3)
    second = _lot(lot_id=2, acquired=2)

    takes = allocate_fifo([first, second], 5)

    assert [(take.lot.id, take.quantity) for take in takes] == [(1, 3), (2, 2)]


def test_exhausted_lots_are_ignored() -> None:
    exhausted = _lot(lot_id=1, remaining=0)
    available = _lot(lot_id=2, acquired=5)

    takes = allocate_fifo([exhausted, available], 5)

    assert [(take.lot.id, take.quantity) for take in takes] == [(2, 5)]


def test_insufficient_stock_is_rejected() -> None:
    with pytest.raises(InsufficientStockError, match="only 4 available"):
        allocate_fifo([_lot(lot_id=1, acquired=4)], 5)


def test_quantity_must_be_a_positive_integer() -> None:
    for quantity in (0, -1, True, "1"):
        with pytest.raises(InvalidInventoryError):
            allocate_fifo([_lot(lot_id=1)], quantity)
