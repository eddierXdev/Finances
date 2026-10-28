"""ORM model for the ``suppliers`` table."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base
from app.infrastructure.database.timestamp import utc_now
from app.infrastructure.database.types import UtcDateTime


class SupplierModel(Base):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    supplier_type: Mapped[str | None] = mapped_column(String(50))
    website: Mapped[str | None] = mapped_column(String(255))
    contact: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, default=utc_now, onupdate=utc_now
    )
