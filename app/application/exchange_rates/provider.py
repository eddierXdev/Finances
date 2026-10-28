"""Exchange-rate provider port."""

from __future__ import annotations

from typing import Protocol

from app.domain.entities.exchange_rate import ExchangeRate
from app.domain.enums.exchange_rate_source import ExchangeRateSource


class ExchangeRateProviderError(Exception):
    """Raised when an external exchange-rate provider cannot supply a rate."""


class ExchangeRateProvider(Protocol):
    """Replaceable source of exchange-rate observations.

    Providers return an unsaved domain rate when they obtain a new observation.
    A provider may return a stored rate (with an identifier) when it is backed by
    local persistence, such as the manual-rate provider.
    """

    @property
    def source(self) -> ExchangeRateSource:
        """Return the source recorded for rates from this provider."""
        ...

    def fetch_rate(
        self, base_code: str, quote_code: str
    ) -> ExchangeRate | None:
        """Return a rate for the pair, or ``None`` when it is unavailable."""
        ...
