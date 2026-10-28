"""Purchase cost allocation methods."""

from enum import StrEnum


class AllocationMethod(StrEnum):
    """Supported ways to distribute a purchase cost across items."""

    BY_QUANTITY = "BY_QUANTITY"
    BY_VALUE = "BY_VALUE"
    BY_WEIGHT = "BY_WEIGHT"
    MANUAL = "MANUAL"
