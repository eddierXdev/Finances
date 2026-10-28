"""Purchase cost allocation and effective acquisition cost rules."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import ROUND_FLOOR, ROUND_HALF_UP, Decimal

from app.domain.entities.purchase_cost import PurchaseCost
from app.domain.entities.purchase_cost_allocation import (
    PurchaseCostAllocation,
)
from app.domain.entities.purchase_item import PurchaseItem
from app.domain.enums.allocation_method import AllocationMethod
from app.domain.exceptions import (
    InvalidCostAllocationError,
    InvalidPurchaseError,
)
from app.domain.value_objects.money import Money


def allocate_purchase_cost(
    cost: PurchaseCost,
    items: Sequence[PurchaseItem],
    manual_allocations: Mapping[int, Money] | None = None,
) -> tuple[PurchaseCostAllocation, ...]:
    """Allocate one cost across items, preserving both currency totals.

    ``manual_allocations`` maps purchase-item ids to purchase-currency
    amounts and is required only for ``MANUAL`` allocation.
    """
    if not items:
        raise InvalidCostAllocationError(
            "A purchase cost cannot be allocated without items."
        )
    if cost.id is None:
        raise InvalidCostAllocationError(
            "The purchase cost must be persisted before allocation."
        )

    expected_purchase_id = cost.purchase.id
    if expected_purchase_id is None:
        raise InvalidCostAllocationError(
            "The purchase cost must belong to a persisted purchase."
        )
    for item in items:
        if item.id is None:
            raise InvalidCostAllocationError(
                "Purchase items must be persisted before allocation."
            )
        if item.purchase.id != expected_purchase_id:
            raise InvalidCostAllocationError(
                "Cost and items must belong to the same purchase."
            )

    if cost.allocation_method is AllocationMethod.MANUAL:
        if manual_allocations is None:
            raise InvalidCostAllocationError(
                "MANUAL allocation requires per-item amounts."
            )
        normalized_values = _manual_amounts(cost, items, manual_allocations)
        original_weights = [value.amount for value in normalized_values]
    else:
        if manual_allocations is not None:
            raise InvalidCostAllocationError(
                "Manual amounts are only valid for MANUAL allocation."
            )
        normalized_values = ()
        original_weights = _weights(cost, items)

    original_values = _allocate_money(cost.amount, original_weights)
    if not normalized_values:
        normalized_values = _allocate_money(
            cost.normalized_amount, original_weights
        )

    return tuple(
        PurchaseCostAllocation(
            purchase_cost=cost,
            purchase_item=item,
            allocated_original_amount=original_amount,
            allocated_purchase_currency_amount=normalized_amount,
        )
        for item, original_amount, normalized_amount in zip(
            items, original_values, normalized_values, strict=True
        )
    )


def purchase_total(
    items: Sequence[PurchaseItem],
    costs: Sequence[PurchaseCost] = (),
) -> Money:
    """Return the total purchase cost in the purchase currency."""
    if not items:
        raise InvalidPurchaseError(
            "A purchase requires at least one item."
        )

    purchase_id = items[0].purchase.id
    if purchase_id is None:
        raise InvalidPurchaseError(
            "The purchase must be persisted before totals are calculated."
        )
    currency = items[0].purchase.currency

    total = Money.zero(currency)
    for item in items:
        if item.purchase.id != purchase_id:
            raise InvalidPurchaseError(
                "All items must belong to the same purchase."
            )
        total += item.line_total

    for cost in costs:
        if cost.purchase.id != purchase_id:
            raise InvalidPurchaseError(
                "All costs must belong to the same purchase."
            )
        total += cost.normalized_amount

    return total


def effective_acquisition_costs(
    items: Sequence[PurchaseItem],
    allocations: Sequence[PurchaseCostAllocation],
) -> dict[int, Money]:
    """Return each item's normalized cost including allocated costs."""
    if not items:
        raise InvalidPurchaseError(
            "A purchase requires at least one item."
        )

    totals: dict[int, Money] = {}
    for item in items:
        if item.id is None:
            raise InvalidPurchaseError(
                "Purchase items must be persisted before costing."
            )
        totals[item.id] = item.line_total

    for allocation in allocations:
        item_id = allocation.purchase_item.id
        if item_id is None or item_id not in totals:
            raise InvalidCostAllocationError(
                "Allocation references an item outside the purchase."
            )
        totals[item_id] += allocation.allocated_purchase_currency_amount

    return totals


