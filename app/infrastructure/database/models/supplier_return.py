"""ORM model for the ``supplier_returns`` table."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base
from app.infrastructure.database.models.account import AccountModel
from app.infrastructure.database.models.currency import CurrencyModel
from app.infrastructure.database.models.purchase import PurchaseModel
from app.infrastructure.database.models.supplier import SupplierModel
from app.infrastructure.database.timestamp import utc_now
from app.infrastructure.database.types import ExactDecimal, UtcDateTime


class SupplierReturnModel(Base):
    __tablename__ = "supplier_returns"
    __table_args__ = (
        CheckConstraint(
            "refund_amount IS NULL OR refund_amount > 0",
            name="refund_amount_positive",
        ),
        CheckConstraint(
            "(refund_amount IS NULL AND refund_currency_id IS NULL AND "
            "account_id IS NULL) OR (refund_amount IS NOT NULL AND "
            "refund_currency_id IS NOT NULL AND account_id IS NOT NULL)",
            name="refund_complete",
        ),
        Index("ix_supplier_returns_purchase_id", "purchase_id"),
        Index("ix_supplier_returns_return_date", "return_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    purchase_id: Mapped[int] = mapped_column(
        ForeignKey("purchases.id"), nullable=False
    )
    supplier_id: Mapped[int | None] = mapped_column(
        ForeignKey("suppliers.id")
    )
    account_id: Mapped[int | None] = mapped_column(
        ForeignKey("accounts.id")
    )
    refund_amount: Mapped[Decimal | None] = mapped_column(
        ExactDecimal(24, 6)
    )
    refund_currency_id: Mapped[int | None] = mapped_column(
        ForeignKey("currencies.id")
    )
    return_date: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, default=utc_now
    )

    purchase: Mapped[PurchaseModel] = relationship(lazy="joined")
    supplier: Mapped[SupplierModel | None] = relationship(lazy="joined")
    account: Mapped[AccountModel | None] = relationship(lazy="joined")
    refund_currency: Mapped[CurrencyModel | None] = relationship(
        lazy="joined"
    )
