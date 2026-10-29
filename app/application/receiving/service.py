"""Application service for the Receiving screen."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.application.inventory import (
    ReceivedPurchase,
    ReceivePurchase,
    ReceivePurchaseRequest,
    VariantStock,
    GetVariantStock,
)
from app.application.unit_of_work import UnitOfWorkFactory
from app.domain.entities.purchase import Purchase
from app.domain.enums.purchase_status import PurchaseStatus
from app.domain.inventory import (
    effective_unit_cost,
    received_quantity,
    remaining_quantity,
)
from app.domain.value_objects.money import Money

_RECEIVABLE_STATUSES = (
    PurchaseStatus.IN_TRANSIT,
    PurchaseStatus.PARTIALLY_RECEIVED,
)


@dataclass(frozen=True, slots=True)
class ReceivingLine:
    """One purchase line with its remaining receipt quantity."""

    purchase_item_id: int
    variant_label: str
    ordered_quantity: int
    received_quantity: int
    remaining_quantity: int
    unit_cost: Money


@dataclass(frozen=True, slots=True)
class ReceivingPurchase:
    """A paid purchase that can still receive stock."""

    purchase_id: int
    purchase_date: datetime
    supplier_name: str | None
    currency_code: str
    status: PurchaseStatus
    lines: tuple[ReceivingLine, ...]

    @property
    def item_count(self) -> int:
        return len(self.lines)

    @property
    def remaining_units(self) -> int:
        return sum(line.remaining_quantity for line in self.lines)


class ReceivingService:
    """Read receivable purchases and register receipts atomically."""

    def __init__(self, unit_of_work: UnitOfWorkFactory) -> None:
        self._unit_of_work = unit_of_work

    def list_receivable_purchases(self) -> tuple[ReceivingPurchase, ...]:
        with self._unit_of_work.unit_of_work() as uow:
            suppliers = {
                supplier.id: supplier.name
                for supplier in uow.suppliers.list_all(include_inactive=True)
            }
            rows: list[ReceivingPurchase] = []
            for purchase in uow.purchases.list_all():
                if purchase.status not in _RECEIVABLE_STATUSES:
                    continue
                rows.append(
                    self._read_purchase(
                        purchase,
                        suppliers,
                        uow.purchase_items,
                        uow.purchase_allocations,
                        uow.inventory_lots,
                        uow.products,
                        uow.variants,
                    )
                )
            return tuple(rows)

    def get_receivable_purchase(self, purchase_id: int) -> ReceivingPurchase:
        with self._unit_of_work.unit_of_work() as uow:
            purchase = uow.purchases.get_by_id(purchase_id)
            if purchase is None:
                raise LookupError(f"Purchase {purchase_id} does not exist.")
            if purchase.status not in _RECEIVABLE_STATUSES:
                raise ValueError(
                    "Only purchases in transit or partially received can "
                    "receive stock."
                )
            suppliers = {
                supplier.id: supplier.name
                for supplier in uow.suppliers.list_all(include_inactive=True)
            }
            return self._read_purchase(
                purchase,
                suppliers,
                uow.purchase_items,
                uow.purchase_allocations,
                uow.inventory_lots,
                uow.products,
                uow.variants,
            )

    def receive_purchase(
        self, request: ReceivePurchaseRequest
    ) -> ReceivedPurchase:
        with self._unit_of_work.unit_of_work() as uow:
            result = ReceivePurchase(
                purchases=uow.purchases,
                items=uow.purchase_items,
                allocations=uow.purchase_allocations,
                lots=uow.inventory_lots,
                movements=uow.inventory_movements,
            ).execute(request)
            uow.commit()
            return result

    def get_variant_stock(self, variant_id: int) -> VariantStock:
        with self._unit_of_work.unit_of_work() as uow:
            return GetVariantStock(
                uow.variants, uow.inventory_lots
            ).execute(variant_id)

    @staticmethod
    def _read_purchase(
        purchase: Purchase,
        suppliers: dict[int, str],
        items_repository,
        allocations_repository,
        lots_repository,
        products_repository,
        variants_repository,
    ) -> ReceivingPurchase:
        if purchase.id is None:
            raise RuntimeError("Persisted purchase has no identifier.")
        items = items_repository.list_for_purchase(purchase.id)
        lots = lots_repository.list_for_purchase(purchase.id)
        allocations = allocations_repository.list_for_purchase(purchase.id)
        lines: list[ReceivingLine] = []
        for item in items:
            if item.id is None:
                continue
            variant = variants_repository.get_by_id(item.variant_id)
            product = (
                products_repository.get_by_id(variant.product_id)
                if variant is not None
                else None
            )
            item_allocations = [
                allocation
                for allocation in allocations
                if allocation.purchase_item.id == item.id
            ]
            lines.append(
                ReceivingLine(
                    purchase_item_id=item.id,
                    variant_label=_variant_label(product, variant),
                    ordered_quantity=item.quantity,
                    received_quantity=received_quantity(item, lots),
                    remaining_quantity=remaining_quantity(item, lots),
                    unit_cost=effective_unit_cost(item, item_allocations),
                )
            )
        return ReceivingPurchase(
            purchase_id=purchase.id,
            purchase_date=purchase.purchase_date,
            supplier_name=(
                suppliers.get(purchase.supplier_id)
                if purchase.supplier_id is not None
                else None
            ),
            currency_code=purchase.currency.code,
            status=purchase.status,
            lines=tuple(line for line in lines if line.remaining_quantity > 0),
        )


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
