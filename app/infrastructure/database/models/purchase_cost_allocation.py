"""ORM model for the ``purchase_cost_allocations`` table."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import (
    ForeignKey,
    Index,
    Integer,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base
from app.infrastructure.database.models.purchase_cost import PurchaseCostModel
from app.infrastructure.database.models.purchase_item import PurchaseItemModel
from app.infrastructure.database.types import ExactDecimal


class PurchaseCostAllocationModel(Base):
    __tablename__ = "purchase_cost_allocations"
    __table_args__ = (
        UniqueConstraint(
            "purchase_cost_id",
            "purchase_item_id",
            name="uq_purchase_cost_allocations_cost_item",
        ),
        Index(
            "ix_purchase_cost_allocations_purchase_item_id",
            "purchase_item_id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    purchase_cost_id: Mapped[int] = mapped_column(
        ForeignKey("purchase_costs.id"), nullable=False
    )
    purchase_item_id: Mapped[int] = mapped_column(
        ForeignKey("purchase_items.id"), nullable=False
    )
    allocated_original_amount: Mapped[Decimal] = mapped_column(
        ExactDecimal(24, 6), nullable=False
    )
    allocated_purchase_currency_amount: Mapped[Decimal] = mapped_column(
        ExactDecimal(24, 6), nullable=False
    )

    purchase_cost: Mapped[PurchaseCostModel] = relationship(lazy="joined")
    purchase_item: Mapped[PurchaseItemModel] = relationship(lazy="joined")
