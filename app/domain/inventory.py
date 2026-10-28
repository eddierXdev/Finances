"""Partial-receipt and lot-derived quantity rules."""

from __future__ import annotations

from collections.abc import Sequence

from app.domain.entities.inventory_lot import InventoryLot
from app.domain.entities.purchase import Purchase
from app.domain.entities.purchase_cost_allocation import (
    PurchaseCostAllocation,
)
from app.domain.entities.purchase_item import PurchaseItem
from app.domain.enums.purchase_status import PurchaseStatus
from app.domain.exceptions import (
    InvalidInventoryError,
    OverReceiptError,
)
from app.domain.purchase_costing import effective_acquisition_costs
from app.domain.value_objects.money import Money


def received_quantity(
    purchase_item: PurchaseItem, lots: Sequence[InventoryLot]
) -> int:
    """Return the units of ``purchase_item`` acquired through lots."""
    _require_persisted_item(purchase_item)
    return sum(
        lot.acquired_quantity
        for lot in lots
        if lot.purchase_item.id == purchase_item.id
    )


def remaining_quantity(
    purchase_item: PurchaseItem, lots: Sequence[InventoryLot]
) -> int:
    """Return the ordered quantity still pending receipt."""
    received = received_quantity(purchase_item, lots)
    if received > purchase_item.quantity:
        raise InvalidInventoryError(
            f"Purchase item {purchase_item.id} has {received} received "
            f"units but only {purchase_item.quantity} were ordered."
        )
    return purchase_item.quantity - received


def validate_receipt(
    purchase_item: PurchaseItem,
    lots: Sequence[InventoryLot],
    quantity: int,
) -> None:
    """Reject receipts that are not positive or exceed the ordered amount."""
    if (
        isinstance(quantity, bool)
        or not isinstance(quantity, int)
        or quantity <= 0
    ):
        raise InvalidInventoryError(
            "Received quantity must be a positive integer."
        )

    remaining = remaining_quantity(purchase_item, lots)
    if quantity > remaining:
        raise OverReceiptError(
            f"Cannot receive {quantity} units for purchase item "
            f"{purchase_item.id}; only {remaining} remain."
        )


def receipt_status(
    purchase: Purchase,
    items: Sequence[PurchaseItem],
    lots: Sequence[InventoryLot],
) -> PurchaseStatus:
    """Return the logistics status implied by the received quantities."""
    if not isinstance(purchase, Purchase):
        raise TypeError("receipt_status requires a Purchase.")
    if purchase.id is None:
        raise InvalidInventoryError(
            "The purchase must be persisted before receipt status is "
            "calculated."
        )
    if not items:
        raise InvalidInventoryError(
            "A purchase requires at least one item to receive."
        )

    total_received = 0
    fully_received = True
    for item in items:
        _require_persisted_item(item)
        if item.purchase.id != purchase.id:
            raise InvalidInventoryError(
                "All items must belong to the purchase being received."
            )
        total_received += received_quantity(item, lots)
        if remaining_quantity(item, lots) > 0:
            fully_received = False

    if total_received == 0:
        raise InvalidInventoryError(
            "Receipt status requires at least one received unit."
        )
    return (
        PurchaseStatus.RECEIVED
        if fully_received
        else PurchaseStatus.PARTIALLY_RECEIVED
    )


def effective_unit_cost(
    purchase_item: PurchaseItem,
    allocations: Sequence[PurchaseCostAllocation] = (),
) -> Money:
    """Return the item's cost per ordered unit, including allocated costs."""
    _require_persisted_item(purchase_item)
    totals = effective_acquisition_costs([purchase_item], allocations)
    return totals[purchase_item.id] / purchase_item.quantity


def _require_persisted_item(purchase_item: PurchaseItem) -> None:
    if not isinstance(purchase_item, PurchaseItem):
        raise TypeError("An InventoryLot rule requires a PurchaseItem.")
    if (
        purchase_item.id is None
        or purchase_item.purchase.id is None
    ):
        raise InvalidInventoryError(
            "Purchase items must be persisted before inventory rules apply."
        )
