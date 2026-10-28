"""ORM model for the ``variant_attribute_values`` join table."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class VariantAttributeValueModel(Base):
    __tablename__ = "variant_attribute_values"
    __table_args__ = (
        Index(
            "ix_variant_attribute_values_attribute_value_id",
            "attribute_value_id",
        ),
    )

    variant_id: Mapped[int] = mapped_column(
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        primary_key=True,
    )
    attribute_value_id: Mapped[int] = mapped_column(
        ForeignKey("attribute_values.id", ondelete="CASCADE"),
        primary_key=True,
    )
