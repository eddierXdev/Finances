"""Sale revenue, historical COGS and gross-profit rules."""

from __future__ import annotations

from collections.abc import Sequence

from app.domain.entities.sale import Sale
from app.domain.entities.sale_item import SaleItem
from app.domain.entities.sale_item_lot_allocation import (
    SaleItemLotAllocation,
)
from app.domain.exceptions import CurrencyMismatchError, InvalidSaleError
from app.domain.value_objects.money import Money


def sale_revenue(sale: Sale, items: Sequence[SaleItem]) -> Money:
    """Return net revenue after item and sale-level discounts."""
    if not isinstance(sale, Sale):
        raise TypeError("sale_revenue requires a Sale.")
    if not items:
        raise InvalidSaleError("A sale requires at least one item.")

    total = Money.zero(sale.currency)
    for item in items:
        if not isinstance(item, SaleItem):
            raise TypeError("sale_revenue requires SaleItem instances.")
        _require_item_belongs_to_sale(item, sale)
        total = total + item.line_total

    if sale.discount_amount is not None:
        if sale.discount_amount > total:
            raise InvalidSaleError(
                "Sale discount_amount cannot exceed the item subtotal."
            )
        total = total - sale.discount_amount

    return total


def sale_cogs_by_currency(
    allocations: Sequence[SaleItemLotAllocation],
) -> tuple[Money, ...]:
    """Group historical COGS by each allocation's cost currency."""
    if not allocations:
        raise InvalidSaleError(
            "COGS requires at least one FIFO allocation."
        )

    totals: dict[str, Money] = {}
    for allocation in allocations:
        if not isinstance(allocation, SaleItemLotAllocation):
            raise TypeError(
                "sale_cogs requires SaleItemLotAllocation instances."
            )
        currency = allocation.unit_cost_snapshot.currency
        current = totals.get(currency.code, Money.zero(currency))
        totals[currency.code] = current + allocation.cogs

    return tuple(totals[code] for code in sorted(totals))


def sale_cogs(
    allocations: Sequence[SaleItemLotAllocation],
) -> Money:
    """Return historical COGS when every allocation shares one currency.

    Mixing currencies raises ``CurrencyMismatchError`` because V1 never
    applies implicit FX. Use ``sale_cogs_by_currency`` to report a sale
    whose lots were acquired in more than one currency.
    """
    totals = sale_cogs_by_currency(allocations)
    if len(totals) != 1:
        raise CurrencyMismatchError(
            "COGS spans multiple currencies; explicit conversion is "
            "required."
        )
    return totals[0]


def sale_gross_profit(
    sale: Sale,
    items: Sequence[SaleItem],
    allocations: Sequence[SaleItemLotAllocation],
) -> Money:
    """Return revenue minus COGS when both use the same currency."""
    return sale_revenue(sale, items) - sale_cogs(allocations)


def _require_item_belongs_to_sale(item: SaleItem, sale: Sale) -> None:
    if sale.id is not None:
        if item.sale.id != sale.id:
            raise InvalidSaleError(
                "All items must belong to the sale being costed."
            )
    elif item.sale is not sale:
        raise InvalidSaleError(
            "All items must belong to the sale being costed."
        )
