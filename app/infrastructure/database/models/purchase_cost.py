"""ORM model for the ``purchase_costs`` table."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base
from app.infrastructure.database.models.currency import CurrencyModel
from app.infrastructure.database.models.exchange_rate import ExchangeRateModel
from app.infrastructure.database.models.purchase import PurchaseModel
from app.infrastructure.database.timestamp import utc_now
from app.infrastructure.database.types import ExactDecimal, UtcDateTime

_COST_TYPES = (
    "SHIPPING",
    "TRANSPORTATION",
    "TAX",
    "COMMISSION",
    "PACKAGING",
    "CUSTOMS",
    "OTHER",
)
_ALLOCATION_METHODS = (
    "BY_QUANTITY",
    "BY_VALUE",
    "BY_WEIGHT",
    "MANUAL",
)


class PurchaseCostModel(Base):
    __tablename__ = "purchase_costs"
    __table_args__ = (
        CheckConstraint(
            "cost_type IN ("
            + ", ".join(f"'{value}'" for value in _COST_TYPES)
            + ")",
            name="cost_type_valid",
        ),
        CheckConstraint(
            "allocation_method IN ("
            + ", ".join(f"'{value}'" for value in _ALLOCATION_METHODS)
            + ")",
            name="allocation_method_valid",
        ),
        Index("ix_purchase_costs_purchase_id", "purchase_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    purchase_id: Mapped[int] = mapped_column(
        ForeignKey("purchases.id"), nullable=False
    )
    cost_type: Mapped[str] = mapped_column(String(32), nullable=False)
    amount: Mapped[Decimal] = mapped_column(
        ExactDecimal(24, 6), nullable=False
    )
    currency_id: Mapped[int] = mapped_column(
        ForeignKey("currencies.id"), nullable=False
    )
    exchange_rate_id: Mapped[int | None] = mapped_column(
        ForeignKey("exchange_rates.id")
    )
    allocation_method: Mapped[str] = mapped_column(
        String(32), nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, default=utc_now
    )

    purchase: Mapped[PurchaseModel] = relationship(lazy="joined")
    currency: Mapped[CurrencyModel] = relationship(lazy="joined")
    exchange_rate: Mapped[ExchangeRateModel | None] = relationship(
        lazy="joined"
    )
