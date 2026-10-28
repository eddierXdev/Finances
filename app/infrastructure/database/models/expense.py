"""ORM model for the ``expenses`` table."""

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

_EXPENSE_TYPES = (
    "ADVERTISING",
    "TRANSPORTATION",
    "PACKAGING",
    "INTERNET",
    "DELIVERY",
    "COMMISSION",
    "OTHER",
)


class ExpenseModel(Base):
    __tablename__ = "expenses"
    __table_args__ = (
        CheckConstraint(
            "expense_type IN ("
            + ", ".join(f"'{value}'" for value in _EXPENSE_TYPES)
            + ")",
            name="expense_type_valid",
        ),
        CheckConstraint("amount > 0", name="amount_positive"),
        Index("ix_expenses_account_id", "account_id"),
        Index("ix_expenses_expense_date", "expense_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id"), nullable=False
    )
    expense_type: Mapped[str] = mapped_column(String(32), nullable=False)
    amount: Mapped[Decimal] = mapped_column(
        ExactDecimal(24, 6), nullable=False
    )
    currency_id: Mapped[int] = mapped_column(
        ForeignKey("currencies.id"), nullable=False
    )
    expense_date: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, default=utc_now
    )

    account: Mapped[AccountModel] = relationship(lazy="joined")
    currency: Mapped[CurrencyModel] = relationship(lazy="joined")
