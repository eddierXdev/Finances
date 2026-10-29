"""Application service for the Currency Rates screen."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.application.exchange_rates.set_manual_exchange_rate import (
    SetManualExchangeRate,
    SetManualExchangeRateRequest,
)
from app.application.unit_of_work import UnitOfWorkFactory
from app.domain.entities.currency import Currency
from app.domain.entities.exchange_rate import ExchangeRate
from app.domain.enums.exchange_rate_source import ExchangeRateSource


@dataclass(frozen=True, slots=True)
class ExchangeRateRow:
    """The latest stored observation for one ordered currency pair."""

    exchange_rate_id: int
    base_code: str
    quote_code: str
    rate: str
    source: ExchangeRateSource
    rate_timestamp: datetime
    age: timedelta
    is_stale: bool
    notes: str | None


class ExchangeRateService:
    """Read stored rates and register manual observations."""

    def __init__(
        self,
        unit_of_work: UnitOfWorkFactory,
        *,
        freshness: timedelta = timedelta(hours=24),
        clock=None,
    ) -> None:
        if freshness <= timedelta(0):
            raise ValueError("freshness must be greater than zero.")
        self._unit_of_work = unit_of_work
        self._freshness = freshness
        self._clock = clock or (lambda: datetime.now(UTC))

    def list_currencies(self) -> tuple[Currency, ...]:
        with self._unit_of_work.unit_of_work() as uow:
            return tuple(uow.currencies.list_all(enabled_only=True))

    def list_latest_rates(self) -> tuple[ExchangeRateRow, ...]:
        now = self._clock()
        with self._unit_of_work.unit_of_work() as uow:
            currencies = uow.currencies.list_all(enabled_only=True)
            rows: list[ExchangeRateRow] = []
            for base in currencies:
                for quote in currencies:
                    if base.code == quote.code:
                        continue
                    rate = uow.exchange_rates.get_latest(
                        base.code, quote.code
                    )
                    if rate is None:
                        continue
                    rows.append(self._row(rate, now))
            rows.sort(key=lambda row: (row.base_code, row.quote_code))
            return tuple(rows)

    def list_history(
        self, base_code: str, quote_code: str
    ) -> tuple[ExchangeRateRow, ...]:
        now = self._clock()
        with self._unit_of_work.unit_of_work() as uow:
            rates = uow.exchange_rates.list_for_pair(
                base_code, quote_code
            )
            return tuple(
                self._row(rate, now) for rate in reversed(rates)
            )

    def set_manual(
        self, request: SetManualExchangeRateRequest
    ) -> ExchangeRate:
        with self._unit_of_work.unit_of_work() as uow:
            rate = SetManualExchangeRate(
                uow.currencies, uow.exchange_rates
            ).execute(request)
            uow.commit()
            return rate

    def _row(
        self, rate: ExchangeRate, now: datetime
    ) -> ExchangeRateRow:
        if rate.id is None:
            raise RuntimeError("Persisted exchange rate has no identifier.")
        age = max(now - rate.rate_timestamp, timedelta(0))
        return ExchangeRateRow(
            exchange_rate_id=rate.id,
            base_code=rate.base_currency.code,
            quote_code=rate.quote_currency.code,
            rate=str(rate.rate),
            source=rate.source,
            rate_timestamp=rate.rate_timestamp,
            age=age,
            is_stale=age > self._freshness,
            notes=rate.notes,
        )
