"""Shared decimal rules for monetary values.

Monetary values are always ``Decimal``; floats are rejected at the boundary.
Amounts are rounded half-up to the precision supported by their currency.
"""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

MAX_DECIMAL_PLACES = 6


def to_decimal(value: Decimal | int | str) -> Decimal:
    """Convert a safe monetary input to ``Decimal``, rejecting floats."""
    if isinstance(value, bool) or isinstance(value, float):
        raise TypeError("Monetary values must be Decimal, int or str, never float.")

    if isinstance(value, Decimal):
        result = value
    elif isinstance(value, int):
        result = Decimal(value)
    elif isinstance(value, str):
        try:
            result = Decimal(value.strip())
        except InvalidOperation as exc:
            raise ValueError(f"Invalid decimal value: {value!r}") from exc
    else:
        raise TypeError(f"Unsupported monetary value type: {type(value).__name__}")

    if not result.is_finite():
        raise ValueError("Monetary values must be finite.")

    return result


def quantize_amount(amount: Decimal, decimal_places: int) -> Decimal:
    """Round ``amount`` half-up to ``decimal_places`` fractional digits."""
    exponent = Decimal(1).scaleb(-decimal_places)
    return amount.quantize(exponent, rounding=ROUND_HALF_UP)
