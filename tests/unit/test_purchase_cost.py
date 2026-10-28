"""Purchase additional-cost rules."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.domain.entities.currency import Currency
from app.domain.entities.exchange_rate import ExchangeRate
from app.domain.entities.purchase import Purchase
from app.domain.entities.purchase_cost import PurchaseCost
from app.domain.enums.allocation_method import AllocationMethod
from app.domain.enums.exchange_rate_source import ExchangeRateSource
from app.domain.enums.purchase_cost_type import PurchaseCostType
from app.domain.exceptions import InvalidPurchaseError
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


def _cost(
    *,
    amount: Money | None = None,
    exchange_rate: ExchangeRate | None = None,
    description: str | None = None,
) -> PurchaseCost:
    return PurchaseCost(
        purchase=PURCHASE,
        cost_type=PurchaseCostType.SHIPPING,
        amount=amount or Money("10.00", USD),
        allocation_method=AllocationMethod.BY_QUANTITY,
        exchange_rate=exchange_rate,
        description=description,
    )


def test_same_currency_cost_keeps_its_amount() -> None:
    cost = _cost(description="  Courier ")

    assert cost.normalized_amount == Money("10.00", USD)
    assert cost.description == "Courier"


def test_foreign_cost_requires_and_uses_a_historical_rate() -> None:
    cost = _cost(
        amount=Money("10.00", EUR),
        exchange_rate=EUR_TO_USD,
    )

    assert cost.amount == Money("10.00", EUR)
    assert cost.normalized_amount == Money("11.00", USD)


def test_foreign_cost_requires_an_exchange_rate() -> None:
    with pytest.raises(InvalidPurchaseError):
        _cost(amount=Money("10.00", EUR))


def test_same_currency_cost_rejects_an_exchange_rate() -> None:
    with pytest.raises(InvalidPurchaseError):
        _cost(exchange_rate=EUR_TO_USD)


def test_cost_rate_must_convert_cost_currency_to_purchase_currency() -> None:
    reversed_rate = ExchangeRate(
        base_currency=USD,
        quote_currency=EUR,
        rate=Decimal("0.90"),
        source=ExchangeRateSource.MANUAL,
        rate_timestamp=NOW,
        id=2,
    )
    with pytest.raises(InvalidPurchaseError):
        _cost(
            amount=Money("10.00", EUR),
            exchange_rate=reversed_rate,
        )


def test_cost_amount_must_be_positive() -> None:
    with pytest.raises(InvalidPurchaseError):
        _cost(amount=Money("0.00", USD))
