"""Historical lot reversal created by a customer return."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.entities.customer_return_item import CustomerReturnItem
from app.domain.entities.sale_item_lot_allocation import (
    SaleItemLotAllocation,
)
from app.domain.exceptions import InvalidCustomerReturnError
from app.domain.value_objects.money import Money


@dataclass(frozen=True, slots=True)
class ReturnLotAllocation:
    """The quantity and historical cost reversed from one sale allocation.

    The inventory lot is intentionally not duplicated: it is reached through
    the original sale allocation.
    """

    customer_return_item: CustomerReturnItem
    sale_item_lot_allocation: SaleItemLotAllocation
    quantity: int
    unit_cost_snapshot: Money
    id: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.customer_return_item, CustomerReturnItem):
            raise TypeError(
                "ReturnLotAllocation requires a CustomerReturnItem."
            )
        if not isinstance(
            self.sale_item_lot_allocation, SaleItemLotAllocation
        ):
            raise TypeError(
                "ReturnLotAllocation requires a SaleItemLotAllocation."
            )

        if self.customer_return_item.id is None:
            raise InvalidCustomerReturnError(
                "ReturnLotAllocation requires a persisted return item."
            )
        if self.sale_item_lot_allocation.id is None:
            raise InvalidCustomerReturnError(
                "ReturnLotAllocation requires a persisted sale allocation."
            )

        if (
            self.customer_return_item.sale_item.id
            != self.sale_item_lot_allocation.sale_item.id
        ):
            raise InvalidCustomerReturnError(
                "A return allocation must match the original sale item."
            )

        if (
            isinstance(self.quantity, bool)
            or not isinstance(self.quantity, int)
            or self.quantity <= 0
        ):
            raise InvalidCustomerReturnError(
                "ReturnLotAllocation quantity must be a positive integer."
            )
        if self.quantity > self.sale_item_lot_allocation.quantity:
            raise InvalidCustomerReturnError(
                "A return allocation cannot exceed the original allocation "
                "quantity."
            )

        if not isinstance(self.unit_cost_snapshot, Money):
            raise TypeError(
                "ReturnLotAllocation unit_cost_snapshot must be Money."
            )
        if self.unit_cost_snapshot.is_negative:
            raise InvalidCustomerReturnError(
                "ReturnLotAllocation unit_cost_snapshot cannot be negative."
            )
        if (
            self.unit_cost_snapshot
            != self.sale_item_lot_allocation.unit_cost_snapshot
        ):
            raise InvalidCustomerReturnError(
                "A return allocation must preserve the original historical "
                "unit cost."
            )

        if self.id is not None:
            if (
                isinstance(self.id, bool)
                or not isinstance(self.id, int)
                or self.id <= 0
            ):
                raise ValueError(
                    "ReturnLotAllocation id must be a positive integer."
                )

    @property
    def customer_return_item_id(self) -> int | None:
        return self.customer_return_item.id

    @property
    def sale_item_lot_allocation_id(self) -> int | None:
        return self.sale_item_lot_allocation.id

    @property
    def inventory_lot_id(self) -> int | None:
        return self.sale_item_lot_allocation.inventory_lot.id

    @property
    def cost(self) -> Money:
        return self.unit_cost_snapshot * self.quantity
