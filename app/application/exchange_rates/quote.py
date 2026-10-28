"""Exchange-rate quotes with freshness metadata."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from app.domain.entities.currency import Currency
from app.domain.entities.exchange_rate import ExchangeRate
from app.domain.enums.exchange_rate_source import ExchangeRateSource
from app.domain.exceptions import StaleExchangeRateError


@dataclass(frozen=True, slots=True)
class ExchangeRateQuote:
    """A stored rate together with its age and staleness."""

    exchange_rate: ExchangeRate
    is_stale: bool
    age: timedelta
    provider_error: str | None = None

    @property
    def base_code(self) -> str:
        return self.exchange_rate.base_currency.code

    @property
    def quote_code(self) -> str:
        return self.exchange_rate.quote_currency.code

    @property
    def base_currency(self) -> Currency:
        return self.exchange_rate.base_currency

    @property
    def quote_currency(self) -> Currency:
        return self.exchange_rate.quote_currency

    @property
    def rate(self) -> Decimal:
        return self.exchange_rate.rate

    @property
    def source(self) -> ExchangeRateSource:
        return self.exchange_rate.source

    @property
    def rate_timestamp(self) -> datetime:
        return self.exchange_rate.rate_timestamp

    @property
    def is_fresh(self) -> bool:
        return not self.is_stale


def build_quote(
    exchange_rate: ExchangeRate,
    *,
    now: datetime,
    max_age: timedelta,
    allow_stale: bool,
    provider_error: str | None = None,
) -> ExchangeRateQuote:
    """Build a quote and reject stale rates when the caller does not allow them."""
    if not isinstance(exchange_rate, ExchangeRate):
        raise TypeError("build_quote requires an ExchangeRate.")
    if max_age <= timedelta(0):
        raise ValueError("max_age must be greater than zero.")

    age = now - exchange_rate.rate_timestamp
    if age < timedelta(0):
        age = timedelta(0)

    is_stale = age > max_age
    if is_stale and not allow_stale:
        raise StaleExchangeRateError(
            f"Exchange rate {exchange_rate.base_currency.code}/"
            f"{exchange_rate.quote_currency.code} is stale "
            f"(age {age}, maximum {max_age})."
        )

    return ExchangeRateQuote(
        exchange_rate=exchange_rate,
        is_stale=is_stale,
        age=age,
        provider_error=provider_error,
    )
