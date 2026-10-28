"""ORM model for the ``inventory_lots`` table."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base
from app.infrastructure.database.models.currency import CurrencyModel
from app.infrastructure.database.models.purchase_item import PurchaseItemModel
from app.infrastructure.database.timestamp import utc_now
from app.infrastructure.database.types import ExactDecimal, UtcDateTime


class InventoryLotModel(Base):
    __tablename__ = "inventory_lots"
    __table_args__ = (
        CheckConstraint(
            "acquired_quantity > 0",
            name="acquired_quantity_positive",
        ),
        CheckConstraint(
            "remaining_quantity >= 0",
            name="remaining_quantity_non_negative",
        ),
        CheckConstraint(
            "remaining_quantity <= acquired_quantity",
            name="remaining_within_acquired",
        ),
        CheckConstraint("unit_cost >= 0", name="unit_cost_non_negative"),
        Index(
            "ix_inventory_lots_variant_id_received_at",
            "variant_id",
            "received_at",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    purchase_item_id: Mapped[int] = mapped_column(
        ForeignKey("purchase_items.id"), nullable=False
    )
    variant_id: Mapped[int] = mapped_column(
        ForeignKey("product_variants.id"), nullable=False
    )
    acquired_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    remaining_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(
        ExactDecimal(24, 6), nullable=False
    )
    currency_id: Mapped[int] = mapped_column(
        ForeignKey("currencies.id"), nullable=False
    )
    received_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, default=utc_now
    )

    purchase_item: Mapped[PurchaseItemModel] = relationship(lazy="joined")
    currency: Mapped[CurrencyModel] = relationship(lazy="joined")
