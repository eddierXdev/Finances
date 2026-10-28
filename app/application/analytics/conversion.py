"""Explicit base-currency conversion for consolidated analytics."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from app.application.analytics.models import MissingExchangeRate
from app.domain.entities.currency import Currency
from app.domain.repositories.exchange_rate_repository import (
    ExchangeRateRepository,
)
from app.domain.value_objects.money import Money


class BaseCurrencyConverter:
    """Convert native amounts with direct stored rates at a fixed cutoff."""

    def __init__(
        self,
        exchange_rates: ExchangeRateRepository,
        base_currency: Currency,
        as_of: datetime,
    ) -> None:
        if as_of.tzinfo is None or as_of.utcoffset() is None:
            raise ValueError("Conversion cutoff must be timezone-aware.")
        self._exchange_rates = exchange_rates
        self._base_currency = base_currency
        self._as_of = as_of
        self._missing: dict[str, MissingExchangeRate] = {}

    @property
    def base_currency(self) -> Currency:
        return self._base_currency

    @property
    def as_of(self) -> datetime:
        return self._as_of

    @property
    def missing_rates(self) -> tuple[MissingExchangeRate, ...]:
        return tuple(
            self._missing[code] for code in sorted(self._missing)
        )

    @property
    def is_complete(self) -> bool:
        return not self._missing

    def convert(self, amount: Money) -> Money | None:
        if amount.amount == 0:
            return Money.zero(self._base_currency)
        if amount.currency.code == self._base_currency.code:
            return Money(amount.amount, self._base_currency)

        stored = self._exchange_rates.get_latest_at_or_before(
            self._base_currency.code,
            amount.currency.code,
            self._as_of,
        )
        if stored is None:
            self._missing[amount.currency.code] = MissingExchangeRate(
                base_code=self._base_currency.code,
                quote_code=amount.currency.code,
                as_of=self._as_of,
            )
            return None

        return Money(amount.amount / stored.rate, self._base_currency)

    def total(self, amounts: Iterable[Money]) -> Money:
        total = Money.zero(self._base_currency)
        for amount in amounts:
            converted = self.convert(amount)
            if converted is not None:
                total = total + converted
        return total
