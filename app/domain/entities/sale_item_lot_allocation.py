"""Immutable FIFO allocation snapshot for a sale item."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.entities.inventory_lot import InventoryLot
from app.domain.entities.sale_item import SaleItem
from app.domain.exceptions import InvalidSaleError
from app.domain.value_objects.money import Money


@dataclass(frozen=True, slots=True)
class SaleItemLotAllocation:
    """The quantity and historical unit cost taken from one lot."""

    sale_item: SaleItem
    inventory_lot: InventoryLot
    quantity: int
    unit_cost_snapshot: Money
    id: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.sale_item, SaleItem):
            raise TypeError("SaleItemLotAllocation requires a SaleItem.")
        if not isinstance(self.inventory_lot, InventoryLot):
            raise TypeError(
                "SaleItemLotAllocation requires an InventoryLot."
            )
        if self.sale_item.id is None:
            raise InvalidSaleError(
                "SaleItemLotAllocation requires a persisted sale item."
            )
        if self.inventory_lot.id is None:
            raise InvalidSaleError(
                "SaleItemLotAllocation requires a persisted inventory lot."
            )

        if self.sale_item.variant_id != self.inventory_lot.variant_id:
            raise InvalidSaleError(
                "Allocation variant must match the sale item variant."
            )

        if (
            isinstance(self.quantity, bool)
            or not isinstance(self.quantity, int)
            or self.quantity <= 0
        ):
            raise InvalidSaleError(
                "Allocation quantity must be a positive integer."
            )
        if self.quantity > self.inventory_lot.acquired_quantity:
            raise InvalidSaleError(
                "Allocation quantity cannot exceed the lot's acquired "
                "quantity."
            )

        if not isinstance(self.unit_cost_snapshot, Money):
            raise TypeError(
                "Allocation unit_cost_snapshot must be Money."
            )
        if self.unit_cost_snapshot.is_negative:
            raise InvalidSaleError(
                "Allocation unit_cost_snapshot cannot be negative."
            )
        if (
            self.unit_cost_snapshot.currency.code
            != self.inventory_lot.unit_cost.currency.code
        ):
            raise InvalidSaleError(
                "Allocation cost currency must match the lot cost currency."
            )
        if self.unit_cost_snapshot != self.inventory_lot.unit_cost:
            raise InvalidSaleError(
                "Allocation unit_cost_snapshot must equal the lot unit cost."
            )

        if self.id is not None:
            if (
                isinstance(self.id, bool)
                or not isinstance(self.id, int)
                or self.id <= 0
            ):
                raise ValueError(
                    "SaleItemLotAllocation id must be a positive integer."
                )

    @property
    def cogs(self) -> Money:
        return self.unit_cost_snapshot * self.quantity
