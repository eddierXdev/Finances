"""ORM model for the ``sale_item_lot_allocations`` table."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base
from app.infrastructure.database.models.inventory_lot import InventoryLotModel
from app.infrastructure.database.models.sale_item import SaleItemModel
from app.infrastructure.database.timestamp import utc_now
from app.infrastructure.database.types import ExactDecimal, UtcDateTime


class SaleItemLotAllocationModel(Base):
    __tablename__ = "sale_item_lot_allocations"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint(
            "unit_cost_snapshot >= 0",
            name="unit_cost_snapshot_non_negative",
        ),
        Index(
            "ix_sale_item_lot_allocations_sale_item_id", "sale_item_id"
        ),
        Index(
            "ix_sale_item_lot_allocations_inventory_lot_id",
            "inventory_lot_id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sale_item_id: Mapped[int] = mapped_column(
        ForeignKey("sale_items.id"), nullable=False
    )
    inventory_lot_id: Mapped[int] = mapped_column(
        ForeignKey("inventory_lots.id"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_cost_snapshot: Mapped[Decimal] = mapped_column(
        ExactDecimal(24, 6), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, default=utc_now
    )

    sale_item: Mapped[SaleItemModel] = relationship(lazy="joined")
    inventory_lot: Mapped[InventoryLotModel] = relationship(lazy="joined")
