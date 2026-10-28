"""ORM model for the ``customer_return_items`` table."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base
from app.infrastructure.database.models.customer_return import (
    CustomerReturnModel,
)
from app.infrastructure.database.models.sale_item import SaleItemModel
from app.infrastructure.database.timestamp import utc_now
from app.infrastructure.database.types import UtcDateTime

_RETURN_CONDITIONS = ("SELLABLE", "DAMAGED")


class CustomerReturnItemModel(Base):
    __tablename__ = "customer_return_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint(
            "condition IN ("
            + ", ".join(
                f"'{value}'" for value in _RETURN_CONDITIONS
            )
            + ")",
            name="condition_valid",
        ),
        Index(
            "ix_customer_return_items_customer_return_id",
            "customer_return_id",
        ),
        Index(
            "ix_customer_return_items_sale_item_id",
            "sale_item_id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_return_id: Mapped[int] = mapped_column(
        ForeignKey("customer_returns.id"), nullable=False
    )
    sale_item_id: Mapped[int] = mapped_column(
        ForeignKey("sale_items.id"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    condition: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, default=utc_now
    )

    customer_return: Mapped[CustomerReturnModel] = relationship(
        lazy="joined"
    )
    sale_item: Mapped[SaleItemModel] = relationship(lazy="joined")
