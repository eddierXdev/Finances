"""Business summary use case."""

from __future__ import annotations

from datetime import UTC, datetime

from app.application.analytics.aggregation import (
    aggregate_sale_items,
    customer_return_cogs,
    customer_return_revenue,
)
from app.application.analytics.calculations import (
    add_decimal,
    add_money,
    money,
    net_totals_map,
    percentage,
    totals_tuple,
)
from app.application.analytics.models import (
    AnalyticsFilters,
    AnalyticsPeriod,
    BusinessSummary,
    CurrencyMargin,
)
from app.application.analytics.ports import AnalyticsRepository
from app.domain.value_objects.money import Money


class GetBusinessSummary:
    """Calculate native revenue, COGS, profit, expenses and refunds."""

    def __init__(
        self,
        analytics: AnalyticsRepository,
        *,
        clock=None,
    ) -> None:
        self._analytics = analytics
        self._clock = clock or (lambda: datetime.now(UTC))

    def execute(
        self,
        period: AnalyticsPeriod,
        filters: AnalyticsFilters | None = None,
    ) -> BusinessSummary:
        filters = filters or AnalyticsFilters()

        sale_records = self._analytics.list_sale_allocations(period, filters)
        return_records = self._analytics.list_customer_return_allocations(
            period, filters
        )
        supplier_return_records = self._analytics.list_supplier_return_items(
            period, filters
        )
        expense_records = self._analytics.list_expenses(period, filters)

        aggregates, cross_currency_sale_ids, sale_count = (
            aggregate_sale_items(sale_records)
        )

        sale_revenue: dict[str, Money] = {}
        sale_cogs: dict[str, Money] = {}
        sale_gross_profit: dict[str, Money] = {}
        sale_units = 0

        for aggregate in aggregates:
            add_money(sale_revenue, aggregate.net_revenue)
            sale_units += sum(
                allocation.allocation_quantity
                for allocation in aggregate.allocations
            )

            item_cogs: dict[str, Money] = {}
            for allocation in aggregate.allocations:
                cogs = money(
                    allocation.allocation_unit_cost
                    * allocation.allocation_quantity,
                    allocation.cost_currency,
                )
                add_money(sale_cogs, cogs)
                add_money(item_cogs, cogs)

            if (
                aggregate.sale_id not in cross_currency_sale_ids
                and item_cogs
            ):
                only_cogs = next(iter(item_cogs.values()))
                add_money(
                    sale_gross_profit,
                    aggregate.net_revenue - only_cogs,
                )

        return_revenue: dict[str, Money] = {}
        return_cogs: dict[str, Money] = {}
        return_gross_reduction: dict[str, Money] = {}
        customer_refunds: dict[str, Money] = {}
        refunded_returns: set[int] = set()
        return_ids: set[int] = set()
        returned_units = 0

        for record in return_records:
            return_ids.add(record.customer_return_id)
            returned_units += record.return_allocation_quantity

            if record.customer_return_id not in refunded_returns:
                refunded_returns.add(record.customer_return_id)
                if record.refund_currency is not None:
                    add_decimal(
                        customer_refunds,
                        record.refund_amount,
                        record.refund_currency,
                    )

            reversed_revenue = customer_return_revenue(record)
            reversed_cogs = customer_return_cogs(record)
            add_money(return_revenue, reversed_revenue)
            add_money(return_cogs, reversed_cogs)

            if record.sale_is_same_currency:
                add_money(
                    return_gross_reduction,
                    reversed_revenue - reversed_cogs,
                )

        supplier_refunds: dict[str, Money] = {}
        supplier_return_cost: dict[str, Money] = {}
        refunded_supplier_returns: set[int] = set()

        for record in supplier_return_records:
            if record.supplier_return_id not in refunded_supplier_returns:
                refunded_supplier_returns.add(record.supplier_return_id)
                if record.refund_currency is not None:
                    add_decimal(
                        supplier_refunds,
                        record.refund_amount,
                        record.refund_currency,
                    )
            add_money(
                supplier_return_cost,
                money(
                    record.unit_cost * record.quantity,
                    record.cost_currency,
                ),
            )

        expenses: dict[str, Money] = {}
        for record in expense_records:
            add_decimal(expenses, record.amount, record.currency)

        revenue_map = net_totals_map(sale_revenue, return_revenue)
        cogs_map = net_totals_map(sale_cogs, return_cogs)
        gross_map = net_totals_map(
            sale_gross_profit, return_gross_reduction
        )
        net_map = net_totals_map(gross_map, expenses)

        margins = tuple(
            CurrencyMargin(
                currency=total.currency,
                gross_margin=(
                    percentage(gross_map[code], total)
                    if code in gross_map
                    else None
                ),
                net_margin=(
                    percentage(net_map[code], total)
                    if code in net_map
                    else None
                ),
            )
            for code, total in sorted(revenue_map.items())
        )

        return BusinessSummary(
            period=period,
            revenue=totals_tuple(revenue_map),
            cogs=totals_tuple(cogs_map),
            gross_profit=totals_tuple(gross_map),
            expenses=totals_tuple(expenses),
            net_profit=totals_tuple(net_map),
            customer_refunds=totals_tuple(customer_refunds),
            supplier_refunds=totals_tuple(supplier_refunds),
            supplier_return_cost=totals_tuple(supplier_return_cost),
            margins=margins,
            units_sold=sale_units - returned_units,
            sale_count=sale_count,
            return_count=len(return_ids),
            cross_currency_sale_count=len(cross_currency_sale_ids),
        )
