"""Exact purchase-cost allocation and effective-cost calculations."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.domain.entities.currency import Currency
from app.domain.entities.exchange_rate import ExchangeRate
from app.domain.entities.purchase import Purchase
from app.domain.entities.purchase_cost import PurchaseCost
from app.domain.entities.purchase_item import PurchaseItem
from app.domain.enums.allocation_method import AllocationMethod
from app.domain.enums.exchange_rate_source import ExchangeRateSource
from app.domain.enums.purchase_cost_type import PurchaseCostType
from app.domain.exceptions import InvalidCostAllocationError
from app.domain.purchase_costing import (
    allocate_purchase_cost,
    effective_acquisition_costs,
    purchase_total,
)
from app.domain.value_objects.money import Money

USD = Currency(code="USD", name="US Dollar", decimal_places=2, id=1)
EUR = Currency(code="EUR", name="Euro", decimal_places=2, id=2)
NOW = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)
PURCHASE = Purchase(currency=USD, purchase_date=NOW, id=10)
EUR_TO_USD = ExchangeRate(
    base_currency=EUR,
    quote_currency=USD,
    rate=Decimal("1.10"),
    source=ExchangeRateSource.MANUAL,
    rate_timestamp=NOW,
    id=1,
)


def _item(
    item_id: int,
    *,
    quantity: int = 1,
    price: str = "10.00",
    weight: str | None = None,
    purchase: Purchase = PURCHASE,
    variant_id: int = 1,
) -> PurchaseItem:
    return PurchaseItem(
        purchase=purchase,
        variant_id=variant_id,
        quantity=quantity,
        unit_price=Money(price, purchase.currency),
        weight=Decimal(weight) if weight is not None else None,
        id=item_id,
    )


def _cost(
    cost_id: int = 1,
    *,
    amount: str = "10.00",
    currency: Currency = USD,
    exchange_rate: ExchangeRate | None = None,
    method: AllocationMethod = AllocationMethod.BY_QUANTITY,
    purchase: Purchase = PURCHASE,
) -> PurchaseCost:
    return PurchaseCost(
        purchase=purchase,
        cost_type=PurchaseCostType.SHIPPING,
        amount=Money(amount, currency),
        allocation_method=method,
        exchange_rate=exchange_rate,
        id=cost_id,
    )


def test_by_quantity_uses_largest_remainder_to_preserve_the_total() -> None:
    items = [
        _item(101, quantity=1),
        _item(102, quantity=2),
        _item(103, quantity=3),
    ]
    cost = _cost(amount="10.00")

    allocations = allocate_purchase_cost(cost, items)

    assert [
        allocation.allocated_purchase_currency_amount for allocation in allocations
    ] == [
        Money("1.67", USD),
        Money("3.33", USD),
        Money("5.00", USD),
    ]
    assert (
        sum(
            (
                allocation.allocated_original_amount
                for allocation in allocations
            ),
            Money.zero(USD),
        )
        == cost.amount
    )


def test_by_value_allocates_in_proportion_to_line_totals() -> None:
    items = [
        _item(101, price="10.00"),
        _item(102, price="20.00"),
        _item(103, price="30.00"),
    ]
    cost = _cost(
        amount="6.00", method=AllocationMethod.BY_VALUE
    )

    allocations = allocate_purchase_cost(cost, items)

    assert [
        allocation.allocated_purchase_currency_amount.amount
        for allocation in allocations
    ] == [Decimal("1.00"), Decimal("2.00"), Decimal("3.00")]


def test_by_weight_allocates_in_proportion_to_weights() -> None:
    items = [
        _item(101, weight="1.0"),
        _item(102, weight="2.0"),
        _item(103, weight="3.0"),
    ]
    cost = _cost(
        amount="6.00", method=AllocationMethod.BY_WEIGHT
    )

    allocations = allocate_purchase_cost(cost, items)

    assert [
        allocation.allocated_purchase_currency_amount.amount
        for allocation in allocations
    ] == [Decimal("1.00"), Decimal("2.00"), Decimal("3.00")]


def test_by_weight_requires_a_weight_on_every_item() -> None:
    items = [_item(101, weight="1.0"), _item(102)]

    with pytest.raises(InvalidCostAllocationError):
        allocate_purchase_cost(
            _cost(method=AllocationMethod.BY_WEIGHT), items
        )


def test_by_value_rejects_free_items() -> None:
    items = [_item(101, price="0.00"), _item(102, price="0.00")]

    with pytest.raises(InvalidCostAllocationError):
        allocate_purchase_cost(
            _cost(method=AllocationMethod.BY_VALUE), items
        )


def test_foreign_cost_preserves_original_and_normalized_totals() -> None:
    items = [_item(101), _item(102)]
    cost = _cost(
        amount="100.00",
        currency=EUR,
        exchange_rate=EUR_TO_USD,
    )

    allocations = allocate_purchase_cost(cost, items)

    assert [
        allocation.allocated_original_amount for allocation in allocations
    ] == [Money("50.00", EUR), Money("50.00", EUR)]
    assert [
        allocation.allocated_purchase_currency_amount
        for allocation in allocations
    ] == [Money("55.00", USD), Money("55.00", USD)]
    assert (
        sum(
            (
                allocation.allocated_original_amount
                for allocation in allocations
            ),
            Money.zero(EUR),
        )
        == cost.amount
    )
    assert (
        sum(
            (
                allocation.allocated_purchase_currency_amount
                for allocation in allocations
            ),
            Money.zero(USD),
        )
        == cost.normalized_amount
    )


def test_manual_allocation_uses_purchase_currency_amounts() -> None:
    items = [_item(101), _item(102)]
    cost = _cost(
        amount="10.00", method=AllocationMethod.MANUAL
    )

    allocations = allocate_purchase_cost(
        cost,
        items,
        {
            101: Money("4.00", USD),
            102: Money("6.00", USD),
        },
    )

    assert [
        allocation.allocated_purchase_currency_amount
        for allocation in allocations
    ] == [Money("4.00", USD), Money("6.00", USD)]
    assert [
        allocation.allocated_original_amount for allocation in allocations
    ] == [Money("4.00", USD), Money("6.00", USD)]


def test_manual_foreign_allocation_derives_original_amounts() -> None:
    items = [_item(101), _item(102)]
    cost = _cost(
        amount="10.00",
        currency=EUR,
        exchange_rate=EUR_TO_USD,
        method=AllocationMethod.MANUAL,
    )

    allocations = allocate_purchase_cost(
        cost,
        items,
        {
            101: Money("3.00", USD),
            102: Money("8.00", USD),
        },
    )

    original_total = sum(
        (
            allocation.allocated_original_amount
            for allocation in allocations
        ),
        Money.zero(EUR),
    )
    normalized_total = sum(
        (
            allocation.allocated_purchase_currency_amount
            for allocation in allocations
        ),
        Money.zero(USD),
    )
    assert original_total == cost.amount
    assert normalized_total == cost.normalized_amount


def test_manual_allocation_requires_every_item_and_the_exact_total() -> None:
    items = [_item(101), _item(102)]
    cost = _cost(
        amount="10.00", method=AllocationMethod.MANUAL
    )

    with pytest.raises(InvalidCostAllocationError):
        allocate_purchase_cost(
            cost, items, {101: Money("10.00", USD)}
        )

    with pytest.raises(InvalidCostAllocationError):
        allocate_purchase_cost(
            cost,
            items,
            {
                101: Money("4.00", USD),
                102: Money("5.00", USD),
            },
        )


def test_manual_allocation_rejects_another_currency() -> None:
    items = [_item(101)]
    cost = _cost(
        amount="10.00", method=AllocationMethod.MANUAL
    )

    with pytest.raises(InvalidCostAllocationError):
        allocate_purchase_cost(
            cost, items, {101: Money("10.00", EUR)}
        )


def test_total_and_effective_costs_include_normalized_costs() -> None:
    items = [_item(101, quantity=2, price="10.00")]
    cost = _cost(
        amount="10.00",
        currency=EUR,
        exchange_rate=EUR_TO_USD,
    )
    allocations = allocate_purchase_cost(cost, items)

    total = purchase_total(items, [cost])
    effective = effective_acquisition_costs(items, allocations)

    assert total == Money("31.00", USD)
    assert effective == {101: Money("31.00", USD)}


def test_allocation_rejects_items_from_another_purchase() -> None:
    other_purchase = Purchase(
        currency=USD, purchase_date=NOW, id=11
    )
    items = [_item(101), _item(102, purchase=other_purchase)]

    with pytest.raises(InvalidCostAllocationError):
        allocate_purchase_cost(_cost(), items)
