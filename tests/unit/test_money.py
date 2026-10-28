"""Money arithmetic and currency mismatch tests."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.domain.entities.currency import Currency
from app.domain.exceptions import CurrencyMismatchError
from app.domain.value_objects.money import Money

USD = Currency(code="USD", name="US Dollar", decimal_places=2)
CUP = Currency(code="CUP", name="Cuban Peso", decimal_places=2)


def test_money_rounds_half_up_to_currency_precision() -> None:
    assert Money("1.005", USD).amount == Decimal("1.01")
    assert Money("1.004", USD).amount == Decimal("1.00")
    assert Money("10", USD).amount == Decimal("10.00")


def test_money_rejects_float_input() -> None:
    with pytest.raises(TypeError):
        Money(10.5, USD)  # type: ignore[arg-type]


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity"])
def test_money_rejects_non_finite_values(value: str) -> None:
    with pytest.raises(ValueError):
        Money(value, USD)


def test_money_addition_and_subtraction_use_same_currency() -> None:
    assert Money("10.00", USD) + Money("2.50", USD) == Money("12.50", USD)
    assert Money("10.00", USD) - Money("2.50", USD) == Money("7.50", USD)


def test_money_rejects_currency_mismatch_in_arithmetic() -> None:
    with pytest.raises(CurrencyMismatchError):
        Money("10.00", USD) + Money("10.00", CUP)

    with pytest.raises(CurrencyMismatchError):
        Money("10.00", USD) - Money("10.00", CUP)


def test_money_rejects_currency_mismatch_in_comparisons() -> None:
    with pytest.raises(CurrencyMismatchError):
        _ = Money("10.00", USD) < Money("10.00", CUP)


def test_money_multiplication_accepts_decimal_and_string_factors() -> None:
    money = Money("10.00", USD)

    assert money * Decimal("1.5") == Money("15.00", USD)
    assert money * 2 == Money("20.00", USD)
    assert money * "0.5" == Money("5.00", USD)
    assert 3 * money == Money("30.00", USD)


def test_money_multiplication_rejects_float_factor() -> None:
    with pytest.raises(TypeError):
        Money("10.00", USD) * 1.5  # type: ignore[operator]


def test_money_division() -> None:
    assert Money("10.00", USD) / 4 == Money("2.50", USD)
    assert Money("10.00", USD) / Decimal("2") == Money("5.00", USD)


def test_money_division_by_zero_is_rejected() -> None:
    with pytest.raises(ZeroDivisionError):
        Money("10.00", USD) / 0


def test_money_equality_uses_currency_code() -> None:
    same_currency_other_instance = Currency(
        code="USD",
        name="United States Dollar",
        decimal_places=2,
    )

    assert Money("10.00", USD) == Money("10.00", same_currency_other_instance)
    assert hash(Money("10.00", USD)) == hash(
        Money("10.00", same_currency_other_instance)
    )


def test_money_comparison_and_sign_helpers() -> None:
    assert Money("5.00", USD) < Money("10.00", USD)
    assert Money("10.00", USD) > Money("5.00", USD)
    assert Money.zero(USD).is_zero
    assert Money("1.00", USD).is_positive
    assert Money("-1.00", USD).is_negative
    assert -Money("5.00", USD) == Money("-5.00", USD)
    assert abs(Money("-5.00", USD)) == Money("5.00", USD)


def test_money_string_representation_uses_currency_precision() -> None:
    assert str(Money("10", USD)) == "10.00 USD"
    assert repr(Money("10", USD)) == "Money(Decimal('10.00'), 'USD')"
