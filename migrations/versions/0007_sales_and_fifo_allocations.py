"""Add customers, sales, FIFO allocations and the sale ledger source.

Revision ID: 0007_sales_and_fifo_allocations
Revises: 0006_inventory_lots_and_movements
Create Date: 2026-10-27

Monetary amounts use the same exact-text strategy as previous migrations on
SQLite. Historical FIFO costs live in ``sale_item_lot_allocations`` rather
than on ``sale_items``.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0007_sales_and_fifo_allocations"
down_revision: str | Sequence[str] | None = (
    "0006_inventory_lots_and_movements"
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SALE_STATUSES = (
    "COMPLETED",
    "PARTIALLY_REFUNDED",
    "REFUNDED",
    "CANCELLED",
)
_OLD_SINGLE_SOURCE_CHECK = (
    "((CASE WHEN purchase_id IS NOT NULL THEN 1 ELSE 0 END) + "
    "(CASE WHEN capital_movement_id IS NOT NULL THEN 1 ELSE 0 END) + "
    "(CASE WHEN account_transfer_id IS NOT NULL THEN 1 ELSE 0 END)) "
    "<= 1"
)
_NEW_SINGLE_SOURCE_CHECK = (
    "((CASE WHEN purchase_id IS NOT NULL THEN 1 ELSE 0 END) + "
    "(CASE WHEN sale_id IS NOT NULL THEN 1 ELSE 0 END) + "
    "(CASE WHEN capital_movement_id IS NOT NULL THEN 1 ELSE 0 END) + "
    "(CASE WHEN account_transfer_id IS NOT NULL THEN 1 ELSE 0 END)) "
    "<= 1"
)
_TRANSACTION_TYPE_CHECK = (
    "transaction_type IN ('CAPITAL_CONTRIBUTION', 'CAPITAL_WITHDRAWAL', "
    "'PURCHASE', 'SALE', 'EXPENSE', 'CUSTOMER_REFUND', "
    "'SUPPLIER_REFUND', 'TRANSFER', 'CURRENCY_EXCHANGE', 'ADJUSTMENT')"
)
# Revision 0004 passed already-prefixed names through the naming convention.
_OLD_TRANSACTION_TYPE_CHECK_NAME = (
    "ck_financial_transactions_ck_financial_transactions_"
    "transaction_type_valid"
)
_SOURCE_CHECK_NAME = "ck_financial_transactions_single_business_source"


def _in_list(values: tuple[str, ...]) -> str:
    return "(" + ", ".join(f"'{value}'" for value in values) + ")"


def _ledger_table(*, with_sale: bool) -> sa.Table:
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
    if with_sale:
        columns.insert(
            6, sa.Column("sale_id", sa.Integer(), nullable=True)
        )

    constraints: list[sa.Constraint] = [
        sa.CheckConstraint(
            _TRANSACTION_TYPE_CHECK,
            name=_OLD_TRANSACTION_TYPE_CHECK_NAME,
        ),
        sa.CheckConstraint(
            _NEW_SINGLE_SOURCE_CHECK
            if with_sale
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
    if with_sale:
        constraints.append(
            sa.ForeignKeyConstraint(
                ["sale_id"],
                ["sales.id"],
                name="fk_financial_transactions_sale_id_sales",
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
        "ix_financial_transactions_transaction_date",
        table.c.transaction_date,
    )
    sa.Index(
        "ix_financial_transactions_account_id_transaction_date",
        table.c.account_id,
        table.c.transaction_date,
    )
    if with_sale:
        sa.Index("ix_financial_transactions_sale_id", table.c.sale_id)
    return table


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("social_contact", sa.String(length=255), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name="pk_customers"),
    )

    op.create_table(
        "sales",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=True),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("currency_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("sale_date", sa.DateTime(), nullable=False),
        sa.Column("discount_amount", sa.String(), nullable=True),
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
        sa.CheckConstraint(
            "status IN " + _in_list(_SALE_STATUSES),
            name="ck_sales_status_valid",
        ),
        sa.CheckConstraint(
            "discount_amount IS NULL OR discount_amount >= 0",
            name="ck_sales_discount_amount_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customers.id"],
            name="fk_sales_customer_id_customers",
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
            name="fk_sales_account_id_accounts",
        ),
        sa.ForeignKeyConstraint(
            ["currency_id"],
            ["currencies.id"],
            name="fk_sales_currency_id_currencies",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_sales"),
    )
    op.create_index("ix_sales_sale_date", "sales", ["sale_date"])
    op.create_index("ix_sales_customer_id", "sales", ["customer_id"])
    op.create_index("ix_sales_status", "sales", ["status"])

    op.create_table(
        "sale_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sale_id", sa.Integer(), nullable=False),
        sa.Column("variant_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.String(), nullable=False),
        sa.Column("discount_amount", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "quantity > 0", name="ck_sale_items_quantity_positive"
        ),
        sa.CheckConstraint(
            "unit_price >= 0",
            name="ck_sale_items_unit_price_non_negative",
        ),
        sa.CheckConstraint(
            "discount_amount IS NULL OR discount_amount >= 0",
            name="ck_sale_items_discount_amount_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["sale_id"],
            ["sales.id"],
            name="fk_sale_items_sale_id_sales",
        ),
        sa.ForeignKeyConstraint(
            ["variant_id"],
            ["product_variants.id"],
            name="fk_sale_items_variant_id_product_variants",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_sale_items"),
    )
    op.create_index("ix_sale_items_sale_id", "sale_items", ["sale_id"])
    op.create_index(
        "ix_sale_items_variant_id", "sale_items", ["variant_id"]
    )

    op.create_table(
        "sale_item_lot_allocations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sale_item_id", sa.Integer(), nullable=False),
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
            name="ck_sale_item_lot_allocations_quantity_positive",
        ),
        sa.CheckConstraint(
            "unit_cost_snapshot >= 0",
            name=(
                "ck_sale_item_lot_allocations_"
                "unit_cost_snapshot_non_negative"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["sale_item_id"],
            ["sale_items.id"],
            name=(
                "fk_sale_item_lot_allocations_sale_item_id_sale_items"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["inventory_lot_id"],
            ["inventory_lots.id"],
            name=(
                "fk_sale_item_lot_allocations_inventory_lot_id_"
                "inventory_lots"
            ),
        ),
        sa.PrimaryKeyConstraint(
            "id", name="pk_sale_item_lot_allocations"
        ),
    )
    op.create_index(
        "ix_sale_item_lot_allocations_sale_item_id",
        "sale_item_lot_allocations",
        ["sale_item_id"],
    )
    op.create_index(
        "ix_sale_item_lot_allocations_inventory_lot_id",
        "sale_item_lot_allocations",
        ["inventory_lot_id"],
    )

    with op.batch_alter_table(
        "financial_transactions",
        copy_from=_ledger_table(with_sale=False),
    ) as batch_op:
        batch_op.add_column(
            sa.Column("sale_id", sa.Integer(), nullable=True)
        )
        batch_op.drop_constraint(
            op.f(_SOURCE_CHECK_NAME), type_="check"
        )
        batch_op.create_check_constraint(
            op.f(_SOURCE_CHECK_NAME), _NEW_SINGLE_SOURCE_CHECK
        )
        batch_op.create_foreign_key(
            "fk_financial_transactions_sale_id_sales",
            "sales",
            ["sale_id"],
            ["id"],
        )
    op.create_index(
        "ix_financial_transactions_sale_id",
        "financial_transactions",
        ["sale_id"],
    )


def downgrade() -> None:
    with op.batch_alter_table(
        "financial_transactions",
        copy_from=_ledger_table(with_sale=True),
    ) as batch_op:
        batch_op.drop_index("ix_financial_transactions_sale_id")
        batch_op.drop_constraint(
            "fk_financial_transactions_sale_id_sales",
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            op.f(_SOURCE_CHECK_NAME), type_="check"
        )
        batch_op.create_check_constraint(
            op.f(_SOURCE_CHECK_NAME), _OLD_SINGLE_SOURCE_CHECK
        )
        batch_op.drop_column("sale_id")

    op.drop_index(
        "ix_sale_item_lot_allocations_inventory_lot_id",
        table_name="sale_item_lot_allocations",
    )
    op.drop_index(
        "ix_sale_item_lot_allocations_sale_item_id",
        table_name="sale_item_lot_allocations",
    )
    op.drop_table("sale_item_lot_allocations")

    op.drop_index("ix_sale_items_variant_id", table_name="sale_items")
    op.drop_index("ix_sale_items_sale_id", table_name="sale_items")
    op.drop_table("sale_items")

    op.drop_index("ix_sales_status", table_name="sales")
    op.drop_index("ix_sales_customer_id", table_name="sales")
    op.drop_index("ix_sales_sale_date", table_name="sales")
    op.drop_table("sales")

    op.drop_table("customers")
