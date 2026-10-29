"""Application read service for the Inventory screen."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.application.analytics.calculations import add_money, totals_tuple
from app.application.unit_of_work import UnitOfWorkFactory
from app.domain.entities.inventory_lot import InventoryLot
from app.domain.entities.inventory_movement import InventoryMovement
from app.domain.entities.product import Product
from app.domain.entities.product_variant import ProductVariant
from app.domain.enums.inventory_movement_type import InventoryMovementType
from app.domain.value_objects.money import Money


@dataclass(frozen=True, slots=True)
class InventoryStockRow:
    """Current stock and historical acquisition value for one variant."""

    variant_id: int
    product_name: str
    variant_name: str | None
    sku: str | None
    is_active: bool
    on_hand: int
    lot_count: int
    value: tuple[Money, ...]

    @property
    def label(self) -> str:
        parts = [self.product_name]
        if self.variant_name:
            parts.append(self.variant_name)
        return " / ".join(parts)

    @property
    def value_label(self) -> str:
        if not self.value:
            return "—"
        return " + ".join(str(amount) for amount in self.value)


@dataclass(frozen=True, slots=True)
class InventoryLotRow:
    """One traceable acquisition lot."""

    lot_id: int
    purchase_id: int
    product_name: str
    variant_name: str | None
    sku: str | None
    received_at: datetime
    acquired_quantity: int
    remaining_quantity: int
    unit_cost: Money
    supplier_name: str | None

    @property
    def label(self) -> str:
        parts = [self.product_name]
        if self.variant_name:
            parts.append(self.variant_name)
        return " / ".join(parts)


@dataclass(frozen=True, slots=True)
class InventoryMovementRow:
    """One signed stock movement."""

    movement_id: int
    movement_date: datetime
    movement_type: InventoryMovementType
    product_name: str
    variant_name: str | None
    sku: str | None
    quantity: int
    lot_id: int | None
    unit_cost: Money | None
    reference_type: str | None
    reference_id: int | None
    notes: str | None

    @property
    def label(self) -> str:
        parts = [self.product_name]
        if self.variant_name:
            parts.append(self.variant_name)
        return " / ".join(parts)


class InventoryService:
    """Build inventory read models without exposing persistence objects."""

    def __init__(self, unit_of_work: UnitOfWorkFactory) -> None:
        self._unit_of_work = unit_of_work

    def list_stock(self) -> tuple[InventoryStockRow, ...]:
        with self._unit_of_work.unit_of_work() as uow:
            rows: list[InventoryStockRow] = []
            for product, variant in _all_variants(
                uow.products, uow.variants
            ):
                lots = uow.inventory_lots.list_by_variant(variant.id)
                values: dict[str, Money] = {}
                for lot in lots:
                    add_money(
                        values,
                        lot.unit_cost * lot.remaining_quantity,
                    )
                rows.append(
                    InventoryStockRow(
                        variant_id=variant.id,
                        product_name=product.name,
                        variant_name=variant.variant_name,
                        sku=variant.sku,
                        is_active=variant.is_active,
                        on_hand=sum(
                            lot.remaining_quantity for lot in lots
                        ),
                        lot_count=len(lots),
                        value=totals_tuple(values),
                    )
                )
            rows.sort(
                key=lambda row: (
                    not row.is_active,
                    row.product_name.casefold(),
                    row.variant_name or "",
                )
            )
            return tuple(rows)

    def list_lots(self) -> tuple[InventoryLotRow, ...]:
        with self._unit_of_work.unit_of_work() as uow:
            suppliers = {
                supplier.id: supplier.name
                for supplier in uow.suppliers.list_all(include_inactive=True)
            }
            rows: list[InventoryLotRow] = []
            for product, variant in _all_variants(
                uow.products, uow.variants
            ):
                for lot in uow.inventory_lots.list_by_variant(variant.id):
                    rows.append(
                        _lot_row(lot, product, variant, suppliers)
                    )
            rows.sort(
                key=lambda row: (row.received_at, row.lot_id),
                reverse=True,
            )
            return tuple(rows)

    def list_movements(self) -> tuple[InventoryMovementRow, ...]:
        with self._unit_of_work.unit_of_work() as uow:
            rows: list[InventoryMovementRow] = []
            for product, variant in _all_variants(
                uow.products, uow.variants
            ):
                for movement in uow.inventory_movements.list_by_variant(
                    variant.id
                ):
                    if movement.id is None:
                        continue
                    rows.append(
                        _movement_row(movement, product, variant)
                    )
            rows.sort(
                key=lambda row: (row.movement_date, row.movement_id),
                reverse=True,
            )
            return tuple(rows)


def _all_variants(products_repository, variants_repository):
    for product in products_repository.list_all(include_inactive=True):
        if product.id is None:
            continue
        for variant in variants_repository.list_for_product(
            product.id, include_inactive=True
        ):
            if variant.id is not None:
                yield product, variant


def _lot_row(
    lot: InventoryLot,
    product: Product,
    variant: ProductVariant,
    suppliers: dict[int, str],
) -> InventoryLotRow:
    if lot.id is None or lot.purchase_item_id is None:
        raise RuntimeError("Persisted inventory lot has no identifier.")
    purchase = lot.purchase_item.purchase
    return InventoryLotRow(
        lot_id=lot.id,
        purchase_id=purchase.id if purchase.id is not None else 0,
        product_name=product.name,
        variant_name=variant.variant_name,
        sku=variant.sku,
        received_at=lot.received_at,
        acquired_quantity=lot.acquired_quantity,
        remaining_quantity=lot.remaining_quantity,
        unit_cost=lot.unit_cost,
        supplier_name=(
            suppliers.get(purchase.supplier_id)
            if purchase.supplier_id is not None
            else None
        ),
    )


def _movement_row(
    movement: InventoryMovement,
    product: Product,
    variant: ProductVariant,
) -> InventoryMovementRow:
    if movement.id is None:
        raise RuntimeError("Persisted inventory movement has no identifier.")
    return InventoryMovementRow(
        movement_id=movement.id,
        movement_date=movement.movement_date,
        movement_type=movement.movement_type,
        product_name=product.name,
        variant_name=variant.variant_name,
        sku=variant.sku,
        quantity=movement.quantity,
        lot_id=movement.inventory_lot_id,
        unit_cost=movement.unit_cost,
        reference_type=movement.reference_type,
        reference_id=movement.reference_id,
        notes=movement.notes,
    )
