"""ORM models for attributes and attribute values."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class AttributeModel(Base):
    __tablename__ = "attributes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)


class AttributeValueModel(Base):
    __tablename__ = "attribute_values"
    __table_args__ = (
        Index("ix_attribute_values_attribute_id", "attribute_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    attribute_id: Mapped[int] = mapped_column(
        ForeignKey("attributes.id"), nullable=False
    )
    value: Mapped[str] = mapped_column(String(150), nullable=False)
