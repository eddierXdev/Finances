"""Resolve the latest stored exchange rate without using the network."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.application.exchange_rates.quote import (
    ExchangeRateQuote,
    build_quote,
)
from app.domain.exceptions import ExchangeRateNotFoundError
from app.domain.repositories.exchange_rate_repository import (
    ExchangeRateRepository,
)


@dataclass(frozen=True, slots=True)
class ResolveExchangeRateRequest:
    """Input for an offline exchange-rate lookup."""

    base_code: str
    quote_code: str
    max_age: timedelta | None = None
    allow_stale: bool = True
    as_of: datetime | None = None


class ResolveExchangeRate:
    """Return the newest stored rate and identify whether it is stale."""

    def __init__(
        self,
        exchange_rates: ExchangeRateRepository,
        *,
        freshness: timedelta = timedelta(hours=24),
        clock=None,
    ) -> None:
        if freshness <= timedelta(0):
            raise ValueError("freshness must be greater than zero.")
        self._exchange_rates = exchange_rates
        self._freshness = freshness
        self._clock = clock or (lambda: datetime.now(UTC))

    def execute(
        self, request: ResolveExchangeRateRequest
    ) -> ExchangeRateQuote:
        base_code = _normalize_code(request.base_code, "Base")
        quote_code = _normalize_code(request.quote_code, "Quote")
        max_age = request.max_age or self._freshness
        as_of = request.as_of
        if as_of is not None:
            if as_of.tzinfo is None or as_of.utcoffset() is None:
                raise ValueError("Exchange-rate as_of must be timezone-aware.")
            as_of = as_of.astimezone(UTC)

        if as_of is None:
            stored = self._exchange_rates.get_latest(base_code, quote_code)
        else:
            stored = self._exchange_rates.get_latest_at_or_before(
                base_code, quote_code, as_of
            )

        if stored is None:
            suffix = (
                f" at or before {as_of.isoformat()}" if as_of else ""
            )
            raise ExchangeRateNotFoundError(
                f"No stored exchange rate is available for "
                f"{base_code}/{quote_code}{suffix}. Enter a manual rate."
            )

        return build_quote(
            stored,
            now=as_of or self._clock(),
            max_age=max_age,
            allow_stale=request.allow_stale,
        )


def _normalize_code(code: str, label: str) -> str:
    if not isinstance(code, str) or not code.strip():
        raise ValueError(f"{label} currency code is required.")
    return code.strip().upper()
