"""ORM model for the ``sales`` table."""

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
from app.infrastructure.database.models.customer import CustomerModel
from app.infrastructure.database.timestamp import utc_now
from app.infrastructure.database.types import ExactDecimal, UtcDateTime

_SALE_STATUSES = (
    "COMPLETED",
    "PARTIALLY_REFUNDED",
    "REFUNDED",
    "CANCELLED",
)


class SaleModel(Base):
    __tablename__ = "sales"
    __table_args__ = (
        CheckConstraint(
            "status IN ("
            + ", ".join(f"'{value}'" for value in _SALE_STATUSES)
            + ")",
            name="status_valid",
        ),
        CheckConstraint(
            "discount_amount IS NULL OR discount_amount >= 0",
            name="discount_amount_non_negative",
        ),
        Index("ix_sales_sale_date", "sale_date"),
        Index("ix_sales_customer_id", "customer_id"),
        Index("ix_sales_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int | None] = mapped_column(
        ForeignKey("customers.id")
    )
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id"), nullable=False
    )
    currency_id: Mapped[int] = mapped_column(
        ForeignKey("currencies.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    sale_date: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False
    )
    discount_amount: Mapped[Decimal | None] = mapped_column(
        ExactDecimal(24, 6)
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, default=utc_now, onupdate=utc_now
    )

    customer: Mapped[CustomerModel | None] = relationship(lazy="joined")
    account: Mapped[AccountModel] = relationship(lazy="joined")
    currency: Mapped[CurrencyModel] = relationship(lazy="joined")
