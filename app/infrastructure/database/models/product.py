"""ORM model for the ``products`` table."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base
from app.infrastructure.database.models.currency import CurrencyModel
from app.infrastructure.database.timestamp import utc_now
from app.infrastructure.database.types import ExactDecimal, UtcDateTime


class ProductModel(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint(
            "(default_selling_price IS NULL) = (selling_currency_id IS NULL)",
            name="selling_price_currency_pair",
        ),
        Index("ix_products_category_id", "category_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id")
    )
    description: Mapped[str | None] = mapped_column(Text)
    brand: Mapped[str | None] = mapped_column(String(100))
    default_selling_price: Mapped[Decimal | None] = mapped_column(
        ExactDecimal(24, 6)
    )
    selling_currency_id: Mapped[int | None] = mapped_column(
        ForeignKey("currencies.id")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, default=utc_now, onupdate=utc_now
    )

    selling_currency: Mapped[CurrencyModel | None] = relationship(
        lazy="joined"
    )
