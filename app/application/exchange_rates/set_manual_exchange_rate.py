"""Store a manual exchange rate."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from app.domain.entities.currency import Currency
from app.domain.entities.exchange_rate import ExchangeRate
from app.domain.enums.exchange_rate_source import ExchangeRateSource
from app.domain.exceptions import CurrencyNotFoundError
from app.domain.repositories.currency_repository import CurrencyRepository
from app.domain.repositories.exchange_rate_repository import (
    ExchangeRateRepository,
)


@dataclass(frozen=True, slots=True)
class SetManualExchangeRateRequest:
    """Input for a manual exchange rate."""

    base_code: str
    quote_code: str
    rate: Decimal | int | str
    rate_timestamp: datetime | None = None
    notes: str | None = None


class SetManualExchangeRate:
    """Create an immutable manual rate record."""

    def __init__(
        self,
        currencies: CurrencyRepository,
        exchange_rates: ExchangeRateRepository,
        *,
        clock=None,
    ) -> None:
        self._currencies = currencies
        self._exchange_rates = exchange_rates
        self._clock = clock or (lambda: datetime.now(UTC))

    def execute(self, request: SetManualExchangeRateRequest) -> ExchangeRate:
        base = _require_currency(
            self._currencies, request.base_code, "Base"
        )
        quote = _require_currency(
            self._currencies, request.quote_code, "Quote"
        )
        rate = ExchangeRate(
            base_currency=base,
            quote_currency=quote,
            rate=request.rate,
            source=ExchangeRateSource.MANUAL,
            rate_timestamp=request.rate_timestamp or self._clock(),
            notes=request.notes,
        )
        return self._exchange_rates.add(rate)


def _require_currency(
    repository: CurrencyRepository, code: str, label: str
) -> Currency:
    if not isinstance(code, str) or not code.strip():
        raise ValueError(f"{label} currency code is required.")

    currency = repository.get_by_code(code)
    if currency is None:
        raise CurrencyNotFoundError(
            f"Currency {code.strip().upper()} is not registered."
        )
    return currency
