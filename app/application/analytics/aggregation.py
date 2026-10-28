"""Shared grouping and revenue-allocation helpers for analytics."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.application.analytics.calculations import (
    allocate_sale_discount,
    money,
    proportional_money,
)
from app.application.analytics.models import (
    CustomerReturnAllocationRecord,
    SaleAllocationRecord,
)
from app.domain.entities.currency import Currency
from app.domain.value_objects.money import Money


@dataclass(frozen=True, slots=True)
class SaleItemAggregate:
    """A sale item with its net revenue and FIFO allocations."""

    sale_id: int
    sale_date: datetime
    sale_currency: Currency
    sale_account_id: int
    customer_id: int | None
    sale_discount_amount: Decimal
    sale_item_id: int
    variant_id: int
    variant_name: str | None
    sku: str | None
    product_id: int
    product_name: str
    category_id: int | None
    item_quantity: int
    line_total: Money
    net_revenue: Money
    allocations: tuple[SaleAllocationRecord, ...]


def aggregate_sale_items(
    records: list[SaleAllocationRecord],
) -> tuple[list[SaleItemAggregate], set[int], int]:
    """Group allocation rows into sale items and allocate sale discounts.

    Returns the item aggregates, the ids of sales whose FIFO costs span a
    different currency, and the number of distinct sales.
    """
    by_sale: dict[int, list[SaleAllocationRecord]] = defaultdict(list)
    for record in records:
        by_sale[record.sale_id].append(record)

    aggregates: list[SaleItemAggregate] = []
    cross_currency_sale_ids: set[int] = set()

    for sale_id in sorted(by_sale):
        sale_records = by_sale[sale_id]
        by_item: dict[int, list[SaleAllocationRecord]] = defaultdict(list)
        for record in sale_records:
            by_item[record.sale_item_id].append(record)

        line_totals: dict[int, Money] = {}
        first_records: dict[int, SaleAllocationRecord] = {}
        for item_id, item_records in by_item.items():
            first = item_records[0]
            first_records[item_id] = first
            subtotal = money(
                first.item_unit_price * first.item_quantity,
                first.sale_currency,
            )
            discount = money(first.item_discount_amount, first.sale_currency)
            line_totals[item_id] = subtotal - discount

        first = sale_records[0]
        sale_discount = money(first.sale_discount_amount, first.sale_currency)
        loaded_total = Money.zero(first.sale_currency)
        for line_total in line_totals.values():
            loaded_total = loaded_total + line_total

        if loaded_total.amount == first.sale_total_line_total:
            discount_shares = allocate_sale_discount(
                line_totals, sale_discount
            )
        else:
            discount_shares = {}
            for item_id, line_total in line_totals.items():
                if first.sale_total_line_total == 0:
                    discount_shares[item_id] = Money.zero(
                        first.sale_currency
                    )
                else:
                    discount_shares[item_id] = money(
                        sale_discount.amount
                        * line_total.amount
                        / first.sale_total_line_total,
                        first.sale_currency,
                    )

        sale_cost_currencies = {
            record.cost_currency.code for record in sale_records
        }
        if (
            sale_cost_currencies
            and sale_cost_currencies != {first.sale_currency.code}
        ):
            cross_currency_sale_ids.add(sale_id)

        for item_id in sorted(by_item):
            item_records = by_item[item_id]
            item_first = first_records[item_id]
            aggregates.append(
                SaleItemAggregate(
                    sale_id=sale_id,
                    sale_date=item_first.sale_date,
                    sale_currency=item_first.sale_currency,
                    sale_account_id=item_first.sale_account_id,
                    customer_id=item_first.customer_id,
                    sale_discount_amount=item_first.sale_discount_amount,
                    sale_item_id=item_id,
                    variant_id=item_first.variant_id,
                    variant_name=item_first.variant_name,
                    sku=item_first.sku,
                    product_id=item_first.product_id,
                    product_name=item_first.product_name,
                    category_id=item_first.category_id,
                    item_quantity=item_first.item_quantity,
                    line_total=line_totals[item_id],
                    net_revenue=line_totals[item_id]
                    - discount_shares[item_id],
                    allocations=tuple(item_records),
                )
            )

    return aggregates, cross_currency_sale_ids, len(by_sale)


def original_item_net_revenue(
    record: CustomerReturnAllocationRecord,
) -> Money:
    """Reconstruct the original sale item's revenue after all discounts."""
    line_total = money(
        record.item_unit_price * record.item_quantity
        - record.item_discount_amount,
        record.sale_currency,
    )
    if (
        record.sale_discount_amount == 0
        or record.sale_total_line_total == 0
    ):
        return line_total

    discount_share = money(
        record.sale_discount_amount
        * line_total.amount
        / record.sale_total_line_total,
        record.sale_currency,
    )
    return line_total - discount_share


def customer_return_revenue(
    record: CustomerReturnAllocationRecord,
) -> Money:
    """Return the proportional revenue reversed by one return allocation."""
    return proportional_money(
        original_item_net_revenue(record),
        record.return_allocation_quantity,
        record.item_quantity,
    )


def customer_return_cogs(
    record: CustomerReturnAllocationRecord,
) -> Money:
    """Return the historical cost reversed by one return allocation."""
    return money(
        record.return_unit_cost * record.return_allocation_quantity,
        record.cost_currency,
    )