def _weights(
    cost: PurchaseCost, items: Sequence[PurchaseItem]
) -> list[Decimal]:
    if cost.allocation_method is AllocationMethod.BY_QUANTITY:
        return [Decimal(item.quantity) for item in items]

    if cost.allocation_method is AllocationMethod.BY_VALUE:
        return [item.line_total.amount for item in items]

    if cost.allocation_method is AllocationMethod.BY_WEIGHT:
        weights: list[Decimal] = []
        for item in items:
            if item.weight is None:
                raise InvalidCostAllocationError(
                    "BY_WEIGHT allocation requires a weight on every item."
                )
            weights.append(item.weight)
        return weights

    raise InvalidCostAllocationError(
        f"Unsupported allocation method: {cost.allocation_method.value}."
    )


def _manual_amounts(
    cost: PurchaseCost,
    items: Sequence[PurchaseItem],
    manual_allocations: Mapping[int, Money],
) -> list[Money]:
    item_ids = {item.id for item in items}
    if set(manual_allocations) != item_ids:
        raise InvalidCostAllocationError(
            "MANUAL allocation must provide an amount for every item."
        )

    values: list[Money] = []
    for item in items:
        value = manual_allocations[item.id]
        if not isinstance(value, Money):
            raise TypeError("Manual allocations must be Money values.")
        if value.currency.code != cost.purchase.currency.code:
            raise InvalidCostAllocationError(
                "Manual allocations must use the purchase currency."
            )
        if value.is_negative:
            raise InvalidCostAllocationError(
                "Manual allocations cannot be negative."
            )
        values.append(value)

    manual_total = Money.zero(cost.purchase.currency)
    for value in values:
        manual_total += value
    if manual_total != cost.normalized_amount:
        raise InvalidCostAllocationError(
            "Manual allocations must add up to the normalized cost."
        )
    return values


def _allocate_money(
    total: Money, weights: Sequence[Decimal]
) -> list[Money]:
    """Allocate ``total`` by weights using exact largest-remainder rounding."""
    if not weights:
        raise InvalidCostAllocationError(
            "At least one allocation weight is required."
        )
    if total.is_negative:
        raise InvalidCostAllocationError(
            "Cannot allocate a negative amount."
        )
    if any(weight < 0 for weight in weights):
        raise InvalidCostAllocationError(
            "Allocation weights cannot be negative."
        )
    if total.is_zero:
        return [Money.zero(total.currency) for _ in weights]

    total_weight = sum(weights, Decimal("0"))
    if total_weight <= 0:
        raise InvalidCostAllocationError(
            "Allocation weights must add up to more than zero."
        )

    quantum = Decimal(1).scaleb(-total.currency.decimal_places)
    raw_values = [
        total.amount * weight / total_weight for weight in weights
    ]
    floored_values = [
        value.quantize(quantum, rounding=ROUND_FLOOR)
        for value in raw_values
    ]
    remainders = [
        value - floored
        for value, floored in zip(
            raw_values, floored_values, strict=True
        )
    ]

    allocated = sum(floored_values, Decimal("0"))
    remaining_units = int(
        ((total.amount - allocated) / quantum).to_integral_value(
            rounding=ROUND_HALF_UP
        )
    )
    if remaining_units < 0 or remaining_units > len(weights):
        raise RuntimeError("Allocation rounding produced an invalid state.")

    order = sorted(
        range(len(weights)),
        key=lambda index: (-remainders[index], index),
    )
    for index in order[:remaining_units]:
        floored_values[index] += quantum

    if sum(floored_values, Decimal("0")) != total.amount:
        raise RuntimeError("Allocation did not preserve the exact total.")

    return [
        Money(value, total.currency) for value in floored_values
    ]
