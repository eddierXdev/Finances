"""Capital movement types."""

from enum import StrEnum


class CapitalMovementType(StrEnum):
    """Supported capital directions."""

    CONTRIBUTION = "CONTRIBUTION"
    WITHDRAWAL = "WITHDRAWAL"
