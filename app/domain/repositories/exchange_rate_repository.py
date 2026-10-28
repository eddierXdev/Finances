"""Exchange-rate repository contract."""

from datetime import datetime
from typing import Protocol

from app.domain.entities.exchange_rate import ExchangeRate
from app.domain.enums.exchange_rate_source import ExchangeRateSource


class ExchangeRateRepository(Protocol):
    """Append-only persistence boundary for historical exchange rates."""

    def add(self, exchange_rate: ExchangeRate) -> ExchangeRate:
        """Persist a rate and return it with its assigned identifier."""
        ...

    def get_by_id(self, exchange_rate_id: int) -> ExchangeRate | None:
        """Return a historical rate by identifier, if it exists."""
        ...

    def get_latest(
        self, base_code: str, quote_code: str
    ) -> ExchangeRate | None:
        """Return the newest rate for a currency pair, if any."""
        ...

    def get_latest_at_or_before(
        self,
        base_code: str,
        quote_code: str,
        as_of: datetime,
    ) -> ExchangeRate | None:
        """Return the newest rate at or before ``as_of``, if any."""
        ...

    def get_latest_by_source(
        self,
        base_code: str,
        quote_code: str,
        source: ExchangeRateSource,
    ) -> ExchangeRate | None:
        """Return the newest rate for a pair from one source, if any."""
        ...

    def list_for_pair(
        self, base_code: str, quote_code: str
    ) -> list[ExchangeRate]:
        """Return the rate history for a pair, oldest first."""
        ...
