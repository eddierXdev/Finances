"""ORM model for the ``product_variants`` table."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base
from app.infrastructure.database.timestamp import utc_now
from app.infrastructure.database.types import UtcDateTime


class ProductVariantModel(Base):
    __tablename__ = "product_variants"
    __table_args__ = (
        Index("ix_product_variants_product_id", "product_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"), nullable=False
    )
    sku: Mapped[str | None] = mapped_column(String(100), unique=True)
    variant_name: Mapped[str | None] = mapped_column(String(150))
    barcode: Mapped[str | None] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, default=utc_now, onupdate=utc_now
    )
