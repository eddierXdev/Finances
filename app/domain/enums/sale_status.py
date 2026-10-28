"""Sale lifecycle statuses."""

from enum import StrEnum


class SaleStatus(StrEnum):
    """Collection and refund status of a sale."""

    COMPLETED = "COMPLETED"
    PARTIALLY_REFUNDED = "PARTIALLY_REFUNDED"
    REFUNDED = "REFUNDED"
    CANCELLED = "CANCELLED"
