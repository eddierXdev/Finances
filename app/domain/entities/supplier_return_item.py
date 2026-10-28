"""Supplier return line entity."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.entities.inventory_lot import InventoryLot
from app.domain.entities.purchase_item import PurchaseItem
from app.domain.entities.supplier_return import SupplierReturn
from app.domain.exceptions import (
    InvalidSupplierReturnError,
    InvalidSupplierReturnLotError,
)
from app.domain.value_objects.money import Money


@dataclass(frozen=True, slots=True)
class SupplierReturnItem:
    """A quantity of one purchase item returned from one exact inventory lot.

    The current remaining quantity is intentionally not checked here: this
    entity also maps historical returns after later stock movements. The
    register use case enforces the eligible remaining inventory before writing.
    """

    supplier_return: SupplierReturn
    purchase_item: PurchaseItem
    inventory_lot: InventoryLot
    quantity: int
    unit_cost_snapshot: Money
    id: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.supplier_return, SupplierReturn):
            raise TypeError(
                "SupplierReturnItem requires a SupplierReturn."
            )
        if not isinstance(self.purchase_item, PurchaseItem):
            raise TypeError("SupplierReturnItem requires a PurchaseItem.")
        if not isinstance(self.inventory_lot, InventoryLot):
            raise TypeError(
                "SupplierReturnItem requires an InventoryLot."
            )

        if self.purchase_item.id is None:
            raise InvalidSupplierReturnError(
                "SupplierReturnItem requires a persisted purchase item."
            )
        if self.inventory_lot.id is None:
            raise InvalidSupplierReturnError(
                "SupplierReturnItem requires a persisted inventory lot."
            )

        if (
            self.purchase_item.purchase.id
            != self.supplier_return.purchase.id
        ):
            raise InvalidSupplierReturnError(
                "A returned item must belong to the original purchase."
            )

        if (
            self.inventory_lot.purchase_item.id
            != self.purchase_item.id
            or self.inventory_lot.variant_id
            != self.purchase_item.variant_id
        ):
            raise InvalidSupplierReturnLotError(
                "A supplier return lot must belong to the original "
                "purchase item."
            )

        if (
            isinstance(self.quantity, bool)
            or not isinstance(self.quantity, int)
            or self.quantity <= 0
        ):
            raise InvalidSupplierReturnError(
                "SupplierReturnItem quantity must be a positive integer."
            )
        if self.quantity > self.inventory_lot.acquired_quantity:
            raise InvalidSupplierReturnError(
                "A supplier return cannot exceed the lot's acquired "
                "quantity."
            )

        if not isinstance(self.unit_cost_snapshot, Money):
            raise TypeError(
                "SupplierReturnItem unit_cost_snapshot must be Money."
            )
        if self.unit_cost_snapshot != self.inventory_lot.unit_cost:
            raise InvalidSupplierReturnError(
                "A supplier return must preserve the lot's historical unit "
                "cost."
            )

        if self.id is not None:
            if (
                isinstance(self.id, bool)
                or not isinstance(self.id, int)
                or self.id <= 0
            ):
                raise ValueError(
                    "SupplierReturnItem id must be a positive integer."
                )

    @property
    def supplier_return_id(self) -> int | None:
        return self.supplier_return.id

    @property
    def purchase_item_id(self) -> int | None:
        return self.purchase_item.id

    @property
    def inventory_lot_id(self) -> int | None:
        return self.inventory_lot.id

    @property
    def cost(self) -> Money:
        return self.unit_cost_snapshot * self.quantity
