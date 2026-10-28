"""Purchase lifecycle statuses."""

from enum import StrEnum


class PurchaseStatus(StrEnum):
    """Logistics and payment status of a purchase."""

    PENDING = "PENDING"
    PURCHASED = "PURCHASED"
    SHIPPED = "SHIPPED"
    IN_TRANSIT = "IN_TRANSIT"
    PARTIALLY_RECEIVED = "PARTIALLY_RECEIVED"
    RECEIVED = "RECEIVED"
    CANCELLED = "CANCELLED"
