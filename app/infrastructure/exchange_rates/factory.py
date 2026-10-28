"""Build exchange-rate providers from runtime settings."""

from __future__ import annotations

from app.application.exchange_rates.provider import ExchangeRateProvider
from app.domain.repositories.currency_repository import CurrencyRepository
from app.domain.repositories.exchange_rate_repository import (
    ExchangeRateRepository,
)
from app.infrastructure.config.settings import Settings
from app.infrastructure.exchange_rates.eltoque_provider import ElToqueProvider
from app.infrastructure.exchange_rates.manual_provider import ManualRateProvider


def create_exchange_rate_provider(
    settings: Settings,
    currencies: CurrencyRepository,
    exchange_rates: ExchangeRateRepository,
) -> ExchangeRateProvider:
    """Create the configured provider without making online FX mandatory."""
    provider = settings.fx_provider.strip().upper()

    if provider == "ELTOQUE":
        return ElToqueProvider(
            currencies,
            api_token=settings.eltoque_api_token,
            api_url=settings.eltoque_api_url,
            timeout=settings.eltoque_timeout_seconds,
        )
    if provider == "MANUAL":
        return ManualRateProvider(exchange_rates)

    raise ValueError(f"Unsupported FX provider: {settings.fx_provider!r}.")
