"""Create the accounts and financial ledger schema.

Revision ID: 0004_accounts_and_ledger
Revises: 0003_product_catalog
Create Date: 2026-10-27

On SQLite, monetary amounts are stored as text to preserve exact decimal
arithmetic. Future business-source foreign keys (purchases, sales, expenses,
and returns) are added by the migrations that create those tables.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004_accounts_and_ledger"
down_revision: str | Sequence[str] | None = "0003_product_catalog"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("currency_id", sa.Integer(), nullable=False),
        sa.Column("account_type", sa.String(length=50), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["currency_id"],
            ["currencies.id"],
            name="fk_accounts_currency_id_currencies",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_accounts"),
    )
    op.create_index("ix_accounts_currency_id", "accounts", ["currency_id"])

    op.create_table(
        "capital_movements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("movement_type", sa.String(length=16), nullable=False),
        sa.Column("amount", sa.String(), nullable=False),
        sa.Column("currency_id", sa.Integer(), nullable=False),
        sa.Column("movement_date", sa.DateTime(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "movement_type IN ('CONTRIBUTION', 'WITHDRAWAL')",
            name="ck_capital_movements_movement_type_valid",
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
            name="fk_capital_movements_account_id_accounts",
        ),
        sa.ForeignKeyConstraint(
            ["currency_id"],
            ["currencies.id"],
            name="fk_capital_movements_currency_id_currencies",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_capital_movements"),
    )
    op.create_index(
        "ix_capital_movements_account_id",
        "capital_movements",
        ["account_id"],
    )

    op.create_table(
        "account_transfers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_account_id", sa.Integer(), nullable=False),
        sa.Column("destination_account_id", sa.Integer(), nullable=False),
        sa.Column("source_amount", sa.String(), nullable=False),
        sa.Column("destination_amount", sa.String(), nullable=False),
        sa.Column("exchange_rate_id", sa.Integer(), nullable=True),
        sa.Column("transfer_date", sa.DateTime(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "source_account_id <> destination_account_id",
            name="ck_account_transfers_different_accounts",
        ),
        sa.ForeignKeyConstraint(
            ["source_account_id"],
            ["accounts.id"],
            name="fk_account_transfers_source_account_id_accounts",
        ),
        sa.ForeignKeyConstraint(
            ["destination_account_id"],
            ["accounts.id"],
            name="fk_account_transfers_destination_account_id_accounts",
        ),
        sa.ForeignKeyConstraint(
            ["exchange_rate_id"],
            ["exchange_rates.id"],
            name="fk_account_transfers_exchange_rate_id_exchange_rates",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_account_transfers"),
    )
    op.create_index(
        "ix_account_transfers_source_account_id",
        "account_transfers",
        ["source_account_id"],
    )
    op.create_index(
        "ix_account_transfers_destination_account_id",
        "account_transfers",
        ["destination_account_id"],
    )

    op.create_table(
        "financial_transactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "transaction_type", sa.String(length=32), nullable=False
        ),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.String(), nullable=False),
        sa.Column("currency_id", sa.Integer(), nullable=False),
        sa.Column("capital_movement_id", sa.Integer(), nullable=True),
        sa.Column("account_transfer_id", sa.Integer(), nullable=True),
        sa.Column("exchange_rate_id", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("transaction_date", sa.DateTime(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "transaction_type IN ("
            "'CAPITAL_CONTRIBUTION', 'CAPITAL_WITHDRAWAL', 'PURCHASE', "
            "'SALE', 'EXPENSE', 'CUSTOMER_REFUND', 'SUPPLIER_REFUND', "
            "'TRANSFER', 'CURRENCY_EXCHANGE', 'ADJUSTMENT')",
            name="ck_financial_transactions_transaction_type_valid",
        ),
        sa.CheckConstraint(
            "(capital_movement_id IS NULL) OR "
            "(account_transfer_id IS NULL)",
            name="ck_financial_transactions_single_business_source",
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
            name="fk_financial_transactions_account_id_accounts",
        ),
        sa.ForeignKeyConstraint(
            ["currency_id"],
            ["currencies.id"],
            name="fk_financial_transactions_currency_id_currencies",
        ),
        sa.ForeignKeyConstraint(
            ["capital_movement_id"],
            ["capital_movements.id"],
            name=(
                "fk_financial_transactions_capital_movement_id_"
                "capital_movements"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["account_transfer_id"],
            ["account_transfers.id"],
            name=(
                "fk_financial_transactions_account_transfer_id_"
                "account_transfers"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["exchange_rate_id"],
            ["exchange_rates.id"],
            name=(
                "fk_financial_transactions_exchange_rate_id_exchange_rates"
            ),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_financial_transactions"),
    )
    op.create_index(
        "ix_financial_transactions_account_id",
        "financial_transactions",
        ["account_id"],
    )
    op.create_index(
        "ix_financial_transactions_transaction_date",
        "financial_transactions",
        ["transaction_date"],
    )
    op.create_index(
        "ix_financial_transactions_account_id_transaction_date",
        "financial_transactions",
        ["account_id", "transaction_date"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_financial_transactions_account_id_transaction_date",
        table_name="financial_transactions",
    )
    op.drop_index(
        "ix_financial_transactions_transaction_date",
        table_name="financial_transactions",
    )
    op.drop_index(
        "ix_financial_transactions_account_id",
        table_name="financial_transactions",
    )
    op.drop_table("financial_transactions")

    op.drop_index(
        "ix_account_transfers_destination_account_id",
        table_name="account_transfers",
    )
    op.drop_index(
        "ix_account_transfers_source_account_id",
        table_name="account_transfers",
    )
    op.drop_table("account_transfers")

    op.drop_index(
        "ix_capital_movements_account_id",
        table_name="capital_movements",
    )
    op.drop_table("capital_movements")

    op.drop_index("ix_accounts_currency_id", table_name="accounts")
    op.drop_table("accounts")
