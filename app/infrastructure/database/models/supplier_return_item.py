"""ORM model for the ``supplier_return_items`` table."""

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
from app.infrastructure.database.models.purchase_item import PurchaseItemModel
from app.infrastructure.database.models.supplier_return import (
    SupplierReturnModel,
)
from app.infrastructure.database.timestamp import utc_now
from app.infrastructure.database.types import ExactDecimal, UtcDateTime


class SupplierReturnItemModel(Base):
    __tablename__ = "supplier_return_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint(
            "unit_cost_snapshot >= 0",
            name="unit_cost_snapshot_non_negative",
        ),
        Index(
            "ix_supplier_return_items_supplier_return_id",
            "supplier_return_id",
        ),
        Index(
            "ix_supplier_return_items_purchase_item_id",
            "purchase_item_id",
        ),
        Index(
            "ix_supplier_return_items_inventory_lot_id",
            "inventory_lot_id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    supplier_return_id: Mapped[int] = mapped_column(
        ForeignKey("supplier_returns.id"), nullable=False
    )
    purchase_item_id: Mapped[int] = mapped_column(
        ForeignKey("purchase_items.id"), nullable=False
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

    supplier_return: Mapped[SupplierReturnModel] = relationship(
        lazy="joined"
    )
    purchase_item: Mapped[PurchaseItemModel] = relationship(lazy="joined")
    inventory_lot: Mapped[InventoryLotModel] = relationship(lazy="joined")
