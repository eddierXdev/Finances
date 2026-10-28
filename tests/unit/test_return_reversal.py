"""Partial FIFO reversal planning for customer returns."""

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
from app.domain.enums.return_condition import ReturnCondition
from app.domain.exceptions import (
    ExcessReturnError,
    InvalidCustomerReturnError,
)
from app.domain.returns import ReturnLine, plan_return_allocations
from app.domain.value_objects.money import Money

USD = Currency(code="USD", name="US Dollar", decimal_places=2, id=1)
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
    quantity=3,
    unit_price=Money("10", USD),
    id=20,
)
PURCHASE = Purchase(currency=USD, purchase_date=NOW, id=30)
PURCHASE_ITEM = PurchaseItem(
    purchase=PURCHASE,
    variant_id=7,
    quantity=10,
    unit_price=Money("5", USD),
    id=40,
)
LOT_A = InventoryLot(
    purchase_item=PURCHASE_ITEM,
    variant_id=7,
    acquired_quantity=10,
    remaining_quantity=4,
    unit_cost=Money("5", USD),
    received_at=NOW,
    id=50,
)
LOT_B = InventoryLot(
    purchase_item=PURCHASE_ITEM,
    variant_id=7,
    acquired_quantity=10,
    remaining_quantity=4,
    unit_cost=Money("7", USD),
    received_at=NOW,
    id=51,
)
ALLOCATION_A = SaleItemLotAllocation(
    sale_item=ITEM,
    inventory_lot=LOT_A,
    quantity=2,
    unit_cost_snapshot=Money("5", USD),
    id=60,
)
ALLOCATION_B = SaleItemLotAllocation(
    sale_item=ITEM,
    inventory_lot=LOT_B,
    quantity=1,
    unit_cost_snapshot=Money("7", USD),
    id=61,
)


def _plan(
    allocations=(ALLOCATION_A, ALLOCATION_B),
    previously_reversed=None,
    lines=(ReturnLine(1, ReturnCondition.SELLABLE),),
):
    return plan_return_allocations(
        ITEM,
        allocations,
        previously_reversed or {},
        lines,
    )


def test_partial_return_reverses_the_most_recent_allocation_first() -> None:
    planned = _plan()

    assert len(planned) == 1
    assert planned[0].allocation is ALLOCATION_B
    assert planned[0].quantity == 1
    assert planned[0].condition is ReturnCondition.SELLABLE


def test_return_spanning_allocations_continues_backwards() -> None:
    planned = _plan(lines=(ReturnLine(2, ReturnCondition.SELLABLE),))

    assert [
        (entry.allocation.id, entry.quantity) for entry in planned
    ] == [(61, 1), (60, 1)]


def test_previously_reversed_quantity_is_skipped() -> None:
    planned = _plan(
        previously_reversed={ALLOCATION_B.id: 1},
        lines=(ReturnLine(1, ReturnCondition.SELLABLE),),
    )

    assert [(entry.allocation.id, entry.quantity) for entry in planned] == [
        (60, 1)
    ]


def test_multiple_return_lines_keep_their_conditions() -> None:
    planned = _plan(
        lines=(
            ReturnLine(1, ReturnCondition.SELLABLE),
            ReturnLine(1, ReturnCondition.DAMAGED),
        )
    )

    assert [
        (entry.allocation.id, entry.quantity, entry.condition)
        for entry in planned
    ] == [
        (61, 1, ReturnCondition.SELLABLE),
        (60, 1, ReturnCondition.DAMAGED),
    ]


def test_allocation_input_order_does_not_change_reversal_order() -> None:
    planned = _plan(allocations=(ALLOCATION_B, ALLOCATION_A))

    assert planned[0].allocation is ALLOCATION_B


def test_excess_return_is_rejected() -> None:
    with pytest.raises(ExcessReturnError):
        _plan(lines=(ReturnLine(4, ReturnCondition.SELLABLE),))

    with pytest.raises(ExcessReturnError):
        _plan(
            previously_reversed={ALLOCATION_B.id: 1},
            lines=(ReturnLine(3, ReturnCondition.SELLABLE),),
        )


def test_allocation_totals_must_match_the_sale_item_quantity() -> None:
    with pytest.raises(InvalidCustomerReturnError):
        _plan(allocations=(ALLOCATION_A,))


def test_previously_reversed_quantities_must_be_valid() -> None:
    with pytest.raises(InvalidCustomerReturnError):
        _plan(previously_reversed={ALLOCATION_A.id: -1})
    with pytest.raises(InvalidCustomerReturnError):
        _plan(previously_reversed={ALLOCATION_A.id: 3})
    with pytest.raises(InvalidCustomerReturnError):
        _plan(previously_reversed={999: 1})


def test_return_lines_must_be_valid() -> None:
    with pytest.raises(InvalidCustomerReturnError):
        _plan(lines=(ReturnLine(0, ReturnCondition.SELLABLE),))
    with pytest.raises(TypeError):
        _plan(lines=(ReturnLine(1, "SELLABLE"),))


def test_unpersisted_rows_are_rejected() -> None:
    unpersisted_item = SaleItem(
        sale=SALE,
        variant_id=7,
        quantity=3,
        unit_price=Money("10", USD),
    )
    unpersisted_allocation = SaleItemLotAllocation(
        sale_item=ITEM,
        inventory_lot=LOT_A,
        quantity=2,
        unit_cost_snapshot=Money("5", USD),
    )

    with pytest.raises(InvalidCustomerReturnError):
        plan_return_allocations(
            unpersisted_item,
            (ALLOCATION_A, ALLOCATION_B),
            {},
            (ReturnLine(1, ReturnCondition.SELLABLE),),
        )
    with pytest.raises(InvalidCustomerReturnError):
        plan_return_allocations(
            ITEM,
            (unpersisted_allocation, ALLOCATION_B),
            {},
            (ReturnLine(1, ReturnCondition.SELLABLE),),
        )
