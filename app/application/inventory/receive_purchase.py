"""Receive a purchase and create traceable inventory lots."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.domain.entities.inventory_lot import InventoryLot
from app.domain.entities.inventory_movement import InventoryMovement
from app.domain.entities.purchase import Purchase
from app.domain.enums.inventory_movement_type import InventoryMovementType
from app.domain.exceptions import (
    InvalidInventoryError,
    PurchaseItemNotFoundError,
    PurchaseNotFoundError,
)
from app.domain.inventory import (
    effective_unit_cost,
    receipt_status,
    validate_receipt,
)
from app.domain.repositories.inventory_lot_repository import (
    InventoryLotRepository,
)
from app.domain.repositories.inventory_movement_repository import (
    InventoryMovementRepository,
)
from app.domain.repositories.purchase_cost_allocation_repository import (
    PurchaseCostAllocationRepository,
)
from app.domain.repositories.purchase_item_repository import (
    PurchaseItemRepository,
)
from app.domain.repositories.purchase_repository import PurchaseRepository

_PURCHASE_REFERENCE = "PURCHASE"


@dataclass(frozen=True, slots=True)
class ReceiptItemRequest:
    """One purchase item and the quantity arriving in this receipt."""

    purchase_item_id: int
    quantity: int


@dataclass(frozen=True, slots=True)
class ReceivePurchaseRequest:
    """Input for receiving one delivery of a purchase."""

    purchase_id: int
    items: tuple[ReceiptItemRequest, ...]
    received_at: datetime
    notes: str | None = None


@dataclass(frozen=True, slots=True)
class ReceivedPurchase:
    """The purchase and the inventory rows created by one receipt."""

    purchase: Purchase
    lots: tuple[InventoryLot, ...]
    movements: tuple[InventoryMovement, ...]


class ReceivePurchase:
    """Create lots and ``PURCHASE_RECEIVED`` movements for a delivery.

    Every quantity and the resulting purchase status are validated before
    anything is written. The caller must still run this use case inside a
    database transaction so a persistence failure rolls back the receipt.
    """

    def __init__(
        self,
        purchases: PurchaseRepository,
        items: PurchaseItemRepository,
        allocations: PurchaseCostAllocationRepository,
        lots: InventoryLotRepository,
        movements: InventoryMovementRepository,
    ) -> None:
        self._purchases = purchases
        self._items = items
        self._allocations = allocations
        self._lots = lots
        self._movements = movements

    def execute(
        self, request: ReceivePurchaseRequest
    ) -> ReceivedPurchase:
        if not request.items:
            raise InvalidInventoryError(
                "A receipt requires at least one purchase item."
            )

        requested_ids = [
            item.purchase_item_id for item in request.items
        ]
        if len(set(requested_ids)) != len(requested_ids):
            raise InvalidInventoryError(
                "A receipt cannot list the same purchase item twice."
            )

        purchase = self._purchases.get_by_id(request.purchase_id)
        if purchase is None:
            raise PurchaseNotFoundError(
                f"Purchase {request.purchase_id} does not exist."
            )

        purchase_items = self._items.list_for_purchase(purchase.id)
        items_by_id = {
            item.id: item
            for item in purchase_items
            if item.id is not None
        }
        if not items_by_id:
            raise InvalidInventoryError(
                "The purchase has no items to receive."
            )

        allocations = self._allocations.list_for_purchase(purchase.id)
        existing_lots = self._lots.list_for_purchase(purchase.id)

        planned_lots: list[InventoryLot] = []
        for receipt in request.items:
            item = items_by_id.get(receipt.purchase_item_id)
            if item is None:
                raise PurchaseItemNotFoundError(
                    f"Purchase item {receipt.purchase_item_id} does not "
                    f"belong to purchase {purchase.id}."
                )

            validate_receipt(
                item,
                (*existing_lots, *planned_lots),
                receipt.quantity,
            )

            item_allocations = [
                allocation
                for allocation in allocations
                if allocation.purchase_item.id == item.id
            ]
            planned_lots.append(
                InventoryLot(
                    purchase_item=item,
                    variant_id=item.variant_id,
                    acquired_quantity=receipt.quantity,
                    remaining_quantity=receipt.quantity,
                    unit_cost=effective_unit_cost(
                        item, item_allocations
                    ),
                    received_at=request.received_at,
                )
            )

        status = receipt_status(
            purchase,
            purchase_items,
            (*existing_lots, *planned_lots),
        )
        updated_purchase = purchase.transition_to(status)

        created_lots: list[InventoryLot] = []
        created_movements: list[InventoryMovement] = []
        for planned_lot in planned_lots:
            lot = self._lots.add(planned_lot)
            if lot.id is None:
                raise RuntimeError(
                    "Persisted inventory lot has no identifier."
                )

            movement = self._movements.add(
                InventoryMovement(
                    variant_id=lot.variant_id,
                    movement_type=(
                        InventoryMovementType.PURCHASE_RECEIVED
                    ),
                    quantity=lot.acquired_quantity,
                    movement_date=request.received_at,
                    inventory_lot_id=lot.id,
                    unit_cost=lot.unit_cost,
                    reference_type=_PURCHASE_REFERENCE,
                    reference_id=purchase.id,
                    notes=request.notes,
                )
            )
            created_lots.append(lot)
            created_movements.append(movement)

        return ReceivedPurchase(
            purchase=self._purchases.save(updated_purchase),
            lots=tuple(created_lots),
            movements=tuple(created_movements),
        )
