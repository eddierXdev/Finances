"""Purchase additional-cost types."""

from enum import StrEnum


class PurchaseCostType(StrEnum):
    """Categories of acquisition costs."""

    SHIPPING = "SHIPPING"
    TRANSPORTATION = "TRANSPORTATION"
    TAX = "TAX"
    COMMISSION = "COMMISSION"
    PACKAGING = "PACKAGING"
    CUSTOMS = "CUSTOMS"
    OTHER = "OTHER"
