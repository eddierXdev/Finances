"""ORM model for the ``currencies`` table."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base
from app.infrastructure.database.timestamp import utc_now
from app.infrastructure.database.types import UtcDateTime


class CurrencyModel(Base):
    __tablename__ = "currencies"
    __table_args__ = (
        CheckConstraint(
            "decimal_places >= 0 AND decimal_places <= 6",
            name="decimal_places_range",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(3), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    symbol: Mapped[str | None] = mapped_column(String(10))
    decimal_places: Mapped[int] = mapped_column(Integer, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, default=utc_now
    )
