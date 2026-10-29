"""Small conversion helpers shared by desktop dialogs."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from PySide6.QtCore import QDate

from app.domain.entities.currency import Currency
from app.domain.value_objects.money import Money


def date_to_datetime(value: QDate) -> datetime:
    """Convert a date widget value to an aware UTC datetime."""
    return datetime(
        value.year(),
        value.month(),
        value.day(),
        tzinfo=UTC,
    )


def display_datetime(value: datetime) -> str:
    """Return a compact local presentation timestamp."""
    return value.astimezone(UTC).strftime("%Y-%m-%d %H:%M")


def display_money(values) -> str:
    """Render zero, one or several Money values without losing currency."""
    values = tuple(values)
    if not values:
        return "—"
    return " + ".join(str(value) for value in values)


def parse_money(text: str, currency: Currency, field: str) -> Money:
    """Parse a decimal amount into the requested native currency."""
    normalized = text.strip().replace(",", ".")
    if not normalized:
        raise ValueError(f"{field} is required.")
    try:
        amount = Decimal(normalized)
    except InvalidOperation as exc:
        raise ValueError(f"{field} must be a number.") from exc
    return Money(amount, currency)


def parse_optional_money(
    text: str, currency: Currency, field: str
) -> Money | None:
    """Parse an optional positive Money value."""
    if not text.strip():
        return None
    money = parse_money(text, currency, field)
    if not money.is_positive:
        raise ValueError(f"{field} must be greater than zero.")
    return money


def parse_optional_decimal(text: str, field: str) -> Decimal | None:
    """Parse an optional positive decimal used by rate forms."""
    normalized = text.strip().replace(",", ".")
    if not normalized:
        return None
    try:
        value = Decimal(normalized)
    except InvalidOperation as exc:
        raise ValueError(f"{field} must be a number.") from exc
    if not value.is_finite() or value <= 0:
        raise ValueError(f"{field} must be greater than zero.")
    return value
