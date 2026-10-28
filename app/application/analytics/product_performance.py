"""Product performance use case."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.application.analytics.aggregation import (
    aggregate_sale_items,
    customer_return_cogs,
    customer_return_revenue,
)
from app.application.analytics.calculations import (
    add_money,
    money,
    percentage,
    proportional_money,
    totals_tuple,
)
from app.application.analytics.models import (
    AnalyticsFilters,
    AnalyticsPeriod,
    ProductPerformance,
    ProductPerformanceReport,
    ProductProfitability,
    SlowMovingProduct,
)
from app.application.analytics.ports import AnalyticsRepository
from app.domain.value_objects.money import Money


class GetProductPerformance:
    """Rank best sellers and profitable products and find slow stock."""

    def __init__(
        self,
        analytics: AnalyticsRepository,
        *,
        slow_moving_days: int = 30,
        clock=None,
    ) -> None:
        if slow_moving_days <= 0:
            raise ValueError("slow_moving_days must be greater than zero.")
        self._analytics = analytics
        self._slow_moving_days = slow_moving_days
        self._clock = clock or (lambda: datetime.now(UTC))

    def execute(
        self,
        period: AnalyticsPeriod,
        filters: AnalyticsFilters | None = None,
        *,
        limit: int = 10,
        slow_moving_days: int | None = None,
    ) -> ProductPerformanceReport:
        if limit <= 0:
            raise ValueError("limit must be greater than zero.")
        threshold_days = (
            slow_moving_days
            if slow_moving_days is not None
            else self._slow_moving_days
        )
        if threshold_days <= 0:
            raise ValueError("slow_moving_days must be greater than zero.")

        filters = filters or AnalyticsFilters()
        sale_records = self._analytics.list_sale_allocations(period, filters)
        return_records = self._analytics.list_customer_return_allocations(
            period, filters
        )
        aggregates, cross_currency_sale_ids, _ = aggregate_sale_items(
            sale_records
        )

        best_sellers: dict[int, dict] = {}
        profitability: dict[tuple[int, str], dict] = {}

        for aggregate in aggregates:
            for allocation in aggregate.allocations:
                revenue_share = proportional_money(
                    aggregate.net_revenue,
                    allocation.allocation_quantity,
                    aggregate.item_quantity,
                )
                cogs = money(
                    allocation.allocation_unit_cost
                    * allocation.allocation_quantity,
                    allocation.cost_currency,
                )
                _add_best_seller(
                    best_sellers,
                    aggregate.product_id,
                    aggregate.product_name,
                    aggregate.category_id,
                    allocation.allocation_quantity,
                    revenue_share,
                )
                if aggregate.sale_id not in cross_currency_sale_ids:
                    _add_profitability(
                        profitability,
                        aggregate.product_id,
                        aggregate.product_name,
                        aggregate.category_id,
                        aggregate.sale_currency,
                        allocation.allocation_quantity,
                        revenue_share,
                        cogs,
                    )

        for record in return_records:
            reversed_revenue = customer_return_revenue(record)
            reversed_cogs = customer_return_cogs(record)
            _add_best_seller(
                best_sellers,
                record.product_id,
                record.product_name,
                record.category_id,
                -record.return_allocation_quantity,
                -reversed_revenue,
            )
            if record.sale_is_same_currency:
                _add_profitability(
                    profitability,
                    record.product_id,
                    record.product_name,
                    record.category_id,
                    record.sale_currency,
                    -record.return_allocation_quantity,
                    -reversed_revenue,
                    -reversed_cogs,
                )

        best = sorted(
            (
                ProductPerformance(
                    product_id=product_id,
                    product_name=entry["product_name"],
                    category_id=entry["category_id"],
                    net_quantity=entry["net_quantity"],
                    revenue=totals_tuple(entry["revenue"]),
                )
                for product_id, entry in best_sellers.items()
            ),
            key=lambda item: (
                -item.net_quantity,
                item.product_name,
                item.product_id,
            ),
        )[:limit]

        profit_entries = [
            ProductProfitability(
                product_id=product_id,
                product_name=entry["product_name"],
                category_id=entry["category_id"],
                currency=entry["currency"],
                net_quantity=entry["net_quantity"],
                revenue=entry["revenue"],
                cogs=entry["cogs"],
                gross_profit=entry["revenue"] - entry["cogs"],
                gross_margin=percentage(
                    entry["revenue"] - entry["cogs"], entry["revenue"]
                ),
            )
            for (product_id, _), entry in profitability.items()
        ]
        profitable: list[ProductProfitability] = []
        for currency_code in sorted(
            {entry.currency.code for entry in profit_entries}
        ):
            same_currency = [
                entry
                for entry in profit_entries
                if entry.currency.code == currency_code
            ]
            same_currency.sort(
                key=lambda item: (
                    -item.gross_profit.amount,
                    -item.net_quantity,
                    item.product_name,
                )
            )
            profitable.extend(same_currency[:limit])

        as_of = period.end_or(self._clock())
        inventory_records = self._analytics.list_inventory_lots(
            as_of, filters
        )
        last_sale_records = self._analytics.list_last_sale_dates(
            as_of, filters
        )
        slow_moving = _slow_moving_products(
            inventory_records,
            last_sale_records,
            as_of,
            threshold_days,
            limit,
        )

        return ProductPerformanceReport(
            period=period,
            best_sellers=tuple(best),
            most_profitable=tuple(profitable),
            slow_moving=tuple(slow_moving),
            cross_currency_sale_count=len(cross_currency_sale_ids),
        )


def _add_best_seller(
    entries: dict[int, dict],
    product_id: int,
    product_name: str,
    category_id: int | None,
    quantity: int,
    revenue: Money,
) -> None:
    entry = entries.setdefault(
        product_id,
        {
            "product_name": product_name,
            "category_id": category_id,
            "net_quantity": 0,
            "revenue": {},
        },
    )
    entry["net_quantity"] += quantity
    add_money(entry["revenue"], revenue)


def _add_profitability(
    entries: dict[tuple[int, str], dict],
    product_id: int,
    product_name: str,
    category_id: int | None,
    currency,
    quantity: int,
    revenue: Money,
    cogs: Money,
) -> None:
    key = (product_id, currency.code)
    entry = entries.setdefault(
        key,
        {
            "product_name": product_name,
            "category_id": category_id,
            "currency": currency,
            "net_quantity": 0,
            "revenue": Money.zero(currency),
            "cogs": Money.zero(currency),
        },
    )
    entry["net_quantity"] += quantity
    entry["revenue"] = entry["revenue"] + revenue
    entry["cogs"] = entry["cogs"] + cogs


def _slow_moving_products(
    inventory_records,
    last_sale_records,
    as_of: datetime,
    threshold_days: int,
    limit: int,
) -> list[SlowMovingProduct]:
    inventory: dict[int, dict] = {}
    for record in inventory_records:
        entry = inventory.setdefault(
            record.product_id,
            {
                "product_name": record.product_name,
                "category_id": record.category_id,
                "remaining_quantity": 0,
                "value": {},
            },
        )
        entry["remaining_quantity"] += record.remaining_quantity
        add_money(
            entry["value"],
            money(
                record.unit_cost * record.remaining_quantity,
                record.currency,
            ),
        )

    last_sale: dict[int, datetime] = {}
    for record in last_sale_records:
        current = last_sale.get(record.product_id)
        if current is None or record.last_sale_date > current:
            last_sale[record.product_id] = record.last_sale_date

    threshold = as_of - timedelta(days=threshold_days)
    result: list[SlowMovingProduct] = []
    for product_id, entry in inventory.items():
        if entry["remaining_quantity"] <= 0:
            continue
        last_date = last_sale.get(product_id)
        if last_date is not None and last_date > threshold:
            continue
        days_since = (
            (as_of - last_date).days if last_date is not None else None
        )
        result.append(
            SlowMovingProduct(
                product_id=product_id,
                product_name=entry["product_name"],
                category_id=entry["category_id"],
                remaining_quantity=entry["remaining_quantity"],
                inventory_value=totals_tuple(entry["value"]),
                last_sale_date=last_date,
                days_since_last_sale=days_since,
            )
        )

    result.sort(
        key=lambda item: (
            item.days_since_last_sale is not None,
            -(item.days_since_last_sale or 0),
            -item.remaining_quantity,
            item.product_name,
        )
    )
    return result[:limit]
