"""Exact monetary helpers shared by analytics use cases."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import ROUND_HALF_UP, Decimal

from app.domain.entities.currency import Currency
from app.domain.value_objects.money import Money

_PERCENTAGE_QUANTUM = Decimal("0.0001")


def money(amount: Decimal, currency: Currency) -> Money:
    """Wrap a stored decimal amount in its native currency."""
    return Money(amount, currency)


def add_money(totals: dict[str, Money], amount: Money) -> None:
    """Accumulate a monetary value by currency code."""
    current = totals.get(amount.currency.code)
    if current is None:
        totals[amount.currency.code] = amount
    else:
        totals[amount.currency.code] = current + amount


def add_decimal(
    totals: dict[str, Money], amount: Decimal, currency: Currency
) -> None:
    """Accumulate a decimal amount by currency code."""
    add_money(totals, money(amount, currency))


def totals_tuple(totals: Mapping[str, Money]) -> tuple[Money, ...]:
    """Return currency totals in deterministic currency-code order."""
    return tuple(totals[code] for code in sorted(totals))


def zero_totals(currencies: Mapping[str, Currency]) -> dict[str, Money]:
    """Return a zero amount for each supplied currency."""
    return {
        code: Money.zero(currency)
        for code, currency in currencies.items()
    }


def net_totals_map(
    positives: Mapping[str, Money],
    negatives: Mapping[str, Money],
) -> dict[str, Money]:
    """Subtract one per-currency mapping from another without FX."""
    currencies: dict[str, Currency] = {}
    for total in positives.values():
        currencies[total.currency.code] = total.currency
    for total in negatives.values():
        currencies[total.currency.code] = total.currency

    result: dict[str, Money] = {}
    for code, currency in currencies.items():
        result[code] = positives.get(code, Money.zero(currency)) - negatives.get(
            code, Money.zero(currency)
        )
    return result


def net_totals(
    positives: Mapping[str, Money],
    negatives: Mapping[str, Money],
) -> tuple[Money, ...]:
    """Subtract one per-currency mapping from another without FX."""
    return totals_tuple(net_totals_map(positives, negatives))


def percentage(numerator: Money, denominator: Money) -> Decimal | None:
    """Return a percentage, or None when the denominator is zero."""
    if numerator.currency.code != denominator.currency.code:
        raise ValueError("Percentage operands must share a currency.")
    if denominator.amount == 0:
        return None
    return (numerator.amount / denominator.amount * Decimal("100")).quantize(
        _PERCENTAGE_QUANTUM, rounding=ROUND_HALF_UP
    )


def proportional_money(
    amount: Money, numerator: int, denominator: int
) -> Money:
    """Return ``amount * numerator / denominator`` in the same currency."""
    if denominator <= 0:
        raise ValueError("Proportional denominator must be positive.")
    if numerator < 0:
        raise ValueError("Proportional numerator cannot be negative.")
    return amount * Decimal(numerator) / Decimal(denominator)


def allocate_sale_discount(
    line_totals: Mapping[int, Money], discount: Money
) -> dict[int, Money]:
    """Allocate a sale-level discount across items by line-total share.

    The last item absorbs the rounding residual so the shares add exactly to
    the sale discount.
    """
    item_ids = sorted(line_totals)
    if not item_ids:
        return {}
    if discount.amount == 0:
        return {item_id: Money.zero(discount.currency) for item_id in item_ids}

    total = Money.zero(discount.currency)
    for item_id in item_ids:
        total = total + line_totals[item_id]

    if total.amount == 0:
        return {item_id: Money.zero(discount.currency) for item_id in item_ids}

    shares: dict[int, Money] = {}
    allocated = Money.zero(discount.currency)
    for item_id in item_ids[:-1]:
        share = Money(
            discount.amount * line_totals[item_id].amount / total.amount,
            discount.currency,
        )
        shares[item_id] = share
        allocated = allocated + share

    shares[item_ids[-1]] = discount - allocated
    return shares
