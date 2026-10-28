"""Add supplier returns, their items and the refund ledger source.

Revision ID: 0009_supplier_returns
Revises: 0008_customer_returns
Create Date: 2026-10-27

Monetary amounts use the same exact-text strategy as previous migrations on
SQLite. Supplier return items point directly to the original purchase item and
inventory lot, preserving the historical acquisition cost without a separate
allocation table.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0009_supplier_returns"
down_revision: str | Sequence[str] | None = "0008_customer_returns"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OLD_SINGLE_SOURCE_CHECK = (
    "((CASE WHEN purchase_id IS NOT NULL THEN 1 ELSE 0 END) + "
    "(CASE WHEN sale_id IS NOT NULL THEN 1 ELSE 0 END) + "
    "(CASE WHEN customer_return_id IS NOT NULL THEN 1 ELSE 0 END) + "
    "(CASE WHEN capital_movement_id IS NOT NULL THEN 1 ELSE 0 END) + "
    "(CASE WHEN account_transfer_id IS NOT NULL THEN 1 ELSE 0 END)) "
    "<= 1"
)
_NEW_SINGLE_SOURCE_CHECK = (
    "((CASE WHEN purchase_id IS NOT NULL THEN 1 ELSE 0 END) + "
    "(CASE WHEN sale_id IS NOT NULL THEN 1 ELSE 0 END) + "
    "(CASE WHEN customer_return_id IS NOT NULL THEN 1 ELSE 0 END) + "
    "(CASE WHEN supplier_return_id IS NOT NULL THEN 1 ELSE 0 END) + "
    "(CASE WHEN capital_movement_id IS NOT NULL THEN 1 ELSE 0 END) + "
    "(CASE WHEN account_transfer_id IS NOT NULL THEN 1 ELSE 0 END)) "
    "<= 1"
)
_TRANSACTION_TYPE_CHECK = (
    "transaction_type IN ('CAPITAL_CONTRIBUTION', 'CAPITAL_WITHDRAWAL', "
    "'PURCHASE', 'SALE', 'EXPENSE', 'CUSTOMER_REFUND', "
    "'SUPPLIER_REFUND', 'TRANSFER', 'CURRENCY_EXCHANGE', 'ADJUSTMENT')"
)
_TRANSACTION_TYPE_CHECK_NAME = (
    "ck_financial_transactions_ck_financial_transactions_"
    "transaction_type_valid"
)
_SOURCE_CHECK_NAME = "ck_financial_transactions_single_business_source"


def _ledger_table(*, with_supplier_return: bool) -> sa.Table:
    """Describe ``financial_transactions`` for offline batch migrations."""
    columns = [
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "transaction_type", sa.String(length=32), nullable=False
        ),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.String(), nullable=False),
        sa.Column("currency_id", sa.Integer(), nullable=False),
        sa.Column("purchase_id", sa.Integer(), nullable=True),
        sa.Column("sale_id", sa.Integer(), nullable=True),
        sa.Column("customer_return_id", sa.Integer(), nullable=True),
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
    ]
    if with_supplier_return:
        columns.insert(
            8, sa.Column("supplier_return_id", sa.Integer(), nullable=True)
        )

    constraints: list[sa.Constraint] = [
        sa.CheckConstraint(
            _TRANSACTION_TYPE_CHECK,
            name=_TRANSACTION_TYPE_CHECK_NAME,
        ),
        sa.CheckConstraint(
            _NEW_SINGLE_SOURCE_CHECK
            if with_supplier_return
            else _OLD_SINGLE_SOURCE_CHECK,
            name=_SOURCE_CHECK_NAME,
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
            ["purchase_id"],
            ["purchases.id"],
            name="fk_financial_transactions_purchase_id_purchases",
        ),
        sa.ForeignKeyConstraint(
            ["sale_id"],
            ["sales.id"],
            name="fk_financial_transactions_sale_id_sales",
        ),
        sa.ForeignKeyConstraint(
            ["customer_return_id"],
            ["customer_returns.id"],
            name=(
                "fk_financial_transactions_customer_return_id_"
                "customer_returns"
            ),
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
        sa.PrimaryKeyConstraint(
            "id", name="pk_financial_transactions"
        ),
    ]
    if with_supplier_return:
        constraints.append(
            sa.ForeignKeyConstraint(
                ["supplier_return_id"],
                ["supplier_returns.id"],
                name=(
                    "fk_financial_transactions_supplier_return_id_"
                    "supplier_returns"
                ),
            )
        )

    table = sa.Table(
        "financial_transactions", sa.MetaData(), *columns, *constraints
    )
    sa.Index(
        "ix_financial_transactions_account_id", table.c.account_id
    )
    sa.Index(
        "ix_financial_transactions_purchase_id", table.c.purchase_id
    )
    sa.Index(
        "ix_financial_transactions_sale_id", table.c.sale_id
    )
    sa.Index(
        "ix_financial_transactions_customer_return_id",
        table.c.customer_return_id,
    )
    if with_supplier_return:
        sa.Index(
            "ix_financial_transactions_supplier_return_id",
            table.c.supplier_return_id,
        )
    sa.Index(
        "ix_financial_transactions_transaction_date",
        table.c.transaction_date,
    )
    sa.Index(
        "ix_financial_transactions_account_id_transaction_date",
        table.c.account_id,
        table.c.transaction_date,
    )
    return table


def upgrade() -> None:
    op.create_table(
        "supplier_returns",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("purchase_id", sa.Integer(), nullable=False),
        sa.Column("supplier_id", sa.Integer(), nullable=True),
        sa.Column("account_id", sa.Integer(), nullable=True),
        sa.Column("refund_amount", sa.String(), nullable=True),
        sa.Column("refund_currency_id", sa.Integer(), nullable=True),
        sa.Column("return_date", sa.DateTime(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "refund_amount IS NULL OR refund_amount > 0",
            name="ck_supplier_returns_refund_amount_positive",
        ),
        sa.CheckConstraint(
            "(refund_amount IS NULL AND refund_currency_id IS NULL AND "
            "account_id IS NULL) OR (refund_amount IS NOT NULL AND "
            "refund_currency_id IS NOT NULL AND account_id IS NOT NULL)",
            name="ck_supplier_returns_refund_complete",
        ),
        sa.ForeignKeyConstraint(
            ["purchase_id"],
            ["purchases.id"],
            name="fk_supplier_returns_purchase_id_purchases",
        ),
        sa.ForeignKeyConstraint(
            ["supplier_id"],
            ["suppliers.id"],
            name="fk_supplier_returns_supplier_id_suppliers",
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
            name="fk_supplier_returns_account_id_accounts",
        ),
        sa.ForeignKeyConstraint(
            ["refund_currency_id"],
            ["currencies.id"],
            name=(
                "fk_supplier_returns_refund_currency_id_currencies"
            ),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_supplier_returns"),
    )
    op.create_index(
        "ix_supplier_returns_purchase_id",
        "supplier_returns",
        ["purchase_id"],
    )
    op.create_index(
        "ix_supplier_returns_return_date",
        "supplier_returns",
        ["return_date"],
    )

    op.create_table(
        "supplier_return_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("supplier_return_id", sa.Integer(), nullable=False),
        sa.Column("purchase_item_id", sa.Integer(), nullable=False),
        sa.Column("inventory_lot_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_cost_snapshot", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "quantity > 0",
            name="ck_supplier_return_items_quantity_positive",
        ),
        sa.CheckConstraint(
            "unit_cost_snapshot >= 0",
            name=(
                "ck_supplier_return_items_"
                "unit_cost_snapshot_non_negative"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["supplier_return_id"],
            ["supplier_returns.id"],
            name=(
                "fk_supplier_return_items_supplier_return_id_"
                "supplier_returns"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["purchase_item_id"],
            ["purchase_items.id"],
            name=(
                "fk_supplier_return_items_purchase_item_id_"
                "purchase_items"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["inventory_lot_id"],
            ["inventory_lots.id"],
            name=(
                "fk_supplier_return_items_inventory_lot_id_"
                "inventory_lots"
            ),
        ),
        sa.PrimaryKeyConstraint(
            "id", name="pk_supplier_return_items"
        ),
    )
    op.create_index(
        "ix_supplier_return_items_supplier_return_id",
        "supplier_return_items",
        ["supplier_return_id"],
    )
    op.create_index(
        "ix_supplier_return_items_purchase_item_id",
        "supplier_return_items",
        ["purchase_item_id"],
    )
    op.create_index(
        "ix_supplier_return_items_inventory_lot_id",
        "supplier_return_items",
        ["inventory_lot_id"],
    )

    with op.batch_alter_table(
        "financial_transactions",
        copy_from=_ledger_table(with_supplier_return=False),
    ) as batch_op:
        batch_op.add_column(
            sa.Column("supplier_return_id", sa.Integer(), nullable=True)
        )
        batch_op.drop_constraint(
            op.f(_SOURCE_CHECK_NAME), type_="check"
        )
        batch_op.create_check_constraint(
            op.f(_SOURCE_CHECK_NAME), _NEW_SINGLE_SOURCE_CHECK
        )
        batch_op.create_foreign_key(
            "fk_financial_transactions_supplier_return_id_"
            "supplier_returns",
            "supplier_returns",
            ["supplier_return_id"],
            ["id"],
        )
    op.create_index(
        "ix_financial_transactions_supplier_return_id",
        "financial_transactions",
        ["supplier_return_id"],
    )


def downgrade() -> None:
    with op.batch_alter_table(
        "financial_transactions",
        copy_from=_ledger_table(with_supplier_return=True),
    ) as batch_op:
        batch_op.drop_index(
            "ix_financial_transactions_supplier_return_id"
        )
        batch_op.drop_constraint(
            "fk_financial_transactions_supplier_return_id_"
            "supplier_returns",
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            op.f(_SOURCE_CHECK_NAME), type_="check"
        )
        batch_op.create_check_constraint(
            op.f(_SOURCE_CHECK_NAME), _OLD_SINGLE_SOURCE_CHECK
        )
        batch_op.drop_column("supplier_return_id")

    op.drop_index(
        "ix_supplier_return_items_inventory_lot_id",
        table_name="supplier_return_items",
    )
    op.drop_index(
        "ix_supplier_return_items_purchase_item_id",
        table_name="supplier_return_items",
    )
    op.drop_index(
        "ix_supplier_return_items_supplier_return_id",
        table_name="supplier_return_items",
    )
    op.drop_table("supplier_return_items")

    op.drop_index(
        "ix_supplier_returns_return_date",
        table_name="supplier_returns",
    )
    op.drop_index(
        "ix_supplier_returns_purchase_id",
        table_name="supplier_returns",
    )
    op.drop_table("supplier_returns")
