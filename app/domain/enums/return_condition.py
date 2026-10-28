"""Customer return conditions supported by V1."""

from enum import StrEnum


class ReturnCondition(StrEnum):
    """Whether a returned unit can re-enter sellable stock."""

    SELLABLE = "SELLABLE"
    DAMAGED = "DAMAGED"
