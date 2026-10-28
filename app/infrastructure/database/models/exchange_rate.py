"""ORM model for the append-only ``exchange_rates`` table."""

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
    event,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.exceptions import ImmutableExchangeRateError
from app.infrastructure.database.base import Base
from app.infrastructure.database.models.currency import CurrencyModel
from app.infrastructure.database.timestamp import utc_now
from app.infrastructure.database.types import ExactDecimal, UtcDateTime


class ExchangeRateModel(Base):
    __tablename__ = "exchange_rates"
    __table_args__ = (
        CheckConstraint("rate > 0", name="rate_positive"),
        CheckConstraint(
            "base_currency_id <> quote_currency_id",
            name="currencies_differ",
        ),
        CheckConstraint(
            "source IN ('MANUAL', 'ELTOQUE')",
            name="source_valid",
        ),
        Index(
            "ix_exchange_rates_pair_timestamp",
            "base_currency_id",
            "quote_currency_id",
            "rate_timestamp",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    base_currency_id: Mapped[int] = mapped_column(
        ForeignKey("currencies.id"), nullable=False
    )
    quote_currency_id: Mapped[int] = mapped_column(
        ForeignKey("currencies.id"), nullable=False
    )
    rate: Mapped[Decimal] = mapped_column(
        ExactDecimal(24, 12), nullable=False
    )
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    rate_timestamp: Mapped[datetime] = mapped_column(UtcDateTime(), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, default=utc_now
    )

    base_currency: Mapped[CurrencyModel] = relationship(
        foreign_keys=[base_currency_id],
        lazy="joined",
    )
    quote_currency: Mapped[CurrencyModel] = relationship(
        foreign_keys=[quote_currency_id],
        lazy="joined",
    )


@event.listens_for(ExchangeRateModel, "before_update")
def _reject_exchange_rate_update(_mapper, _connection, _target) -> None:
    raise ImmutableExchangeRateError(
        "Historical exchange rates cannot be updated; add a new rate instead."
    )


@event.listens_for(ExchangeRateModel, "before_delete")
def _reject_exchange_rate_delete(_mapper, _connection, _target) -> None:
    raise ImmutableExchangeRateError(
        "Historical exchange rates cannot be deleted."
    )
