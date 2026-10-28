"""ORM model for the ``accounts`` table."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base
from app.infrastructure.database.models.currency import CurrencyModel
from app.infrastructure.database.timestamp import utc_now
from app.infrastructure.database.types import UtcDateTime


class AccountModel(Base):
    __tablename__ = "accounts"
    __table_args__ = (
        Index("ix_accounts_currency_id", "currency_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    currency_id: Mapped[int] = mapped_column(
        ForeignKey("currencies.id"), nullable=False
    )
    account_type: Mapped[str | None] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, default=utc_now, onupdate=utc_now
    )

    currency: Mapped[CurrencyModel] = relationship(lazy="joined")
