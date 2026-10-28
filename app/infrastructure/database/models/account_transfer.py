"""ORM model for the ``account_transfers`` table."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base
from app.infrastructure.database.models.account import AccountModel
from app.infrastructure.database.models.exchange_rate import ExchangeRateModel
from app.infrastructure.database.timestamp import utc_now
from app.infrastructure.database.types import ExactDecimal, UtcDateTime


class AccountTransferModel(Base):
    __tablename__ = "account_transfers"
    __table_args__ = (
        CheckConstraint(
            "source_account_id <> destination_account_id",
            name="different_accounts",
        ),
        Index(
            "ix_account_transfers_source_account_id", "source_account_id"
        ),
        Index(
            "ix_account_transfers_destination_account_id",
            "destination_account_id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id"), nullable=False
    )
    destination_account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id"), nullable=False
    )
    source_amount: Mapped[Decimal] = mapped_column(
        ExactDecimal(24, 6), nullable=False
    )
    destination_amount: Mapped[Decimal] = mapped_column(
        ExactDecimal(24, 6), nullable=False
    )
    exchange_rate_id: Mapped[int | None] = mapped_column(
        ForeignKey("exchange_rates.id")
    )
    transfer_date: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, default=utc_now
    )

    source_account: Mapped[AccountModel] = relationship(
        foreign_keys=[source_account_id], lazy="joined"
    )
    destination_account: Mapped[AccountModel] = relationship(
        foreign_keys=[destination_account_id], lazy="joined"
    )
    exchange_rate: Mapped[ExchangeRateModel | None] = relationship(
        lazy="joined"
    )
