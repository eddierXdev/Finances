"""Customer return reversal planning.

Normal inventory costing consumes lots in FIFO order. A customer return is a
reversal of one specific historical sale, so it walks that sale's allocations
backwards: the most recently consumed allocation is reversed first.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from app.domain.entities.sale_item import SaleItem
from app.domain.entities.sale_item_lot_allocation import (
    SaleItemLotAllocation,
)
from app.domain.enums.return_condition import ReturnCondition
from app.domain.exceptions import (
    ExcessReturnError,
    InvalidCustomerReturnError,
)


@dataclass(frozen=True, slots=True)
class ReturnLine:
    """A requested return quantity and its condition."""

    quantity: int
    condition: ReturnCondition


@dataclass(frozen=True, slots=True)
class PlannedReturnAllocation:
    """One original allocation and the quantity reversed from it."""

    allocation: SaleItemLotAllocation
    quantity: int
    condition: ReturnCondition


def plan_return_allocations(
    sale_item: SaleItem,
    allocations: Sequence[SaleItemLotAllocation],
    previously_reversed: Mapping[int, int],
    lines: Sequence[ReturnLine],
) -> tuple[PlannedReturnAllocation, ...]:
    """Plan which historical allocations a return must reverse.

    ``previously_reversed`` maps original allocation ids to quantities already
    reversed by earlier customer returns. The plan never mutates the original
    sale or its allocation snapshots.
    """
    if not isinstance(sale_item, SaleItem):
        raise TypeError("plan_return_allocations requires a SaleItem.")
    if sale_item.id is None:
        raise InvalidCustomerReturnError(
            "Return planning requires a persisted sale item."
        )

    ordered_allocations = _validate_allocations(
        sale_item, allocations
    )
    remaining = _validate_previously_reversed(
        ordered_allocations, previously_reversed
    )
    validated_lines = _validate_lines(lines)

    available = sum(remaining.values())
    requested = sum(line.quantity for line in validated_lines)
    if requested > available:
        raise ExcessReturnError(
            f"Cannot return {requested} units; only {available} units of "
            "this sale item remain returnable."
        )

    planned: list[PlannedReturnAllocation] = []
    for line in validated_lines:
        quantity_left = line.quantity
        for allocation in reversed(ordered_allocations):
            allocation_id = allocation.id
            if allocation_id is None:
                raise InvalidCustomerReturnError(
                    "Return planning requires persisted allocations."
                )
            allocation_remaining = remaining[allocation_id]
            if allocation_remaining == 0:
                continue

            take = min(quantity_left, allocation_remaining)
            planned.append(
                PlannedReturnAllocation(
                    allocation=allocation,
                    quantity=take,
                    condition=line.condition,
                )
            )
            remaining[allocation_id] -= take
            quantity_left -= take
            if quantity_left == 0:
                break

        if quantity_left:
            raise ExcessReturnError(
                "The return exceeds the reversible quantity of this sale "
                "item."
            )

    return tuple(planned)


def _validate_allocations(
    sale_item: SaleItem,
    allocations: Sequence[SaleItemLotAllocation],
) -> tuple[SaleItemLotAllocation, ...]:
    if not allocations:
        raise InvalidCustomerReturnError(
            "Return planning requires the original sale allocations."
        )

    ordered: list[SaleItemLotAllocation] = []
    seen_ids: set[int] = set()
    for allocation in allocations:
        if not isinstance(allocation, SaleItemLotAllocation):
            raise TypeError(
                "Return planning requires SaleItemLotAllocation instances."
            )
        if allocation.id is None:
            raise InvalidCustomerReturnError(
                "Return planning requires persisted allocations."
            )
        if allocation.sale_item.id != sale_item.id:
            raise InvalidCustomerReturnError(
                "Every allocation must belong to the returned sale item."
            )
        if allocation.id in seen_ids:
            raise InvalidCustomerReturnError(
                "Return planning received a duplicate allocation."
            )
        seen_ids.add(allocation.id)
        ordered.append(allocation)

    ordered.sort(key=lambda allocation: allocation.id or 0)
    total_allocated = sum(
        allocation.quantity for allocation in ordered
    )
    if total_allocated != sale_item.quantity:
        raise InvalidCustomerReturnError(
            "The original allocations do not cover the sold quantity."
        )

    return tuple(ordered)


def _validate_previously_reversed(
    allocations: Sequence[SaleItemLotAllocation],
    previously_reversed: Mapping[int, int],
) -> dict[int, int]:
    if not isinstance(previously_reversed, Mapping):
        raise TypeError("previously_reversed must be a mapping.")

    by_id = {
        allocation.id: allocation
        for allocation in allocations
        if allocation.id is not None
    }
    remaining: dict[int, int] = {
        allocation_id: allocation.quantity
        for allocation_id, allocation in by_id.items()
    }

    for allocation_id, quantity in previously_reversed.items():
        if (
            isinstance(allocation_id, bool)
            or not isinstance(allocation_id, int)
            or allocation_id <= 0
        ):
            raise InvalidCustomerReturnError(
                "Previously reversed allocation ids must be positive "
                "integers."
            )
        allocation = by_id.get(allocation_id)
        if allocation is None:
            raise InvalidCustomerReturnError(
                f"Allocation {allocation_id} does not belong to this sale "
                "item."
            )
        if (
            isinstance(quantity, bool)
            or not isinstance(quantity, int)
            or quantity < 0
            or quantity > allocation.quantity
        ):
            raise InvalidCustomerReturnError(
                "Previously reversed quantities must fit their original "
                "allocation."
            )
        remaining[allocation_id] -= quantity

    return remaining


def _validate_lines(
    lines: Sequence[ReturnLine],
) -> tuple[ReturnLine, ...]:
    if not lines:
        raise InvalidCustomerReturnError(
            "A customer return requires at least one item."
        )

    validated: list[ReturnLine] = []
    for line in lines:
        if not isinstance(line, ReturnLine):
            raise TypeError("Return planning requires ReturnLine instances.")
        if (
            isinstance(line.quantity, bool)
            or not isinstance(line.quantity, int)
            or line.quantity <= 0
        ):
            raise InvalidCustomerReturnError(
                "Return line quantities must be positive integers."
            )
        if not isinstance(line.condition, ReturnCondition):
            raise TypeError(
                "Return line conditions must be ReturnCondition instances."
            )
        validated.append(line)

    return tuple(validated)
