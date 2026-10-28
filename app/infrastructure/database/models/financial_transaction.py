"""ORM model for the ``financial_transactions`` table."""

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
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base
from app.infrastructure.database.models.account import AccountModel
from app.infrastructure.database.models.currency import CurrencyModel
from app.infrastructure.database.timestamp import utc_now
from app.infrastructure.database.types import ExactDecimal, UtcDateTime

_TRANSACTION_TYPES = (
    "CAPITAL_CONTRIBUTION",
    "CAPITAL_WITHDRAWAL",
    "PURCHASE",
    "SALE",
    "EXPENSE",
    "CUSTOMER_REFUND",
    "SUPPLIER_REFUND",
    "TRANSFER",
    "CURRENCY_EXCHANGE",
    "ADJUSTMENT",
)


class FinancialTransactionModel(Base):
    __tablename__ = "financial_transactions"
    __table_args__ = (
        CheckConstraint(
            "transaction_type IN ("
            + ", ".join(f"'{value}'" for value in _TRANSACTION_TYPES)
            + ")",
            name="transaction_type_valid",
        ),
        CheckConstraint(
            "((CASE WHEN purchase_id IS NOT NULL THEN 1 ELSE 0 END) + "
            "(CASE WHEN sale_id IS NOT NULL THEN 1 ELSE 0 END) + "
            "(CASE WHEN expense_id IS NOT NULL THEN 1 ELSE 0 END) + "
            "(CASE WHEN customer_return_id IS NOT NULL THEN 1 ELSE 0 END) + "
            "(CASE WHEN supplier_return_id IS NOT NULL THEN 1 ELSE 0 END) + "
            "(CASE WHEN capital_movement_id IS NOT NULL THEN 1 ELSE 0 END) + "
            "(CASE WHEN account_transfer_id IS NOT NULL THEN 1 ELSE 0 END)) "
            "<= 1",
            name="single_business_source",
        ),
        Index("ix_financial_transactions_account_id", "account_id"),
        Index("ix_financial_transactions_purchase_id", "purchase_id"),
        Index("ix_financial_transactions_sale_id", "sale_id"),
        Index("ix_financial_transactions_expense_id", "expense_id"),
        Index(
            "ix_financial_transactions_customer_return_id",
            "customer_return_id",
        ),
        Index(
            "ix_financial_transactions_supplier_return_id",
            "supplier_return_id",
        ),
        Index(
            "ix_financial_transactions_transaction_date",
            "transaction_date",
        ),
        Index(
            "ix_financial_transactions_account_id_transaction_date",
            "account_id",
            "transaction_date",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    transaction_type: Mapped[str] = mapped_column(String(32), nullable=False)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(
        ExactDecimal(24, 6), nullable=False
    )
    currency_id: Mapped[int] = mapped_column(
        ForeignKey("currencies.id"), nullable=False
    )
    purchase_id: Mapped[int | None] = mapped_column(
        ForeignKey("purchases.id")
    )
    sale_id: Mapped[int | None] = mapped_column(ForeignKey("sales.id"))
    expense_id: Mapped[int | None] = mapped_column(
        ForeignKey("expenses.id")
    )
    customer_return_id: Mapped[int | None] = mapped_column(
        ForeignKey("customer_returns.id")
    )
    supplier_return_id: Mapped[int | None] = mapped_column(
        ForeignKey("supplier_returns.id")
    )
    capital_movement_id: Mapped[int | None] = mapped_column(
        ForeignKey("capital_movements.id")
    )
    account_transfer_id: Mapped[int | None] = mapped_column(
        ForeignKey("account_transfers.id")
    )
    exchange_rate_id: Mapped[int | None] = mapped_column(
        ForeignKey("exchange_rates.id")
    )
    description: Mapped[str | None] = mapped_column(Text)
    transaction_date: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, default=utc_now
    )

    account: Mapped[AccountModel] = relationship(lazy="joined")
    currency: Mapped[CurrencyModel] = relationship(lazy="joined")
