"""ORM model for the ``inventory_movements`` table."""

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
from app.infrastructure.database.models.currency import CurrencyModel
from app.infrastructure.database.models.inventory_lot import InventoryLotModel
from app.infrastructure.database.timestamp import utc_now
from app.infrastructure.database.types import ExactDecimal, UtcDateTime

_MOVEMENT_TYPES = (
    "PURCHASE_RECEIVED",
    "SALE",
    "CUSTOMER_RETURN",
    "SUPPLIER_RETURN",
    "ADJUSTMENT_IN",
    "ADJUSTMENT_OUT",
    "DAMAGED",
    "LOST",
)
_POSITIVE_TYPES = (
    "PURCHASE_RECEIVED",
    "CUSTOMER_RETURN",
    "ADJUSTMENT_IN",
)
_NEGATIVE_TYPES = (
    "SALE",
    "SUPPLIER_RETURN",
    "ADJUSTMENT_OUT",
    "DAMAGED",
    "LOST",
)


def _in_list(values: tuple[str, ...]) -> str:
    return "(" + ", ".join(f"'{value}'" for value in values) + ")"


class InventoryMovementModel(Base):
    __tablename__ = "inventory_movements"
    __table_args__ = (
        CheckConstraint(
            "movement_type IN " + _in_list(_MOVEMENT_TYPES),
            name="movement_type_valid",
        ),
        CheckConstraint(
            "(quantity > 0 AND movement_type IN "
            + _in_list(_POSITIVE_TYPES)
            + ") OR (quantity < 0 AND movement_type IN "
            + _in_list(_NEGATIVE_TYPES)
            + ")",
            name="quantity_sign_valid",
        ),
        CheckConstraint(
            "unit_cost IS NULL OR unit_cost >= 0",
            name="unit_cost_non_negative",
        ),
        Index("ix_inventory_movements_variant_id", "variant_id"),
        Index("ix_inventory_movements_movement_date", "movement_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    variant_id: Mapped[int] = mapped_column(
        ForeignKey("product_variants.id"), nullable=False
    )
    inventory_lot_id: Mapped[int | None] = mapped_column(
        ForeignKey("inventory_lots.id")
    )
    movement_type: Mapped[str] = mapped_column(String(32), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_cost: Mapped[Decimal | None] = mapped_column(ExactDecimal(24, 6))
    currency_id: Mapped[int | None] = mapped_column(
        ForeignKey("currencies.id")
    )
    reference_type: Mapped[str | None] = mapped_column(String(32))
    reference_id: Mapped[int | None] = mapped_column(Integer)
    movement_date: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, default=utc_now
    )

    inventory_lot: Mapped[InventoryLotModel | None] = relationship(
        lazy="joined"
    )
    currency: Mapped[CurrencyModel | None] = relationship(lazy="joined")
