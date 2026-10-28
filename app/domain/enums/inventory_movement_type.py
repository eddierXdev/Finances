"""Inventory movement types and their stock direction."""

from enum import StrEnum


class InventoryMovementType(StrEnum):
    """The business reason for a stock change."""

    PURCHASE_RECEIVED = "PURCHASE_RECEIVED"
    SALE = "SALE"
    CUSTOMER_RETURN = "CUSTOMER_RETURN"
    SUPPLIER_RETURN = "SUPPLIER_RETURN"
    ADJUSTMENT_IN = "ADJUSTMENT_IN"
    ADJUSTMENT_OUT = "ADJUSTMENT_OUT"
    DAMAGED = "DAMAGED"
    LOST = "LOST"
