"""Application service for the Sales screen."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.application.sales.register_sale import (
    RegisteredSale,
    RegisterSale,
    RegisterSaleRequest,
)
from app.application.unit_of_work import UnitOfWorkFactory
from app.domain.entities.account import Account
from app.domain.entities.currency import Currency
from app.domain.entities.sale import Sale
from app.domain.entities.sale_item import SaleItem
from app.domain.entities.sale_item_lot_allocation import (
    SaleItemLotAllocation,
)
from app.domain.enums.sale_status import SaleStatus
from app.domain.sales_costing import sale_revenue
from app.domain.value_objects.money import Money


@dataclass(frozen=True, slots=True)
class SaleLineRow:
    """One sold line in a sale detail."""

    sale_item_id: int
    variant_label: str
    quantity: int
    unit_price: Money
    discount_amount: Money | None
    line_total: Money


@dataclass(frozen=True, slots=True)
class SaleAllocationRow:
    """One immutable FIFO allocation of a sale line."""

    sale_item_id: int
    variant_label: str
    lot_id: int
    quantity: int
    unit_cost: Money
    cost: Money


@dataclass(frozen=True, slots=True)
class SaleRow:
    """A sale header with totals and historical FIFO result."""

    sale_id: int
    sale_date: datetime
    account_name: str
    currency_code: str
    item_count: int
    total: Money
    status: SaleStatus
    cogs: tuple[Money, ...]
    gross_profit: tuple[Money, ...]
    notes: str | None


@dataclass(frozen=True, slots=True)
class SaleDetail:
    """Everything the read-only sale detail dialog displays."""

    sale: SaleRow
    lines: tuple[SaleLineRow, ...]
    allocations: tuple[SaleAllocationRow, ...]


@dataclass(frozen=True, slots=True)
class SaleVariantOption:
    """A sellable variant with stock and optional catalog price."""

    variant_id: int
    label: str
    sku: str | None
    default_selling_price: Money | None
    on_hand: int


class SalesService:
    """Read sales and register fully collected FIFO sales."""

    def __init__(self, unit_of_work: UnitOfWorkFactory) -> None:
        self._unit_of_work = unit_of_work

    def list_sales(self) -> tuple[SaleRow, ...]:
        with self._unit_of_work.unit_of_work() as uow:
            rows = []
            for sale in uow.sales.list_all():
                items = self._items_for(uow.sale_items, sale)
                allocations = self._allocations_for(
                    uow.sale_allocations, sale
                )
                rows.append(self._sale_row(sale, items, allocations))
            return tuple(rows)

    def get_sale_detail(self, sale_id: int) -> SaleDetail:
        with self._unit_of_work.unit_of_work() as uow:
            sale = uow.sales.get_by_id(sale_id)
            if sale is None:
                raise LookupError(f"Sale {sale_id} does not exist.")
            items = self._items_for(uow.sale_items, sale)
            allocations = self._allocations_for(
                uow.sale_allocations, sale
            )
            labels = self._variant_labels(uow, items, allocations)
            lines = tuple(
                SaleLineRow(
                    sale_item_id=item.id or 0,
                    variant_label=labels.get(item.variant_id, "Unknown"),
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    discount_amount=item.discount_amount,
                    line_total=item.line_total,
                )
                for item in items
            )
            allocation_rows = tuple(
                SaleAllocationRow(
                    sale_item_id=(
                        allocation.sale_item.id
                        if allocation.sale_item.id is not None
                        else 0
                    ),
                    variant_label=labels.get(
                        allocation.sale_item.variant_id, "Unknown"
                    ),
                    lot_id=(
                        allocation.inventory_lot.id
                        if allocation.inventory_lot.id is not None
                        else 0
                    ),
                    quantity=allocation.quantity,
                    unit_cost=allocation.unit_cost_snapshot,
                    cost=allocation.cogs,
                )
                for allocation in allocations
            )
            return SaleDetail(
                sale=self._sale_row(sale, items, allocations),
                lines=lines,
                allocations=allocation_rows,
            )

    def list_accounts(self) -> tuple[Account, ...]:
        with self._unit_of_work.unit_of_work() as uow:
            return tuple(uow.accounts.list_all())

    def list_enabled_currencies(self) -> tuple[Currency, ...]:
        with self._unit_of_work.unit_of_work() as uow:
            return tuple(uow.currencies.list_all(enabled_only=True))

    def list_variant_options(self) -> tuple[SaleVariantOption, ...]:
        with self._unit_of_work.unit_of_work() as uow:
            options: list[SaleVariantOption] = []
            for product in uow.products.list_all():
                if product.id is None:
                    continue
                for variant in uow.variants.list_for_product(product.id):
                    if variant.id is None:
                        continue
                    stock = uow.inventory_lots.total_remaining_by_variant(
                        variant.id
                    )
                    options.append(
                        SaleVariantOption(
                            variant_id=variant.id,
                            label=_variant_label(product, variant),
                            sku=variant.sku,
                            default_selling_price=(
                                product.default_selling_price
                            ),
                            on_hand=stock,
                        )
                    )
            options.sort(key=lambda option: option.label.casefold())
            return tuple(options)

    def register_sale(
        self, request: RegisterSaleRequest
    ) -> RegisteredSale:
        with self._unit_of_work.unit_of_work() as uow:
            result = RegisterSale(
                accounts=uow.accounts,
                customers=uow.customers,
                variants=uow.variants,
                sales=uow.sales,
                items=uow.sale_items,
                allocations=uow.sale_allocations,
                lots=uow.inventory_lots,
                movements=uow.inventory_movements,
                transactions=uow.transactions,
            ).execute(request)
            uow.commit()
            return result

    @staticmethod
    def _items_for(repository, sale: Sale) -> tuple[SaleItem, ...]:
        if sale.id is None:
            return ()
        return tuple(repository.list_for_sale(sale.id))

    @staticmethod
    def _allocations_for(repository, sale: Sale) -> tuple[SaleItemLotAllocation, ...]:
        if sale.id is None:
            return ()
        return tuple(repository.list_for_sale(sale.id))

    @staticmethod
    def _variant_labels(uow, items, allocations) -> dict[int, str]:
        labels: dict[int, str] = {}
        variant_ids = {item.variant_id for item in items}
        for variant_id in variant_ids:
            variant = uow.variants.get_by_id(variant_id)
            if variant is None:
                labels[variant_id] = f"Variant {variant_id}"
                continue
            product = uow.products.get_by_id(variant.product_id)
            labels[variant_id] = _variant_label(product, variant)
        return labels

    def _sale_row(
        self,
        sale: Sale,
        items: tuple[SaleItem, ...],
        allocations: tuple[SaleItemLotAllocation, ...],
    ) -> SaleRow:
        if sale.id is None:
            raise RuntimeError("Persisted sale has no identifier.")
        cogs_by_currency: dict[str, Money] = {}
        for allocation in allocations:
            code = allocation.cogs.currency.code
            cogs_by_currency[code] = (
                cogs_by_currency.get(code, Money.zero(allocation.cogs.currency))
                + allocation.cogs
            )
        cogs = tuple(cogs_by_currency[code] for code in sorted(cogs_by_currency))
        revenue = sale_revenue(sale, items)
        gross_profit = (
            (revenue - cogs[0],)
            if len(cogs) == 1
            and cogs[0].currency.code == revenue.currency.code
            else ()
        )
        return SaleRow(
            sale_id=sale.id,
            sale_date=sale.sale_date,
            account_name=sale.account.name,
            currency_code=sale.currency.code,
            item_count=len(items),
            total=revenue,
            status=sale.status,
            cogs=cogs,
            gross_profit=gross_profit,
            notes=sale.notes,
        )


def _variant_label(product, variant) -> str:
    product_name = product.name if product is not None else "Unknown product"
    parts = [product_name]
    if variant.variant_name:
        parts.append(variant.variant_name)
    label = " / ".join(parts)
    if variant.sku:
        label = f"{label} ({variant.sku})"
    return label
