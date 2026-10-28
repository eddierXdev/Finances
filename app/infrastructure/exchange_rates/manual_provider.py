"""Local manual exchange-rate provider."""

from __future__ import annotations

from app.domain.entities.exchange_rate import ExchangeRate
from app.domain.enums.exchange_rate_source import ExchangeRateSource
from app.domain.repositories.exchange_rate_repository import (
    ExchangeRateRepository,
)


class ManualRateProvider:
    """Return the latest stored manual rate without using the network."""

    source = ExchangeRateSource.MANUAL

    def __init__(self, exchange_rates: ExchangeRateRepository) -> None:
        self._exchange_rates = exchange_rates

    def fetch_rate(
        self, base_code: str, quote_code: str
    ) -> ExchangeRate | None:
        return self._exchange_rates.get_latest_by_source(
            base_code, quote_code, ExchangeRateSource.MANUAL
        )
