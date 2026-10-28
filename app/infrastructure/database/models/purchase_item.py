"""ORM model for the ``purchase_items`` table."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base
from app.infrastructure.database.models.purchase import PurchaseModel
from app.infrastructure.database.timestamp import utc_now
from app.infrastructure.database.types import ExactDecimal, UtcDateTime


class PurchaseItemModel(Base):
    __tablename__ = "purchase_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        Index("ix_purchase_items_purchase_id", "purchase_id"),
        Index("ix_purchase_items_variant_id", "variant_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    purchase_id: Mapped[int] = mapped_column(
        ForeignKey("purchases.id"), nullable=False
    )
    variant_id: Mapped[int] = mapped_column(
        ForeignKey("product_variants.id"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(
        ExactDecimal(24, 6), nullable=False
    )
    weight: Mapped[Decimal | None] = mapped_column(
        ExactDecimal(24, 6)
    )
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, default=utc_now
    )

    purchase: Mapped[PurchaseModel] = relationship(lazy="joined")
