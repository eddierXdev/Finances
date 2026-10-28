"""Exchange rate entity."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from app.domain.entities.currency import Currency
from app.domain.enums.exchange_rate_source import ExchangeRateSource
from app.domain.exceptions import CurrencyMismatchError, InvalidExchangeRateError
from app.domain.value_objects.decimal_rules import to_decimal
from app.domain.value_objects.money import Money


@dataclass(frozen=True, slots=True)
class ExchangeRate:
    """An immutable historical rate: 1 base unit equals ``rate`` quote units."""

    base_currency: Currency
    quote_currency: Currency
    rate: Decimal
    source: ExchangeRateSource
    rate_timestamp: datetime
    notes: str | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.base_currency, Currency) or not isinstance(
            self.quote_currency, Currency
        ):
            raise TypeError("ExchangeRate requires Currency instances.")

        if self.base_currency.code == self.quote_currency.code:
            raise InvalidExchangeRateError(
                "Base and quote currencies must be different."
            )

        rate = to_decimal(self.rate)
        if rate <= 0:
            raise InvalidExchangeRateError(
                "Exchange rate must be greater than zero."
            )
        object.__setattr__(self, "rate", rate)

        if not isinstance(self.source, ExchangeRateSource):
            raise TypeError("ExchangeRate source must be an ExchangeRateSource.")

        if not isinstance(self.rate_timestamp, datetime):
            raise TypeError("ExchangeRate rate_timestamp must be a datetime.")
        if self.rate_timestamp.tzinfo is None or self.rate_timestamp.utcoffset() is None:
            raise InvalidExchangeRateError(
                "ExchangeRate rate_timestamp must be timezone-aware."
            )
        object.__setattr__(
            self, "rate_timestamp", self.rate_timestamp.astimezone(UTC)
        )

        if self.notes is not None:
            if not isinstance(self.notes, str):
                raise TypeError("ExchangeRate notes must be a string or None.")
            object.__setattr__(self, "notes", self.notes.strip() or None)

    def convert(self, amount: Money) -> Money:
        """Convert a base-currency amount into the quote currency."""
        if not isinstance(amount, Money):
            raise TypeError("ExchangeRate can only convert Money values.")
        if amount.currency.code != self.base_currency.code:
            raise CurrencyMismatchError(
                f"Rate {self.base_currency.code}/{self.quote_currency.code} "
                f"cannot convert {amount.currency.code}."
            )
        return Money(amount.amount * self.rate, self.quote_currency)
