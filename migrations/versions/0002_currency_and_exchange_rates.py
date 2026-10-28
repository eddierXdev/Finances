"""Add currencies and historical exchange rates.

Revision ID: 0002_currency_and_exchange_rates
Revises: 0001_baseline
Create Date: 2026-10-27

On SQLite, the rate is stored as text to avoid binary floating-point
conversion. ``ExactDecimal`` maps it to NUMERIC on other backends.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_currency_and_exchange_rates"
down_revision: str | Sequence[str] | None = "0001_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INITIAL_CURRENCIES = (
    ("CAD", "Canadian Dollar", "C$", 2),
    ("CUP", "Cuban Peso", "$", 2),
    ("EUR", "Euro", "€", 2),
    ("GBP", "British Pound", "£", 2),
    ("MLC", "Cuban Convertible Currency", None, 2),
    ("MXN", "Mexican Peso", "$", 2),
    ("USD", "US Dollar", "$", 2),
)


def upgrade() -> None:
    op.create_table(
        "currencies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=3), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("symbol", sa.String(length=10), nullable=True),
        sa.Column("decimal_places", sa.Integer(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "decimal_places >= 0 AND decimal_places <= 6",
            name="ck_currencies_decimal_places_range",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_currencies"),
        sa.UniqueConstraint("code", name="uq_currencies_code"),
    )

    op.create_table(
        "exchange_rates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("base_currency_id", sa.Integer(), nullable=False),
        sa.Column("quote_currency_id", sa.Integer(), nullable=False),
        sa.Column("rate", sa.String(), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("rate_timestamp", sa.DateTime(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "rate > 0",
            name="ck_exchange_rates_rate_positive",
        ),
        sa.CheckConstraint(
            "base_currency_id <> quote_currency_id",
            name="ck_exchange_rates_currencies_differ",
        ),
        sa.CheckConstraint(
            "source IN ('MANUAL', 'ELTOQUE')",
            name="ck_exchange_rates_source_valid",
        ),
        sa.ForeignKeyConstraint(
            ["base_currency_id"],
            ["currencies.id"],
            name="fk_exchange_rates_base_currency_id_currencies",
        ),
        sa.ForeignKeyConstraint(
            ["quote_currency_id"],
            ["currencies.id"],
            name="fk_exchange_rates_quote_currency_id_currencies",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_exchange_rates"),
    )
    op.create_index(
        "ix_exchange_rates_pair_timestamp",
        "exchange_rates",
        ["base_currency_id", "quote_currency_id", "rate_timestamp"],
        unique=False,
    )

    currencies_table = sa.table(
        "currencies",
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("symbol", sa.String),
        sa.column("decimal_places", sa.Integer),
        sa.column("is_enabled", sa.Boolean),
    )
    op.bulk_insert(
        currencies_table,
        [
            {
                "code": code,
                "name": name,
                "symbol": symbol,
                "decimal_places": decimal_places,
                "is_enabled": True,
            }
            for code, name, symbol, decimal_places in INITIAL_CURRENCIES
        ],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_exchange_rates_pair_timestamp",
        table_name="exchange_rates",
    )
    op.drop_table("exchange_rates")
    op.drop_table("currencies")
