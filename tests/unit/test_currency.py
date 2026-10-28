"""Currency domain tests."""

from __future__ import annotations

import pytest

from app.domain.entities.currency import Currency


def test_currency_normalizes_code_name_and_symbol() -> None:
    currency = Currency(
        code=" usd ",
        name=" US Dollar ",
        decimal_places=2,
        symbol=" $ ",
    )

    assert currency.code == "USD"
    assert currency.name == "US Dollar"
    assert currency.symbol == "$"
    assert currency.is_enabled is True
    assert currency.id is None


def test_blank_symbol_becomes_none() -> None:
    currency = Currency(code="MLC", name="Cuban Convertible Currency", decimal_places=2)

    assert currency.symbol is None


@pytest.mark.parametrize("code", ["US", "USDD", "U1D", ""])
def test_invalid_currency_codes_are_rejected(code: str) -> None:
    with pytest.raises(ValueError):
        Currency(code=code, name="Invalid", decimal_places=2)


def test_currency_name_is_required() -> None:
    with pytest.raises(ValueError):
        Currency(code="USD", name="   ", decimal_places=2)


@pytest.mark.parametrize("decimal_places", [-1, 7])
def test_decimal_places_must_be_within_supported_range(decimal_places: int) -> None:
    with pytest.raises(ValueError):
        Currency(code="USD", name="US Dollar", decimal_places=decimal_places)


def test_decimal_places_must_be_an_integer() -> None:
    with pytest.raises(TypeError):
        Currency(code="USD", name="US Dollar", decimal_places=True)  # type: ignore[arg-type]
