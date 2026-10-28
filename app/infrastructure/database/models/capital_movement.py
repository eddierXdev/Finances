"""ORM model for the ``capital_movements`` table."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base
from app.infrastructure.database.models.account import AccountModel
from app.infrastructure.database.models.currency import CurrencyModel
from app.infrastructure.database.timestamp import utc_now
from app.infrastructure.database.types import ExactDecimal, UtcDateTime


class CapitalMovementModel(Base):
    __tablename__ = "capital_movements"
    __table_args__ = (
        CheckConstraint(
            "movement_type IN ('CONTRIBUTION', 'WITHDRAWAL')",
            name="movement_type_valid",
        ),
        Index("ix_capital_movements_account_id", "account_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id"), nullable=False
    )
    movement_type: Mapped[str] = mapped_column(String(16), nullable=False)
    amount: Mapped[Decimal] = mapped_column(
        ExactDecimal(24, 6), nullable=False
    )
    currency_id: Mapped[int] = mapped_column(
        ForeignKey("currencies.id"), nullable=False
    )
    movement_date: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, default=utc_now
    )

    account: Mapped[AccountModel] = relationship(lazy="joined")
    currency: Mapped[CurrencyModel] = relationship(lazy="joined")
