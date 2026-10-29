"""Prepared, read-only chart data for the Dashboard screen.

The desktop chart widgets never query persistence or calculate revenue. This
use case turns the existing analytics records into a small, presentation-ready
time series and chart value collection.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

from app.application.analytics.aggregation import (
    aggregate_sale_items,
    customer_return_revenue,
)
from app.application.analytics.calculations import add_money
from app.application.analytics.conversion import BaseCurrencyConverter
from app.application.analytics.models import AnalyticsFilters, AnalyticsPeriod
from app.application.analytics.ports import AnalyticsRepository
from app.domain.entities.currency import Currency
from app.domain.repositories.exchange_rate_repository import (
    ExchangeRateRepository,
)
from app.domain.value_objects.money import Money

ChartGranularity = Literal["day", "month"]

_DAILY_CHART_LIMIT_DAYS = 120


@dataclass(frozen=True, slots=True)
class SalesEvolutionPoint:
    """Net revenue in the base currency for one chart bucket."""

    period_start: datetime
    revenue: Money


@dataclass(frozen=True, slots=True)
class ChartAmount:
    """A named monetary value used by a comparison chart."""

    key: str
    amount: Money


@dataclass(frozen=True, slots=True)
class ChartQuantity:
    """A named unit count used by a product ranking chart."""

    label: str
    quantity: int


@dataclass(frozen=True, slots=True)
class SalesEvolution:
    """Prepared sales time series and its bucket size."""

    points: tuple[SalesEvolutionPoint, ...]
    granularity: ChartGranularity


@dataclass(frozen=True, slots=True)
class DashboardChartData:
    """All presentation-ready data required by the Dashboard charts."""

    sales_evolution: tuple[SalesEvolutionPoint, ...]
    granularity: ChartGranularity
    revenue_expenses: tuple[ChartAmount, ...]
    top_products: tuple[ChartQuantity, ...]


class GetSalesEvolution:
    """Aggregate non-cancelled sales and customer returns by period bucket."""

    def __init__(
        self,
        analytics: AnalyticsRepository,
        exchange_rates: ExchangeRateRepository,
    ) -> None:
        self._analytics = analytics
        self._exchange_rates = exchange_rates

    def execute(
        self,
        period: AnalyticsPeriod,
        filters: AnalyticsFilters | None = None,
        *,
        as_of: datetime,
        base_currency: Currency,
    ) -> SalesEvolution:
        filters = filters or AnalyticsFilters()
        sale_records = self._analytics.list_sale_allocations(period, filters)
        return_records = self._analytics.list_customer_return_allocations(
            period, filters
        )

        if not sale_records and not return_records:
            return SalesEvolution(points=(), granularity="day")

        totals_by_bucket: dict[datetime, dict[str, Money]] = defaultdict(dict)
        dates: list[datetime] = []

        sale_items, _, _ = aggregate_sale_items(sale_records)
        for item in sale_items:
            sale_date = _as_utc(item.sale_date)
            dates.append(sale_date)
            bucket = _bucket_start(sale_date, "day")
            add_money(totals_by_bucket[bucket], item.net_revenue)

        for record in return_records:
            return_date = _as_utc(record.return_date)
            dates.append(return_date)
            bucket = _bucket_start(return_date, "day")
            add_money(
                totals_by_bucket[bucket],
                -customer_return_revenue(record),
            )

        start = period.start or min(dates)
        end = period.end or max(dates)
        granularity: ChartGranularity = (
            "day"
            if end - start <= timedelta(days=_DAILY_CHART_LIMIT_DAYS)
            else "month"
        )

        if granularity == "month":
            month_totals: dict[datetime, dict[str, Money]] = defaultdict(dict)
            for bucket, currency_totals in totals_by_bucket.items():
                for amount in currency_totals.values():
                    add_money(
                        month_totals[_bucket_start(bucket, "month")],
                        amount,
                    )
            totals_by_bucket = month_totals

        converter = BaseCurrencyConverter(
            self._exchange_rates,
            base_currency,
            as_of,
        )
        points: list[SalesEvolutionPoint] = []
        cursor = _bucket_start(start, granularity)
        last = _bucket_start(end, granularity)
        while cursor <= last:
            currency_totals = totals_by_bucket.get(cursor, {})
            points.append(
                SalesEvolutionPoint(
                    period_start=cursor,
                    revenue=converter.total(currency_totals.values()),
                )
            )
            cursor = _next_bucket(cursor, granularity)

        return SalesEvolution(points=tuple(points), granularity=granularity)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _bucket_start(value: datetime, granularity: ChartGranularity) -> datetime:
    value = _as_utc(value)
    if granularity == "month":
        return datetime(value.year, value.month, 1, tzinfo=UTC)
    return datetime(value.year, value.month, value.day, tzinfo=UTC)


def _next_bucket(
    value: datetime, granularity: ChartGranularity
) -> datetime:
    if granularity == "month":
        if value.month == 12:
            return datetime(value.year + 1, 1, 1, tzinfo=UTC)
        return datetime(value.year, value.month + 1, 1, tzinfo=UTC)
    return value + timedelta(days=1)
