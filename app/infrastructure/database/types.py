"""Custom column types that keep exact monetary values and UTC timestamps."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, String
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator


class ExactDecimal(TypeDecorator[Decimal]):
    """Store ``Decimal`` values without binary floating-point conversion.

    SQLite has no exact decimal type, and its NUMERIC affinity stores values
    as REAL. On SQLite this type uses text storage; other backends use NUMERIC.
    """

    impl = Numeric
    cache_ok = True

    def __init__(self, precision: int = 24, scale: int = 12) -> None:
        self.precision = precision
        self.scale = scale
        super().__init__()

    def load_dialect_impl(self, dialect: Dialect):
        if dialect.name == "sqlite":
            return dialect.type_descriptor(String())
        return dialect.type_descriptor(Numeric(self.precision, self.scale))

    def process_bind_param(self, value: Decimal | None, dialect: Dialect):
        if value is None:
            return None
        decimal_value = value if isinstance(value, Decimal) else Decimal(str(value))
        if dialect.name == "sqlite":
            return format(decimal_value, "f")
        return decimal_value

    def process_result_value(self, value: object, dialect: Dialect) -> Decimal | None:
        if value is None:
            return None
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))


class UtcDateTime(TypeDecorator[datetime]):
    """Persist timezone-aware datetimes as UTC and read them back as UTC."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect):
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Naive datetimes are not accepted; use UTC-aware values.")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value: object, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if not isinstance(value, datetime):
            raise TypeError(f"Expected datetime from database, got {type(value)!r}.")
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
