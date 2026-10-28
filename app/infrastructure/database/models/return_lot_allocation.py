"""ORM model for the ``return_lot_allocations`` table."""

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
from app.infrastructure.database.models.customer_return_item import (
    CustomerReturnItemModel,
)
from app.infrastructure.database.models.sale_item_lot_allocation import (
    SaleItemLotAllocationModel,
)
from app.infrastructure.database.timestamp import utc_now
from app.infrastructure.database.types import ExactDecimal, UtcDateTime


class ReturnLotAllocationModel(Base):
    __tablename__ = "return_lot_allocations"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint(
            "unit_cost_snapshot >= 0",
            name="unit_cost_snapshot_non_negative",
        ),
        Index(
            "ix_return_lot_allocations_customer_return_item_id",
            "customer_return_item_id",
        ),
        Index(
            "ix_return_lot_allocations_sale_item_lot_allocation_id",
            "sale_item_lot_allocation_id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_return_item_id: Mapped[int] = mapped_column(
        ForeignKey("customer_return_items.id"), nullable=False
    )
    sale_item_lot_allocation_id: Mapped[int] = mapped_column(
        ForeignKey("sale_item_lot_allocations.id"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_cost_snapshot: Mapped[Decimal] = mapped_column(
        ExactDecimal(24, 6), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, default=utc_now
    )

    customer_return_item: Mapped[CustomerReturnItemModel] = relationship(
        lazy="joined"
    )
    sale_item_lot_allocation: Mapped[SaleItemLotAllocationModel] = (
        relationship(lazy="joined")
    )
