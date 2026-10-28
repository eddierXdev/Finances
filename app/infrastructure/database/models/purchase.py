"""ORM model for the ``purchases`` table."""

from __future__ import annotations

from datetime import datetime

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
from app.infrastructure.database.models.supplier import SupplierModel
from app.infrastructure.database.timestamp import utc_now
from app.infrastructure.database.types import UtcDateTime

_PURCHASE_STATUSES = (
    "PENDING",
    "PURCHASED",
    "SHIPPED",
    "IN_TRANSIT",
    "PARTIALLY_RECEIVED",
    "RECEIVED",
    "CANCELLED",
)


class PurchaseModel(Base):
    __tablename__ = "purchases"
    __table_args__ = (
        CheckConstraint(
            "status IN ("
            + ", ".join(f"'{value}'" for value in _PURCHASE_STATUSES)
            + ")",
            name="status_valid",
        ),
        Index("ix_purchases_purchase_date", "purchase_date"),
        Index("ix_purchases_status", "status"),
        Index("ix_purchases_supplier_id", "supplier_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    supplier_id: Mapped[int | None] = mapped_column(
        ForeignKey("suppliers.id")
    )
    account_id: Mapped[int | None] = mapped_column(
        ForeignKey("accounts.id")
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    currency_id: Mapped[int] = mapped_column(
        ForeignKey("currencies.id"), nullable=False
    )
    purchase_date: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False
    )
    order_number: Mapped[str | None] = mapped_column(String(100))
    tracking_number: Mapped[str | None] = mapped_column(String(100))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, default=utc_now, onupdate=utc_now
    )

    supplier: Mapped[SupplierModel | None] = relationship(lazy="joined")
    account: Mapped[AccountModel | None] = relationship(lazy="joined")
    currency: Mapped[CurrencyModel] = relationship(lazy="joined")
