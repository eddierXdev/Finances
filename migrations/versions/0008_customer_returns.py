"""Add customer returns, return allocations and the refund ledger source.

Revision ID: 0008_customer_returns
Revises: 0007_sales_and_fifo_allocations
Create Date: 2026-10-27

Monetary amounts use the same exact-text strategy as previous migrations on
SQLite. Return allocations point to the original sale FIFO allocation instead
of duplicating the inventory lot.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0008_customer_returns"
down_revision: str | Sequence[str] | None = (
    "0007_sales_and_fifo_allocations"
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_RETURN_CONDITIONS = ("SELLABLE", "DAMAGED")
_OLD_SINGLE_SOURCE_CHECK = (
    "((CASE WHEN purchase_id IS NOT NULL THEN 1 ELSE 0 END) + "
    "(CASE WHEN sale_id IS NOT NULL THEN 1 ELSE 0 END) + "
    "(CASE WHEN capital_movement_id IS NOT NULL THEN 1 ELSE 0 END) + "
    "(CASE WHEN account_transfer_id IS NOT NULL THEN 1 ELSE 0 END)) "
    "<= 1"
)
_NEW_SINGLE_SOURCE_CHECK = (
    "((CASE WHEN purchase_id IS NOT NULL THEN 1 ELSE 0 END) + "
    "(CASE WHEN sale_id IS NOT NULL THEN 1 ELSE 0 END) + "
    "(CASE WHEN customer_return_id IS NOT NULL THEN 1 ELSE 0 END) + "
    "(CASE WHEN capital_movement_id IS NOT NULL THEN 1 ELSE 0 END) + "
    "(CASE WHEN account_transfer_id IS NOT NULL THEN 1 ELSE 0 END)) "
    "<= 1"
)
_TRANSACTION_TYPE_CHECK = (
    "transaction_type IN ('CAPITAL_CONTRIBUTION', 'CAPITAL_WITHDRAWAL', "
    "'PURCHASE', 'SALE', 'EXPENSE', 'CUSTOMER_REFUND', "
    "'SUPPLIER_REFUND', 'TRANSFER', 'CURRENCY_EXCHANGE', 'ADJUSTMENT')"
)
_OLD_TRANSACTION_TYPE_CHECK_NAME = (
    "ck_financial_transactions_ck_financial_transactions_"
    "transaction_type_valid"
)
_SOURCE_CHECK_NAME = "ck_financial_transactions_single_business_source"


def _in_list(values: tuple[str, ...]) -> str:
    return "(" + ", ".join(f"'{value}'" for value in values) + ")"


def _ledger_table(*, with_customer_return: bool) -> sa.Table:
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
    if with_customer_return:
        columns.insert(
            7, sa.Column("customer_return_id", sa.Integer(), nullable=True)
        )

    constraints: list[sa.Constraint] = [
        sa.CheckConstraint(
            _TRANSACTION_TYPE_CHECK,
            name=_OLD_TRANSACTION_TYPE_CHECK_NAME,
        ),
        sa.CheckConstraint(
            _NEW_SINGLE_SOURCE_CHECK
            if with_customer_return
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
    if with_customer_return:
        constraints.append(
            sa.ForeignKeyConstraint(
                ["customer_return_id"],
                ["customer_returns.id"],
                name=(
                    "fk_financial_transactions_customer_return_id_"
                    "customer_returns"
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
        "ix_financial_transactions_transaction_date",
        table.c.transaction_date,
    )
    sa.Index(
        "ix_financial_transactions_account_id_transaction_date",
        table.c.account_id,
        table.c.transaction_date,
    )
    if with_customer_return:
        sa.Index(
            "ix_financial_transactions_customer_return_id",
            table.c.customer_return_id,
        )
    return table


def upgrade() -> None:
    op.create_table(
        "customer_returns",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sale_id", sa.Integer(), nullable=False),
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
            name="ck_customer_returns_refund_amount_positive",
        ),
        sa.CheckConstraint(
            "(refund_amount IS NULL AND refund_currency_id IS NULL AND "
            "account_id IS NULL) OR (refund_amount IS NOT NULL AND "
            "refund_currency_id IS NOT NULL AND account_id IS NOT NULL)",
            name="ck_customer_returns_refund_complete",
        ),
        sa.ForeignKeyConstraint(
            ["sale_id"],
            ["sales.id"],
            name="fk_customer_returns_sale_id_sales",
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
            name="fk_customer_returns_account_id_accounts",
        ),
        sa.ForeignKeyConstraint(
            ["refund_currency_id"],
            ["currencies.id"],
            name=(
                "fk_customer_returns_refund_currency_id_currencies"
            ),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_customer_returns"),
    )
    op.create_index(
        "ix_customer_returns_sale_id",
        "customer_returns",
        ["sale_id"],
    )
    op.create_index(
        "ix_customer_returns_return_date",
        "customer_returns",
        ["return_date"],
    )

    op.create_table(
        "customer_return_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("customer_return_id", sa.Integer(), nullable=False),
        sa.Column("sale_item_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("condition", sa.String(length=16), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "quantity > 0",
            name="ck_customer_return_items_quantity_positive",
        ),
        sa.CheckConstraint(
            "condition IN " + _in_list(_RETURN_CONDITIONS),
            name="ck_customer_return_items_condition_valid",
        ),
        sa.ForeignKeyConstraint(
            ["customer_return_id"],
            ["customer_returns.id"],
            name=(
                "fk_customer_return_items_customer_return_id_"
                "customer_returns"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["sale_item_id"],
            ["sale_items.id"],
            name="fk_customer_return_items_sale_item_id_sale_items",
        ),
        sa.PrimaryKeyConstraint(
            "id", name="pk_customer_return_items"
        ),
    )
    op.create_index(
        "ix_customer_return_items_customer_return_id",
        "customer_return_items",
        ["customer_return_id"],
    )
    op.create_index(
        "ix_customer_return_items_sale_item_id",
        "customer_return_items",
        ["sale_item_id"],
    )

    op.create_table(
        "return_lot_allocations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("customer_return_item_id", sa.Integer(), nullable=False),
        sa.Column(
            "sale_item_lot_allocation_id", sa.Integer(), nullable=False
        ),
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
            name="ck_return_lot_allocations_quantity_positive",
        ),
        sa.CheckConstraint(
            "unit_cost_snapshot >= 0",
            name=(
                "ck_return_lot_allocations_"
                "unit_cost_snapshot_non_negative"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["customer_return_item_id"],
            ["customer_return_items.id"],
            name=(
                "fk_return_lot_allocations_customer_return_item_id_"
                "customer_return_items"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["sale_item_lot_allocation_id"],
            ["sale_item_lot_allocations.id"],
            name=(
                "fk_return_lot_allocations_sale_item_lot_allocation_id_"
                "sale_item_lot_allocations"
            ),
        ),
        sa.PrimaryKeyConstraint(
            "id", name="pk_return_lot_allocations"
        ),
    )
    op.create_index(
        "ix_return_lot_allocations_customer_return_item_id",
        "return_lot_allocations",
        ["customer_return_item_id"],
    )
    op.create_index(
        "ix_return_lot_allocations_sale_item_lot_allocation_id",
        "return_lot_allocations",
        ["sale_item_lot_allocation_id"],
    )

    with op.batch_alter_table(
        "financial_transactions",
        copy_from=_ledger_table(with_customer_return=False),
    ) as batch_op:
        batch_op.add_column(
            sa.Column("customer_return_id", sa.Integer(), nullable=True)
        )
        batch_op.drop_constraint(
            op.f(_SOURCE_CHECK_NAME), type_="check"
        )
        batch_op.create_check_constraint(
            op.f(_SOURCE_CHECK_NAME), _NEW_SINGLE_SOURCE_CHECK
        )
        batch_op.create_foreign_key(
            "fk_financial_transactions_customer_return_id_"
            "customer_returns",
            "customer_returns",
            ["customer_return_id"],
            ["id"],
        )
    op.create_index(
        "ix_financial_transactions_customer_return_id",
        "financial_transactions",
        ["customer_return_id"],
    )


def downgrade() -> None:
    with op.batch_alter_table(
        "financial_transactions",
        copy_from=_ledger_table(with_customer_return=True),
    ) as batch_op:
        batch_op.drop_index(
            "ix_financial_transactions_customer_return_id"
        )
        batch_op.drop_constraint(
            "fk_financial_transactions_customer_return_id_"
            "customer_returns",
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            op.f(_SOURCE_CHECK_NAME), type_="check"
        )
        batch_op.create_check_constraint(
            op.f(_SOURCE_CHECK_NAME), _OLD_SINGLE_SOURCE_CHECK
        )
        batch_op.drop_column("customer_return_id")

    op.drop_index(
        "ix_return_lot_allocations_sale_item_lot_allocation_id",
        table_name="return_lot_allocations",
    )
    op.drop_index(
        "ix_return_lot_allocations_customer_return_item_id",
        table_name="return_lot_allocations",
    )
    op.drop_table("return_lot_allocations")

    op.drop_index(
        "ix_customer_return_items_sale_item_id",
        table_name="customer_return_items",
    )
    op.drop_index(
        "ix_customer_return_items_customer_return_id",
        table_name="customer_return_items",
    )
    op.drop_table("customer_return_items")

    op.drop_index(
        "ix_customer_returns_return_date",
        table_name="customer_returns",
    )
    op.drop_index(
        "ix_customer_returns_sale_id",
        table_name="customer_returns",
    )
    op.drop_table("customer_returns")
