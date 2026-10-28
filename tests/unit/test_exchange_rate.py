"""Exchange-rate domain tests."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.domain.entities.currency import Currency
from app.domain.entities.exchange_rate import ExchangeRate
from app.domain.enums.exchange_rate_source import ExchangeRateSource
from app.domain.exceptions import (
    CurrencyMismatchError,
    InvalidExchangeRateError,
)
from app.domain.value_objects.money import Money

USD = Currency(code="USD", name="US Dollar", decimal_places=2)
CUP = Currency(code="CUP", name="Cuban Peso", decimal_places=2)
TIMESTAMP = datetime(2026, 10, 20, 14, 30, tzinfo=UTC)


def make_rate(
    rate: Decimal | int | str = Decimal("320.50"),
    *,
    base: Currency = USD,
    quote: Currency = CUP,
) -> ExchangeRate:
    return ExchangeRate(
        base_currency=base,
        quote_currency=quote,
        rate=rate,
        source=ExchangeRateSource.MANUAL,
        rate_timestamp=TIMESTAMP,
    )


def test_valid_manual_rate_preserves_exact_rate() -> None:
    rate = make_rate(Decimal("320.123456789012"))

    assert rate.rate == Decimal("320.123456789012")
    assert rate.source is ExchangeRateSource.MANUAL
    assert rate.rate_timestamp == TIMESTAMP
    assert rate.notes is None
    assert rate.id is None


@pytest.mark.parametrize("rate", [0, -1, "NaN", "Infinity"])
def test_invalid_rates_are_rejected(rate: Decimal | int | str) -> None:
    with pytest.raises((InvalidExchangeRateError, ValueError)):
        make_rate(rate)


def test_base_and_quote_currencies_must_differ() -> None:
    with pytest.raises(InvalidExchangeRateError):
        make_rate(base=USD, quote=USD)


def test_rate_rejects_float_input() -> None:
    with pytest.raises(TypeError):
        make_rate(320.5)  # type: ignore[arg-type]


def test_timestamp_must_be_timezone_aware() -> None:
    with pytest.raises(InvalidExchangeRateError):
        ExchangeRate(
            base_currency=USD,
            quote_currency=CUP,
            rate=Decimal("320.50"),
            source=ExchangeRateSource.MANUAL,
            rate_timestamp=datetime(2026, 10, 20, 14, 30),
        )


def test_timestamp_is_normalized_to_utc() -> None:
    local_time = datetime(
        2026,
        10,
        20,
        10,
        30,
        tzinfo=timezone(timedelta(hours=-4)),
    )

    rate = ExchangeRate(
        base_currency=USD,
        quote_currency=CUP,
        rate=Decimal("320.50"),
        source=ExchangeRateSource.MANUAL,
        rate_timestamp=local_time,
    )

    assert rate.rate_timestamp == datetime(2026, 10, 20, 14, 30, tzinfo=UTC)
    assert rate.rate_timestamp.tzinfo is UTC


def test_source_must_be_an_enum_member() -> None:
    with pytest.raises(TypeError):
        ExchangeRate(
            base_currency=USD,
            quote_currency=CUP,
            rate=Decimal("320.50"),
            source="MANUAL",  # type: ignore[arg-type]
            rate_timestamp=TIMESTAMP,
        )


def test_exchange_rate_is_immutable() -> None:
    rate = make_rate()

    with pytest.raises(FrozenInstanceError):
        rate.rate = Decimal("1")  # type: ignore[misc]


def test_notes_are_trimmed() -> None:
    rate = ExchangeRate(
        base_currency=USD,
        quote_currency=CUP,
        rate=Decimal("320.50"),
        source=ExchangeRateSource.MANUAL,
        rate_timestamp=TIMESTAMP,
        notes="  street rate  ",
    )

    assert rate.notes == "street rate"


def test_convert_uses_base_currency_and_quote_precision() -> None:
    rate = make_rate(Decimal("320.50"))

    converted = rate.convert(Money("10.00", USD))

    assert converted == Money("3205.00", CUP)
    assert converted.currency.code == "CUP"


def test_convert_rejects_amount_in_another_currency() -> None:
    rate = make_rate()

    with pytest.raises(CurrencyMismatchError):
        rate.convert(Money("10.00", CUP))


def test_conversion_rounds_to_quote_currency_precision() -> None:
    rate = make_rate(Decimal("0.333"))

    converted = rate.convert(Money("1.00", USD))

    assert converted == Money("0.33", CUP)
