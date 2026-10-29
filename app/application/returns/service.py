"""Application service for the Returns screen."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.application.returns.register_customer_return import (
    RegisteredCustomerReturn,
    RegisterCustomerReturn,
    RegisterCustomerReturnRequest,
)
from app.application.returns.register_supplier_return import (
    RegisteredSupplierReturn,
    RegisterSupplierReturn,
    RegisterSupplierReturnRequest,
)
from app.application.unit_of_work import UnitOfWorkFactory
from app.domain.entities.account import Account
from app.domain.entities.currency import Currency
from app.domain.entities.customer_return import CustomerReturn
from app.domain.entities.purchase import Purchase
from app.domain.entities.sale import Sale
from app.domain.entities.supplier_return import SupplierReturn
from app.domain.enums.sale_status import SaleStatus
from app.domain.sales_costing import sale_revenue
from app.domain.value_objects.money import Money


@dataclass(frozen=True, slots=True)
class CustomerReturnRow:
    """A customer return header ready for display."""

    return_id: int
    return_date: datetime
    sale_id: int
    item_count: int
    refund_amount: Money | None
    account_name: str | None
    notes: str | None


@dataclass(frozen=True, slots=True)
class SupplierReturnRow:
    """A supplier return header ready for display."""

    return_id: int
    return_date: datetime
    purchase_id: int
    supplier_name: str | None
    item_count: int
    refund_amount: Money | None
    account_name: str | None
    notes: str | None


@dataclass(frozen=True, slots=True)
class ReturnableSale:
    """A sale that can still receive customer returns."""

    sale_id: int
    sale_date: datetime
    account_name: str
    currency_code: str
    total: Money
    status: SaleStatus
    returnable_units: int

    @property
    def label(self) -> str:
        return (
            f"Sale #{self.sale_id} · {self.sale_date.date().isoformat()} · "
            f"{self.total}"
        )


@dataclass(frozen=True, slots=True)
class ReturnablePurchase:
    """A purchase with remaining lots available for supplier return."""

    purchase_id: int
    purchase_date: datetime
    supplier_name: str | None
    currency_code: str
    lot_count: int
    remaining_units: int

    @property
    def label(self) -> str:
        supplier = self.supplier_name or "No supplier"
        return (
            f"Purchase #{self.purchase_id} · {supplier} · "
            f"{self.purchase_date.date().isoformat()}"
        )


@dataclass(frozen=True, slots=True)
class CustomerReturnLine:
    """One sold line and its remaining returnable quantity."""

    sale_item_id: int
    variant_label: str
    sold_quantity: int
    returned_quantity: int
    returnable_quantity: int
    unit_price: Money
    line_total: Money


@dataclass(frozen=True, slots=True)
class CustomerReturnContext:
    """Original sale data needed by the customer-return dialog."""

    sale_id: int
    sale_date: datetime
    account_name: str
    currency: Currency
    status: SaleStatus
    total: Money
    lines: tuple[CustomerReturnLine, ...]


@dataclass(frozen=True, slots=True)
class SupplierReturnLot:
    """One exact lot available for supplier return."""

    purchase_item_id: int
    lot_id: int
    variant_label: str
    remaining_quantity: int
    unit_cost: Money


@dataclass(frozen=True, slots=True)
class SupplierReturnContext:
    """Original purchase data needed by the supplier-return dialog."""

    purchase_id: int
    purchase_date: datetime
    supplier_name: str | None
    currency: Currency
    lots: tuple[SupplierReturnLot, ...]


class ReturnsService:
    """Read return history and register customer/supplier returns."""

    def __init__(self, unit_of_work: UnitOfWorkFactory) -> None:
        self._unit_of_work = unit_of_work

    def list_customer_returns(self) -> tuple[CustomerReturnRow, ...]:
        with self._unit_of_work.unit_of_work() as uow:
            rows = []
            for customer_return in uow.customer_returns.list_all():
                if customer_return.id is None:
                    continue
                items = uow.customer_return_items.list_for_return(
                    customer_return.id
                )
                rows.append(
                    CustomerReturnRow(
                        return_id=customer_return.id,
                        return_date=customer_return.return_date,
                        sale_id=customer_return.sale.id
                        if customer_return.sale.id is not None
                        else 0,
                        item_count=len(items),
                        refund_amount=customer_return.refund_amount,
                        account_name=(
                            customer_return.account.name
                            if customer_return.account is not None
                            else None
                        ),
                        notes=customer_return.notes,
                    )
                )
            return tuple(rows)

    def list_supplier_returns(self) -> tuple[SupplierReturnRow, ...]:
        with self._unit_of_work.unit_of_work() as uow:
            suppliers = {
                supplier.id: supplier.name
                for supplier in uow.suppliers.list_all(include_inactive=True)
            }
            rows = []
            for supplier_return in uow.supplier_returns.list_all():
                if supplier_return.id is None:
                    continue
                items = uow.supplier_return_items.list_for_return(
                    supplier_return.id
                )
                purchase = supplier_return.purchase
                rows.append(
                    SupplierReturnRow(
                        return_id=supplier_return.id,
                        return_date=supplier_return.return_date,
                        purchase_id=(
                            purchase.id if purchase.id is not None else 0
                        ),
                        supplier_name=(
                            suppliers.get(purchase.supplier_id)
                            if purchase.supplier_id is not None
                            else None
                        ),
                        item_count=len(items),
                        refund_amount=supplier_return.refund_amount,
                        account_name=(
                            supplier_return.account.name
                            if supplier_return.account is not None
                            else None
                        ),
                        notes=supplier_return.notes,
                    )
                )
            return tuple(rows)

    def list_returnable_sales(self) -> tuple[ReturnableSale, ...]:
        with self._unit_of_work.unit_of_work() as uow:
            rows = []
            for sale in uow.sales.list_all():
                if sale.status in (
                    SaleStatus.CANCELLED,
                    SaleStatus.REFUNDED,
                ):
                    continue
                if sale.id is None:
                    continue
                items = uow.sale_items.list_for_sale(sale.id)
                returned = _returned_by_sale_item(
                    uow.customer_return_items.list_for_sale(sale.id)
                )
                returnable = sum(
                    max(0, item.quantity - returned.get(item.id, 0))
                    for item in items
                    if item.id is not None
                )
                if returnable == 0:
                    continue
                rows.append(
                    ReturnableSale(
                        sale_id=sale.id,
                        sale_date=sale.sale_date,
                        account_name=sale.account.name,
                        currency_code=sale.currency.code,
                        total=sale_revenue(sale, items),
                        status=sale.status,
                        returnable_units=returnable,
                    )
                )
            return tuple(rows)

    def list_returnable_purchases(self) -> tuple[ReturnablePurchase, ...]:
        with self._unit_of_work.unit_of_work() as uow:
            suppliers = {
                supplier.id: supplier.name
                for supplier in uow.suppliers.list_all(include_inactive=True)
            }
            rows = []
            for purchase in uow.purchases.list_all():
                if purchase.id is None:
                    continue
                lots = [
                    lot
                    for lot in uow.inventory_lots.list_for_purchase(
                        purchase.id
                    )
                    if lot.remaining_quantity > 0
                ]
                if not lots:
                    continue
                rows.append(
                    ReturnablePurchase(
                        purchase_id=purchase.id,
                        purchase_date=purchase.purchase_date,
                        supplier_name=(
                            suppliers.get(purchase.supplier_id)
                            if purchase.supplier_id is not None
                            else None
                        ),
                        currency_code=purchase.currency.code,
                        lot_count=len(lots),
                        remaining_units=sum(
                            lot.remaining_quantity for lot in lots
                        ),
                    )
                )
            return tuple(rows)

    def get_customer_return_context(
        self, sale_id: int
    ) -> CustomerReturnContext:
        with self._unit_of_work.unit_of_work() as uow:
            sale = uow.sales.get_by_id(sale_id)
            if sale is None:
                raise LookupError(f"Sale {sale_id} does not exist.")
            if sale.status in (
                SaleStatus.CANCELLED,
                SaleStatus.REFUNDED,
            ):
                raise ValueError(
                    f"Sale {sale_id} cannot receive more returns."
                )
            items = uow.sale_items.list_for_sale(sale_id)
            returned = _returned_by_sale_item(
                uow.customer_return_items.list_for_sale(sale_id)
            )
            labels = _sale_labels(uow, sale, items)
            lines = tuple(
                CustomerReturnLine(
                    sale_item_id=item.id or 0,
                    variant_label=labels.get(item.variant_id, "Unknown"),
                    sold_quantity=item.quantity,
                    returned_quantity=returned.get(item.id, 0),
                    returnable_quantity=max(
                        0, item.quantity - returned.get(item.id, 0)
                    ),
                    unit_price=item.unit_price,
                    line_total=item.line_total,
                )
                for item in items
                if item.id is not None
                and item.quantity - returned.get(item.id, 0) > 0
            )
            return CustomerReturnContext(
                sale_id=sale_id,
                sale_date=sale.sale_date,
                account_name=sale.account.name,
                currency=sale.currency,
                status=sale.status,
                total=sale_revenue(sale, items),
                lines=lines,
            )

    def get_supplier_return_context(
        self, purchase_id: int
    ) -> SupplierReturnContext:
        with self._unit_of_work.unit_of_work() as uow:
            purchase = uow.purchases.get_by_id(purchase_id)
            if purchase is None:
                raise LookupError(
                    f"Purchase {purchase_id} does not exist."
                )
            suppliers = {
                supplier.id: supplier.name
                for supplier in uow.suppliers.list_all(include_inactive=True)
            }
            items = uow.purchase_items.list_for_purchase(purchase_id)
            items_by_id = {
                item.id: item for item in items if item.id is not None
            }
            labels = _purchase_labels(uow, purchase, items_by_id)
            lots = []
            for lot in uow.inventory_lots.list_for_purchase(purchase_id):
                if lot.remaining_quantity <= 0:
                    continue
                item = items_by_id.get(lot.purchase_item_id)
                if item is None or lot.id is None:
                    continue
                lots.append(
                    SupplierReturnLot(
                        purchase_item_id=item.id or 0,
                        lot_id=lot.id,
                        variant_label=labels.get(
                            item.variant_id, "Unknown"
                        ),
                        remaining_quantity=lot.remaining_quantity,
                        unit_cost=lot.unit_cost,
                    )
                )
            return SupplierReturnContext(
                purchase_id=purchase_id,
                purchase_date=purchase.purchase_date,
                supplier_name=(
                    suppliers.get(purchase.supplier_id)
                    if purchase.supplier_id is not None
                    else None
                ),
                currency=purchase.currency,
                lots=tuple(lots),
            )

    def list_accounts(self) -> tuple[Account, ...]:
        with self._unit_of_work.unit_of_work() as uow:
            return tuple(uow.accounts.list_all())

    def register_customer_return(
        self, request: RegisterCustomerReturnRequest
    ) -> RegisteredCustomerReturn:
        with self._unit_of_work.unit_of_work() as uow:
            result = RegisterCustomerReturn(
                accounts=uow.accounts,
                sales=uow.sales,
                sale_items=uow.sale_items,
                sale_allocations=uow.sale_allocations,
                customer_returns=uow.customer_returns,
                return_items=uow.customer_return_items,
                return_allocations=uow.return_allocations,
                lots=uow.inventory_lots,
                movements=uow.inventory_movements,
                transactions=uow.transactions,
            ).execute(request)
            uow.commit()
            return result

    def register_supplier_return(
        self, request: RegisterSupplierReturnRequest
    ) -> RegisteredSupplierReturn:
        with self._unit_of_work.unit_of_work() as uow:
            result = RegisterSupplierReturn(
                accounts=uow.accounts,
                purchases=uow.purchases,
                purchase_items=uow.purchase_items,
                lots=uow.inventory_lots,
                supplier_returns=uow.supplier_returns,
                return_items=uow.supplier_return_items,
                movements=uow.inventory_movements,
                transactions=uow.transactions,
            ).execute(request)
            uow.commit()
            return result


def _returned_by_sale_item(items) -> dict[int, int]:
    totals: dict[int, int] = {}
    for item in items:
        if item.sale_item_id is None:
            continue
        totals[item.sale_item_id] = (
            totals.get(item.sale_item_id, 0) + item.quantity
        )
    return totals


def _sale_labels(uow, sale: Sale, items) -> dict[int, str]:
    labels: dict[int, str] = {}
    for variant_id in {item.variant_id for item in items}:
        variant = uow.variants.get_by_id(variant_id)
        product = (
            uow.products.get_by_id(variant.product_id)
            if variant is not None
            else None
        )
        labels[variant_id] = _variant_label(product, variant)
    return labels


def _purchase_labels(uow, purchase: Purchase, items_by_id) -> dict[int, str]:
    labels: dict[int, str] = {}
    for item in items_by_id.values():
        variant = uow.variants.get_by_id(item.variant_id)
        product = (
            uow.products.get_by_id(variant.product_id)
            if variant is not None
            else None
        )
        labels[item.variant_id] = _variant_label(product, variant)
    return labels


def _variant_label(product, variant) -> str:
    if variant is None:
        return "Unknown variant"
    product_name = product.name if product is not None else "Unknown product"
    parts = [product_name]
    if variant.variant_name:
        parts.append(variant.variant_name)
    label = " / ".join(parts)
    if variant.sku:
        label = f"{label} ({variant.sku})"
    return label
