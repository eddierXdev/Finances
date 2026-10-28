"""Partial receipt rules and lot-derived purchase quantities."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.domain.entities.currency import Currency
from app.domain.entities.inventory_lot import InventoryLot
from app.domain.entities.purchase import Purchase
from app.domain.entities.purchase_cost import PurchaseCost
from app.domain.entities.purchase_cost_allocation import (
    PurchaseCostAllocation,
)
from app.domain.entities.purchase_item import PurchaseItem
from app.domain.enums.allocation_method import AllocationMethod
from app.domain.enums.purchase_cost_type import PurchaseCostType
from app.domain.enums.purchase_status import PurchaseStatus
from app.domain.exceptions import (
    InvalidInventoryError,
    OverReceiptError,
)
from app.domain.inventory import (
    effective_unit_cost,
    received_quantity,
    receipt_status,
    remaining_quantity,
    validate_receipt,
)
from app.domain.value_objects.money import Money

USD = Currency(code="USD", name="US Dollar", decimal_places=2, id=1)
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
OTHER_ITEM = PurchaseItem(
    purchase=PURCHASE,
    variant_id=8,
    quantity=4,
    unit_price=Money("2", USD),
    id=21,
)


def _lot(item: PurchaseItem, quantity: int, **kwargs) -> InventoryLot:
    values = {
        "purchase_item": item,
        "variant_id": item.variant_id,
        "acquired_quantity": quantity,
        "remaining_quantity": quantity,
        "unit_cost": Money("5", USD),
        "received_at": NOW,
    }
    values.update(kwargs)
    return InventoryLot(**values)


def test_received_quantity_sums_only_lots_of_the_purchase_item() -> None:
    lots = (
        _lot(ITEM, 6),
        _lot(ITEM, 2),
        _lot(OTHER_ITEM, 4),
    )

    assert received_quantity(ITEM, lots) == 8
    assert received_quantity(OTHER_ITEM, lots) == 4
    assert received_quantity(ITEM, ()) == 0


def test_remaining_quantity_is_ordered_minus_received() -> None:
    lots = (_lot(ITEM, 6),)

    assert remaining_quantity(ITEM, lots) == 4
    assert remaining_quantity(ITEM, ()) == 10

    with pytest.raises(InvalidInventoryError):
        remaining_quantity(ITEM, (_lot(ITEM, 11),))


def test_validate_receipt_accepts_up_to_the_remaining_quantity() -> None:
    lots = (_lot(ITEM, 6),)

    validate_receipt(ITEM, lots, 4)

    with pytest.raises(OverReceiptError):
        validate_receipt(ITEM, lots, 5)


def test_validate_receipt_rejects_non_positive_quantities() -> None:
    for quantity in (0, -1, True, "1"):
        with pytest.raises(InvalidInventoryError):
            validate_receipt(ITEM, (), quantity)


def test_receipt_status_reports_partial_and_complete_receipts() -> None:
    partial_lots = (_lot(ITEM, 6),)
    assert (
        receipt_status(PURCHASE, (ITEM, OTHER_ITEM), partial_lots)
        is PurchaseStatus.PARTIALLY_RECEIVED
    )

    complete_lots = (_lot(ITEM, 10), _lot(OTHER_ITEM, 4))
    assert (
        receipt_status(PURCHASE, (ITEM, OTHER_ITEM), complete_lots)
        is PurchaseStatus.RECEIVED
    )


def test_receipt_status_requires_at_least_one_received_unit() -> None:
    with pytest.raises(InvalidInventoryError):
        receipt_status(PURCHASE, (ITEM,), ())

    with pytest.raises(InvalidInventoryError):
        receipt_status(PURCHASE, (), ())


def test_receipt_status_rejects_items_from_another_purchase() -> None:
    other_purchase = Purchase(
        currency=USD,
        purchase_date=NOW,
        status=PurchaseStatus.PENDING,
        id=11,
    )
    foreign_item = PurchaseItem(
        purchase=other_purchase,
        variant_id=9,
        quantity=1,
        unit_price=Money("1", USD),
        id=22,
    )

    with pytest.raises(InvalidInventoryError):
        receipt_status(PURCHASE, (ITEM, foreign_item), (_lot(ITEM, 1),))


def test_effective_unit_cost_includes_allocated_purchase_costs() -> None:
    assert effective_unit_cost(ITEM) == Money("5", USD)

    cost = PurchaseCost(
        purchase=PURCHASE,
        cost_type=PurchaseCostType.SHIPPING,
        amount=Money("10", USD),
        allocation_method=AllocationMethod.BY_QUANTITY,
        id=30,
    )
    allocation = PurchaseCostAllocation(
        purchase_cost=cost,
        purchase_item=ITEM,
        allocated_original_amount=Money("10", USD),
        allocated_purchase_currency_amount=Money("10", USD),
        id=40,
    )

    assert effective_unit_cost(ITEM, (allocation,)) == Money("6", USD)


def test_effective_unit_cost_rounds_to_the_currency_precision() -> None:
    item = PurchaseItem(
        purchase=PURCHASE,
        variant_id=7,
        quantity=3,
        unit_price=Money("3.33", USD),
        id=23,
    )
    cost = PurchaseCost(
        purchase=PURCHASE,
        cost_type=PurchaseCostType.SHIPPING,
        amount=Money("0.01", USD),
        allocation_method=AllocationMethod.BY_QUANTITY,
        id=31,
    )
    allocation = PurchaseCostAllocation(
        purchase_cost=cost,
        purchase_item=item,
        allocated_original_amount=Money("0.01", USD),
        allocated_purchase_currency_amount=Money("0.01", USD),
        id=41,
    )

    # Total is 10.00 USD for 3 units: 3.333... rounds half-up to 3.33.
    assert effective_unit_cost(item, (allocation,)) == Money("3.33", USD)
