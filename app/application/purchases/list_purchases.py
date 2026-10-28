"""Purchase list, detail and reference-data queries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.domain.entities.purchase import Purchase
from app.domain.entities.purchase_cost import PurchaseCost
from app.domain.entities.purchase_item import PurchaseItem
from app.domain.enums.allocation_method import AllocationMethod
from app.domain.enums.purchase_cost_type import PurchaseCostType
from app.domain.enums.purchase_status import PurchaseStatus
from app.domain.exceptions import PurchaseNotFoundError
from app.domain.purchase_costing import purchase_total
from app.domain.repositories.product_repository import ProductRepository
from app.domain.repositories.product_variant_repository import (
    ProductVariantRepository,
)
from app.domain.repositories.purchase_cost_repository import (
    PurchaseCostRepository,
)
from app.domain.repositories.purchase_item_repository import (
    PurchaseItemRepository,
)
from app.domain.repositories.purchase_repository import PurchaseRepository
from app.domain.repositories.supplier_repository import SupplierRepository
from app.domain.value_objects.money import Money


@dataclass(frozen=True, slots=True)
class PurchaseListItem:
    """One purchase row ready for presentation."""

    purchase_id: int
    purchase_date: datetime
    supplier_id: int | None
    supplier_name: str | None
    currency_code: str
    item_count: int
    total: Money
    status: PurchaseStatus
    account_name: str | None
    order_number: str | None
    tracking_number: str | None
    notes: str | None
    allowed_statuses: tuple[PurchaseStatus, ...]


@dataclass(frozen=True, slots=True)
class PurchaseItemDetail:
    """One ordered item inside a purchase detail."""

    item_id: int
    variant_label: str
    quantity: int
    unit_price: Money
    line_total: Money
    weight: str | None


@dataclass(frozen=True, slots=True)
class PurchaseCostDetail:
    """One acquisition cost inside a purchase detail."""

    cost_id: int
    cost_type: PurchaseCostType
    amount: Money
    normalized_amount: Money
    allocation_method: AllocationMethod
    description: str | None


@dataclass(frozen=True, slots=True)
class PurchaseDetail:
    """Header, items and costs of one purchase."""

    purchase: PurchaseListItem
    items: tuple[PurchaseItemDetail, ...]
    costs: tuple[PurchaseCostDetail, ...]


@dataclass(frozen=True, slots=True)
class VariantOption:
    """An active variant that can be added to a purchase."""

    variant_id: int
    label: str
    product_name: str
    variant_name: str | None
    sku: str | None


class ListPurchases:
    """Return purchases with derived totals and supplier names."""

    def __init__(
        self,
        purchases: PurchaseRepository,
        items: PurchaseItemRepository,
        costs: PurchaseCostRepository,
        suppliers: SupplierRepository,
    ) -> None:
        self._purchases = purchases
        self._items = items
        self._costs = costs
        self._suppliers = suppliers

    def execute(self) -> tuple[PurchaseListItem, ...]:
        supplier_names = {
            supplier.id: supplier.name
            for supplier in self._suppliers.list_all(include_inactive=True)
        }
        rows: list[PurchaseListItem] = []
        for purchase in self._purchases.list_all():
            if purchase.id is None:
                raise RuntimeError("Stored purchase has no identifier.")
            rows.append(
                _list_item(
                    purchase,
                    items=self._items.list_for_purchase(purchase.id),
                    costs=self._costs.list_for_purchase(purchase.id),
                    supplier_names=supplier_names,
                )
            )
        return tuple(rows)


class GetPurchaseDetail:
    """Return the full content of one purchase."""

    def __init__(
        self,
        purchases: PurchaseRepository,
        items: PurchaseItemRepository,
        costs: PurchaseCostRepository,
        suppliers: SupplierRepository,
        products: ProductRepository,
        variants: ProductVariantRepository,
    ) -> None:
        self._purchases = purchases
        self._items = items
        self._costs = costs
        self._suppliers = suppliers
        self._products = products
        self._variants = variants

    def execute(self, purchase_id: int) -> PurchaseDetail:
        purchase = self._purchases.get_by_id(purchase_id)
        if purchase is None:
            raise PurchaseNotFoundError(
                f"Purchase {purchase_id} does not exist."
            )

        items = self._items.list_for_purchase(purchase_id)
        costs = self._costs.list_for_purchase(purchase_id)
        supplier_names: dict[int, str] = {}
        if purchase.supplier_id is not None:
            supplier = self._suppliers.get_by_id(purchase.supplier_id)
            if supplier is not None:
                supplier_names[purchase.supplier_id] = supplier.name

        return PurchaseDetail(
            purchase=_list_item(
                purchase,
                items=items,
                costs=costs,
                supplier_names=supplier_names,
            ),
            items=tuple(
                _item_detail(item, self._variant_label(item.variant_id))
                for item in items
            ),
            costs=tuple(_cost_detail(cost) for cost in costs),
        )

    def _variant_label(self, variant_id: int) -> str:
        variant = self._variants.get_by_id(variant_id)
        if variant is None:
            return f"Variant {variant_id}"
        product = self._products.get_by_id(variant.product_id)
        product_name = (
            product.name
            if product is not None
            else f"Product {variant.product_id}"
        )
        return _variant_label(
            product_name,
            variant.variant_name,
            variant.sku,
        )


class ListVariantOptions:
    """Return active product variants with a display label."""

    def __init__(
        self,
        products: ProductRepository,
        variants: ProductVariantRepository,
    ) -> None:
        self._products = products
        self._variants = variants

    def execute(self) -> tuple[VariantOption, ...]:
        options: list[VariantOption] = []
        for product in self._products.list_all():
            if product.id is None:
                continue
            for variant in self._variants.list_for_product(product.id):
                if variant.id is None:
                    continue
                options.append(
                    VariantOption(
                        variant_id=variant.id,
                        label=_variant_label(
                            product.name,
                            variant.variant_name,
                            variant.sku,
                        ),
                        product_name=product.name,
                        variant_name=variant.variant_name,
                        sku=variant.sku,
                    )
                )
        return tuple(options)


def _list_item(
    purchase: Purchase,
    *,
    items: list[PurchaseItem],
    costs: list[PurchaseCost],
    supplier_names: dict[int, str],
) -> PurchaseListItem:
    if purchase.id is None:
        raise RuntimeError("Stored purchase has no identifier.")
    if not items:
        raise RuntimeError(
            f"Purchase {purchase.id} has no items and cannot be listed."
        )

    return PurchaseListItem(
        purchase_id=purchase.id,
        purchase_date=purchase.purchase_date,
        supplier_id=purchase.supplier_id,
        supplier_name=supplier_names.get(purchase.supplier_id),
        currency_code=purchase.currency.code,
        item_count=len(items),
        total=purchase_total(items, costs),
        status=purchase.status,
        account_name=(
            purchase.account.name if purchase.account is not None else None
        ),
        order_number=purchase.order_number,
        tracking_number=purchase.tracking_number,
        notes=purchase.notes,
        allowed_statuses=purchase.allowed_logistics_transitions,
    )


def _item_detail(item: PurchaseItem, variant_label: str) -> PurchaseItemDetail:
    if item.id is None:
        raise RuntimeError("Stored purchase item has no identifier.")
    return PurchaseItemDetail(
        item_id=item.id,
        variant_label=variant_label,
        quantity=item.quantity,
        unit_price=item.unit_price,
        line_total=item.line_total,
        weight=str(item.weight) if item.weight is not None else None,
    )


def _cost_detail(cost: PurchaseCost) -> PurchaseCostDetail:
    if cost.id is None:
        raise RuntimeError("Stored purchase cost has no identifier.")
    return PurchaseCostDetail(
        cost_id=cost.id,
        cost_type=cost.cost_type,
        amount=cost.amount,
        normalized_amount=cost.normalized_amount,
        allocation_method=cost.allocation_method,
        description=cost.description,
    )


def _variant_label(
    product_name: str,
    variant_name: str | None,
    sku: str | None,
) -> str:
    label = product_name
    if variant_name:
        label = f"{label} / {variant_name}"
    if sku:
        label = f"{label} ({sku})"
    return label
