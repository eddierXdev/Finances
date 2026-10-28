"""Inventory movement sign convention and validation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.domain.entities.currency import Currency
from app.domain.entities.inventory_movement import InventoryMovement
from app.domain.enums.inventory_movement_type import InventoryMovementType
from app.domain.exceptions import InvalidInventoryMovementError
from app.domain.value_objects.money import Money

USD = Currency(code="USD", name="US Dollar", decimal_places=2, id=1)
NOW = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)

POSITIVE_TYPES = (
    InventoryMovementType.PURCHASE_RECEIVED,
    InventoryMovementType.CUSTOMER_RETURN,
    InventoryMovementType.ADJUSTMENT_IN,
)
NEGATIVE_TYPES = (
    InventoryMovementType.SALE,
    InventoryMovementType.SUPPLIER_RETURN,
    InventoryMovementType.ADJUSTMENT_OUT,
    InventoryMovementType.DAMAGED,
    InventoryMovementType.LOST,
)


def _movement(**kwargs) -> InventoryMovement:
    values = {
        "variant_id": 7,
        "movement_type": InventoryMovementType.PURCHASE_RECEIVED,
        "quantity": 5,
        "movement_date": NOW,
    }
    values.update(kwargs)
    return InventoryMovement(**values)


@pytest.mark.parametrize("movement_type", POSITIVE_TYPES)
def test_inflow_types_require_positive_quantities(
    movement_type: InventoryMovementType,
) -> None:
    movement = _movement(movement_type=movement_type, quantity=3)

    assert movement.quantity == 3
    assert movement.movement_type is movement_type


@pytest.mark.parametrize("movement_type", NEGATIVE_TYPES)
def test_outflow_types_require_negative_quantities(
    movement_type: InventoryMovementType,
) -> None:
    movement = _movement(movement_type=movement_type, quantity=-3)

    assert movement.quantity == -3
    assert movement.movement_type is movement_type


@pytest.mark.parametrize("movement_type", POSITIVE_TYPES)
def test_inflow_types_reject_negative_quantities(
    movement_type: InventoryMovementType,
) -> None:
    with pytest.raises(InvalidInventoryMovementError):
        _movement(movement_type=movement_type, quantity=-1)


@pytest.mark.parametrize("movement_type", NEGATIVE_TYPES)
def test_outflow_types_reject_positive_quantities(
    movement_type: InventoryMovementType,
) -> None:
    with pytest.raises(InvalidInventoryMovementError):
        _movement(movement_type=movement_type, quantity=1)


def test_zero_quantity_is_never_a_valid_movement() -> None:
    with pytest.raises(InvalidInventoryMovementError):
        _movement(quantity=0)


def test_quantity_must_be_an_integer_and_movement_type_an_enum() -> None:
    for quantity in (True, "5", 5.0):
        with pytest.raises(InvalidInventoryMovementError):
            _movement(quantity=quantity)

    with pytest.raises(TypeError):
        _movement(movement_type="PURCHASE_RECEIVED")


def test_movement_date_is_normalized_to_utc() -> None:
    local_time = datetime(
        2026, 10, 27, 7, 0, tzinfo=timezone(timedelta(hours=-5))
    )

    movement = _movement(movement_date=local_time)

    assert movement.movement_date == NOW
    assert movement.movement_date.tzinfo is UTC


def test_movement_date_must_be_timezone_aware() -> None:
    with pytest.raises(InvalidInventoryMovementError):
        _movement(movement_date=datetime(2026, 10, 27, 12, 0))


def test_unit_cost_is_optional_but_must_be_non_negative_money() -> None:
    assert _movement(unit_cost=Money("5", USD)).unit_cost == Money("5", USD)
    assert _movement().unit_cost is None

    with pytest.raises(InvalidInventoryMovementError):
        _movement(unit_cost=Money("-1", USD))

    with pytest.raises(TypeError):
        _movement(unit_cost="5")


def test_lot_and_reference_identifiers_must_be_positive_when_present() -> None:
    movement = _movement(
        inventory_lot_id=3,
        reference_type="  PURCHASE  ",
        reference_id=9,
        notes="  First receipt ",
    )

    assert movement.inventory_lot_id == 3
    assert movement.reference_type == "PURCHASE"
    assert movement.reference_id == 9
    assert movement.notes == "First receipt"

    for value in (0, -1, True, "3"):
        with pytest.raises(InvalidInventoryMovementError):
            _movement(inventory_lot_id=value)
        with pytest.raises(InvalidInventoryMovementError):
            _movement(reference_id=value)

    assert _movement(reference_type="   ").reference_type is None


def test_movement_id_must_be_a_positive_integer_when_present() -> None:
    assert _movement(id=1).id == 1

    for movement_id in (0, -1, True, "1"):
        with pytest.raises(ValueError):
            _movement(id=movement_id)
