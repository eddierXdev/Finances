"""Exchange-rate application use cases."""

from app.application.exchange_rates.provider import (
    ExchangeRateProvider,
    ExchangeRateProviderError,
)
from app.application.exchange_rates.quote import ExchangeRateQuote
from app.application.exchange_rates.resolve_exchange_rate import (
    ResolveExchangeRate,
    ResolveExchangeRateRequest,
)
from app.application.exchange_rates.set_manual_exchange_rate import (
    SetManualExchangeRate,
    SetManualExchangeRateRequest,
)
from app.application.exchange_rates.update_exchange_rates import (
    ExchangeRatePair,
    UpdateExchangeRates,
    UpdateExchangeRatesRequest,
)

__all__ = [
    "ExchangeRatePair",
    "ExchangeRateProvider",
    "ExchangeRateProviderError",
    "ExchangeRateQuote",
    "ResolveExchangeRate",
    "ResolveExchangeRateRequest",
    "SetManualExchangeRate",
    "SetManualExchangeRateRequest",
    "UpdateExchangeRates",
    "UpdateExchangeRatesRequest",
]
