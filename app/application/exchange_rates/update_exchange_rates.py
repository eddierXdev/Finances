"""Fetch exchange rates, persist observations and fall back to stored rates."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.application.exchange_rates.provider import (
    ExchangeRateProvider,
    ExchangeRateProviderError,
)
from app.application.exchange_rates.quote import (
    ExchangeRateQuote,
    build_quote,
)
from app.domain.entities.exchange_rate import ExchangeRate
from app.domain.exceptions import ExchangeRateNotFoundError
from app.domain.repositories.exchange_rate_repository import (
    ExchangeRateRepository,
)


@dataclass(frozen=True, slots=True)
class ExchangeRatePair:
    """A currency pair to refresh."""

    base_code: str
    quote_code: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "base_code", _normalize_code(self.base_code, "Base")
        )
        object.__setattr__(
            self, "quote_code", _normalize_code(self.quote_code, "Quote")
        )


@dataclass(frozen=True, slots=True)
class UpdateExchangeRatesRequest:
    """Input for refreshing one or more exchange-rate pairs."""

    pairs: Sequence[ExchangeRatePair]
    max_age: timedelta | None = None
    allow_stale: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "pairs", tuple(self.pairs))


class UpdateExchangeRates:
    """Refresh rates through a provider and persist successful observations.

    A provider failure never prevents using a locally stored rate. When no
    stored fallback exists, the use case raises ``ExchangeRateNotFoundError`` so
    the caller can request manual input instead of inventing a rate.
    """

    def __init__(
        self,
        exchange_rates: ExchangeRateRepository,
        provider: ExchangeRateProvider,
        *,
        freshness: timedelta = timedelta(hours=24),
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if freshness <= timedelta(0):
            raise ValueError("freshness must be greater than zero.")
        self._exchange_rates = exchange_rates
        self._provider = provider
        self._freshness = freshness
        self._clock = clock or (lambda: datetime.now(UTC))

    def execute(
        self, request: UpdateExchangeRatesRequest
    ) -> list[ExchangeRateQuote]:
        max_age = request.max_age or self._freshness
        return [
            self._update_pair(pair, max_age, request.allow_stale)
            for pair in request.pairs
        ]

    def _update_pair(
        self,
        pair: ExchangeRatePair,
        max_age: timedelta,
        allow_stale: bool,
    ) -> ExchangeRateQuote:
        provider_error: str | None = None
        fetched: ExchangeRate | None = None

        try:
            fetched = self._provider.fetch_rate(
                pair.base_code, pair.quote_code
            )
        except ExchangeRateProviderError as exc:
            provider_error = str(exc)

        if fetched is not None:
            if not self._pair_matches(fetched, pair):
                provider_error = (
                    "Provider returned a rate for a different currency pair."
                )
                fetched = None

        if fetched is not None:
            stored = (
                fetched
                if fetched.id is not None
                else self._exchange_rates.add(fetched)
            )
            return build_quote(
                stored,
                now=self._clock(),
                max_age=max_age,
                allow_stale=allow_stale,
            )

        stored = self._exchange_rates.get_latest(
            pair.base_code, pair.quote_code
        )
        if stored is None:
            detail = (
                f" Provider error: {provider_error}."
                if provider_error
                else " The provider returned no rate."
            )
            raise ExchangeRateNotFoundError(
                f"No exchange rate is available for "
                f"{pair.base_code}/{pair.quote_code}.{detail} "
                "Enter a manual rate."
            )

        return build_quote(
            stored,
            now=self._clock(),
            max_age=max_age,
            allow_stale=allow_stale,
            provider_error=provider_error
            or "Provider returned no rate; using the stored rate.",
        )

    @staticmethod
    def _pair_matches(
        fetched: ExchangeRate, pair: ExchangeRatePair
    ) -> bool:
        return (
            fetched.base_currency.code == pair.base_code
            and fetched.quote_currency.code == pair.quote_code
        )


def _normalize_code(code: str, label: str) -> str:
    if not isinstance(code, str) or not code.strip():
        raise ValueError(f"{label} currency code is required.")
    return code.strip().upper()
