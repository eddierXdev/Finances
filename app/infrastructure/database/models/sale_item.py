"""ORM model for the ``sale_items`` table."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base
from app.infrastructure.database.models.sale import SaleModel
from app.infrastructure.database.timestamp import utc_now
from app.infrastructure.database.types import ExactDecimal, UtcDateTime


class SaleItemModel(Base):
    __tablename__ = "sale_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint(
            "unit_price >= 0", name="unit_price_non_negative"
        ),
        CheckConstraint(
            "discount_amount IS NULL OR discount_amount >= 0",
            name="discount_amount_non_negative",
        ),
        Index("ix_sale_items_sale_id", "sale_id"),
        Index("ix_sale_items_variant_id", "variant_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sale_id: Mapped[int] = mapped_column(
        ForeignKey("sales.id"), nullable=False
    )
    variant_id: Mapped[int] = mapped_column(
        ForeignKey("product_variants.id"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(
        ExactDecimal(24, 6), nullable=False
    )
    discount_amount: Mapped[Decimal | None] = mapped_column(
        ExactDecimal(24, 6)
    )
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, default=utc_now
    )

    sale: Mapped[SaleModel] = relationship(lazy="joined")
