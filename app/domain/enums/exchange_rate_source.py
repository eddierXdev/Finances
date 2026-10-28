"""Exchange-rate sources."""

from enum import StrEnum


class ExchangeRateSource(StrEnum):
    """Supported origins for a stored exchange rate."""

    MANUAL = "MANUAL"
    ELTOQUE = "ELTOQUE"
