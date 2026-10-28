"""Supplier profitability use case."""

from __future__ import annotations

from app.application.analytics.aggregation import (
    aggregate_sale_items,
    customer_return_cogs,
    customer_return_revenue,
)
from app.application.analytics.calculations import (
    add_decimal,
    add_money,
    money,
    proportional_money,
    totals_tuple,
)
from app.application.analytics.models import (
    AnalyticsFilters,
    AnalyticsPeriod,
    SupplierProfitability,
    SupplierProfitabilityReport,
)
from app.application.analytics.ports import AnalyticsRepository
from app.domain.value_objects.money import Money


class GetSupplierProfitability:
    """Attribute net revenue, COGS and refunds to each supplier."""

    def __init__(self, analytics: AnalyticsRepository) -> None:
        self._analytics = analytics

    def execute(
        self,
        period: AnalyticsPeriod,
        filters: AnalyticsFilters | None = None,
    ) -> SupplierProfitabilityReport:
        filters = filters or AnalyticsFilters()
        sale_records = self._analytics.list_sale_allocations(period, filters)
        return_records = self._analytics.list_customer_return_allocations(
            period, filters
        )
        supplier_return_records = self._analytics.list_supplier_return_items(
            period, filters
        )
        aggregates, cross_currency_sale_ids, _ = aggregate_sale_items(
            sale_records
        )

        entries: dict[int | None, dict] = {}
        cross_sales_by_supplier: dict[int | None, set[int]] = {}

        for aggregate in aggregates:
            for allocation in aggregate.allocations:
                entry = _entry(
                    entries,
                    allocation.supplier_id,
                    allocation.supplier_name,
                )
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
                entry["net_quantity"] += allocation.allocation_quantity
                add_money(entry["revenue"], revenue_share)
                add_money(entry["cogs"], cogs)
                if aggregate.sale_id not in cross_currency_sale_ids:
                    add_money(
                        entry["gross_profit"], revenue_share - cogs
                    )
                else:
                    cross_sales_by_supplier.setdefault(
                        allocation.supplier_id, set()
                    ).add(aggregate.sale_id)

        for record in return_records:
            entry = _entry(
                entries, record.supplier_id, record.supplier_name
            )
            reversed_revenue = customer_return_revenue(record)
            reversed_cogs = customer_return_cogs(record)
            entry["net_quantity"] -= record.return_allocation_quantity
            add_money(entry["revenue"], -reversed_revenue)
            add_money(entry["cogs"], -reversed_cogs)
            add_money(
                entry["customer_return_revenue"], reversed_revenue
            )
            add_money(entry["customer_return_cogs"], reversed_cogs)
            if record.sale_is_same_currency:
                add_money(
                    entry["gross_profit"],
                    -(reversed_revenue - reversed_cogs),
                )

        refunded_returns: set[int] = set()
        for record in supplier_return_records:
            entry = _entry(
                entries, record.supplier_id, record.supplier_name
            )
            add_money(
                entry["supplier_return_cost"],
                money(
                    record.unit_cost * record.quantity,
                    record.cost_currency,
                ),
            )
            if record.supplier_return_id not in refunded_returns:
                refunded_returns.add(record.supplier_return_id)
                if record.refund_currency is not None:
                    add_decimal(
                        entry["supplier_refunds"],
                        record.refund_amount,
                        record.refund_currency,
                    )

        suppliers = tuple(
            SupplierProfitability(
                supplier_id=supplier_id,
                supplier_name=entry["supplier_name"],
                net_quantity=entry["net_quantity"],
                revenue=totals_tuple(entry["revenue"]),
                cogs=totals_tuple(entry["cogs"]),
                gross_profit=totals_tuple(entry["gross_profit"]),
                customer_return_revenue=totals_tuple(
                    entry["customer_return_revenue"]
                ),
                customer_return_cogs=totals_tuple(
                    entry["customer_return_cogs"]
                ),
                supplier_refunds=totals_tuple(entry["supplier_refunds"]),
                supplier_return_cost=totals_tuple(
                    entry["supplier_return_cost"]
                ),
                cross_currency_sale_count=len(
                    cross_sales_by_supplier.get(supplier_id, set())
                ),
            )
            for supplier_id, entry in sorted(
                entries.items(),
                key=lambda item: (
                    item[1]["supplier_name"] or "",
                    item[0] if item[0] is not None else 0,
                ),
            )
        )

        return SupplierProfitabilityReport(
            period=period,
            suppliers=suppliers,
        )


def _entry(
    entries: dict[int | None, dict],
    supplier_id: int | None,
    supplier_name: str | None,
) -> dict:
    return entries.setdefault(
        supplier_id,
        {
            "supplier_name": supplier_name,
            "net_quantity": 0,
            "revenue": {},
            "cogs": {},
            "gross_profit": {},
            "customer_return_revenue": {},
            "customer_return_cogs": {},
            "supplier_refunds": {},
            "supplier_return_cost": {},
        },
    )
