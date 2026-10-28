"""Add suppliers, purchases, costs and purchase payment traceability.

Revision ID: 0005_purchases
Revises: 0004_accounts_and_ledger
Create Date: 2026-10-27

Monetary amounts and weights use the same exact-text strategy as previous
migrations on SQLite. The financial ledger gains its ``purchase_id`` source
foreign key in this phase.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005_purchases"
down_revision: str | Sequence[str] | None = "0004_accounts_and_ledger"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OLD_SINGLE_SOURCE_CHECK = (
    "(capital_movement_id IS NULL) OR (account_transfer_id IS NULL)"
)
_NEW_SINGLE_SOURCE_CHECK = (
    "((CASE WHEN purchase_id IS NOT NULL THEN 1 ELSE 0 END) + "
    "(CASE WHEN capital_movement_id IS NOT NULL THEN 1 ELSE 0 END) + "
    "(CASE WHEN account_transfer_id IS NOT NULL THEN 1 ELSE 0 END)) "
    "<= 1"
)
_TRANSACTION_TYPE_CHECK = (
    "transaction_type IN ('CAPITAL_CONTRIBUTION', 'CAPITAL_WITHDRAWAL', "
    "'PURCHASE', 'SALE', 'EXPENSE', 'CUSTOMER_REFUND', "
    "'SUPPLIER_REFUND', 'TRANSFER', 'CURRENCY_EXCHANGE', 'ADJUSTMENT')"
)
# Revision 0004 passed already-prefixed names through the naming convention,
# so the constraints live in existing databases with these exact names.
_OLD_TRANSACTION_TYPE_CHECK_NAME = (
    "ck_financial_transactions_ck_financial_transactions_"
    "transaction_type_valid"
)
_OLD_SOURCE_CHECK_NAME = (
    "ck_financial_transactions_ck_financial_transactions_"
    "single_business_source"
)
_NEW_SOURCE_CHECK_NAME = (
    "ck_financial_transactions_single_business_source"
)


def _ledger_table(*, with_purchase: bool) -> sa.Table:
    """Describe ``financial_transactions`` for offline batch migrations.

    Batch mode on SQLite normally reflects the live table. Supplying this
    definition keeps ``alembic upgrade --sql`` operational while preserving
    the existing constraints and indexes during the table rebuild.
    """
    columns = [
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
    ]
    if with_purchase:
        columns.insert(
            4, sa.Column("purchase_id", sa.Integer(), nullable=True)
        )

    constraints: list[sa.Constraint] = [
        sa.CheckConstraint(
            _TRANSACTION_TYPE_CHECK,
            name=_OLD_TRANSACTION_TYPE_CHECK_NAME,
        ),
        sa.CheckConstraint(
            _NEW_SINGLE_SOURCE_CHECK
            if with_purchase
            else _OLD_SINGLE_SOURCE_CHECK,
            name=(
                _NEW_SOURCE_CHECK_NAME
                if with_purchase
                else _OLD_SOURCE_CHECK_NAME
            ),
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
        sa.PrimaryKeyConstraint(
            "id", name="pk_financial_transactions"
        ),
    ]
    if with_purchase:
        constraints.append(
            sa.ForeignKeyConstraint(
                ["purchase_id"],
                ["purchases.id"],
                name="fk_financial_transactions_purchase_id_purchases",
            )
        )

    table = sa.Table(
        "financial_transactions", sa.MetaData(), *columns, *constraints
    )
    sa.Index(
        "ix_financial_transactions_account_id", table.c.account_id
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
    if with_purchase:
        sa.Index(
            "ix_financial_transactions_purchase_id", table.c.purchase_id
        )
    return table


def upgrade() -> None:
    op.create_table(
        "suppliers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("supplier_type", sa.String(length=50), nullable=True),
        sa.Column("website", sa.String(length=255), nullable=True),
        sa.Column("contact", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name="pk_suppliers"),
    )

    op.create_table(
        "purchases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("supplier_id", sa.Integer(), nullable=True),
        sa.Column("account_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("currency_id", sa.Integer(), nullable=False),
        sa.Column("purchase_date", sa.DateTime(), nullable=False),
        sa.Column("order_number", sa.String(length=100), nullable=True),
        sa.Column("tracking_number", sa.String(length=100), nullable=True),
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
            "status IN ('PENDING', 'PURCHASED', 'SHIPPED', 'IN_TRANSIT', "
            "'PARTIALLY_RECEIVED', 'RECEIVED', 'CANCELLED')",
            name="ck_purchases_status_valid",
        ),
        sa.ForeignKeyConstraint(
            ["supplier_id"],
            ["suppliers.id"],
            name="fk_purchases_supplier_id_suppliers",
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
            name="fk_purchases_account_id_accounts",
        ),
        sa.ForeignKeyConstraint(
            ["currency_id"],
            ["currencies.id"],
            name="fk_purchases_currency_id_currencies",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_purchases"),
    )
    op.create_index(
        "ix_purchases_purchase_date", "purchases", ["purchase_date"]
    )
    op.create_index("ix_purchases_status", "purchases", ["status"])
    op.create_index(
        "ix_purchases_supplier_id", "purchases", ["supplier_id"]
    )

    op.create_table(
        "purchase_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("purchase_id", sa.Integer(), nullable=False),
        sa.Column("variant_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.String(), nullable=False),
        sa.Column("weight", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "quantity > 0",
            name="ck_purchase_items_quantity_positive",
        ),
        sa.ForeignKeyConstraint(
            ["purchase_id"],
            ["purchases.id"],
            name="fk_purchase_items_purchase_id_purchases",
        ),
        sa.ForeignKeyConstraint(
            ["variant_id"],
            ["product_variants.id"],
            name="fk_purchase_items_variant_id_product_variants",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_purchase_items"),
    )
    op.create_index(
        "ix_purchase_items_purchase_id",
        "purchase_items",
        ["purchase_id"],
    )
    op.create_index(
        "ix_purchase_items_variant_id",
        "purchase_items",
        ["variant_id"],
    )

    op.create_table(
        "purchase_costs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("purchase_id", sa.Integer(), nullable=False),
        sa.Column("cost_type", sa.String(length=32), nullable=False),
        sa.Column("amount", sa.String(), nullable=False),
        sa.Column("currency_id", sa.Integer(), nullable=False),
        sa.Column("exchange_rate_id", sa.Integer(), nullable=True),
        sa.Column("allocation_method", sa.String(length=32), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "cost_type IN ('SHIPPING', 'TRANSPORTATION', 'TAX', "
            "'COMMISSION', 'PACKAGING', 'CUSTOMS', 'OTHER')",
            name="ck_purchase_costs_cost_type_valid",
        ),
        sa.CheckConstraint(
            "allocation_method IN ('BY_QUANTITY', 'BY_VALUE', 'BY_WEIGHT', "
            "'MANUAL')",
            name="ck_purchase_costs_allocation_method_valid",
        ),
        sa.ForeignKeyConstraint(
            ["purchase_id"],
            ["purchases.id"],
            name="fk_purchase_costs_purchase_id_purchases",
        ),
        sa.ForeignKeyConstraint(
            ["currency_id"],
            ["currencies.id"],
            name="fk_purchase_costs_currency_id_currencies",
        ),
        sa.ForeignKeyConstraint(
            ["exchange_rate_id"],
            ["exchange_rates.id"],
            name="fk_purchase_costs_exchange_rate_id_exchange_rates",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_purchase_costs"),
    )
    op.create_index(
        "ix_purchase_costs_purchase_id",
        "purchase_costs",
        ["purchase_id"],
    )

    op.create_table(
        "purchase_cost_allocations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("purchase_cost_id", sa.Integer(), nullable=False),
        sa.Column("purchase_item_id", sa.Integer(), nullable=False),
        sa.Column(
            "allocated_original_amount", sa.String(), nullable=False
        ),
        sa.Column(
            "allocated_purchase_currency_amount",
            sa.String(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["purchase_cost_id"],
            ["purchase_costs.id"],
            name=(
                "fk_purchase_cost_allocations_purchase_cost_id_"
                "purchase_costs"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["purchase_item_id"],
            ["purchase_items.id"],
            name=(
                "fk_purchase_cost_allocations_purchase_item_id_"
                "purchase_items"
            ),
        ),
        sa.PrimaryKeyConstraint(
            "id", name="pk_purchase_cost_allocations"
        ),
        sa.UniqueConstraint(
            "purchase_cost_id",
            "purchase_item_id",
            name="uq_purchase_cost_allocations_cost_item",
        ),
    )
    op.create_index(
        "ix_purchase_cost_allocations_purchase_item_id",
        "purchase_cost_allocations",
        ["purchase_item_id"],
    )

    with op.batch_alter_table(
        "financial_transactions",
        copy_from=_ledger_table(with_purchase=False),
    ) as batch_op:
        batch_op.add_column(
            sa.Column("purchase_id", sa.Integer(), nullable=True)
        )
        batch_op.drop_constraint(
            op.f(_OLD_SOURCE_CHECK_NAME),
            type_="check",
        )
        batch_op.create_check_constraint(
            op.f(_NEW_SOURCE_CHECK_NAME),
            _NEW_SINGLE_SOURCE_CHECK,
        )
        batch_op.create_foreign_key(
            "fk_financial_transactions_purchase_id_purchases",
            "purchases",
            ["purchase_id"],
            ["id"],
        )
    op.create_index(
        "ix_financial_transactions_purchase_id",
        "financial_transactions",
        ["purchase_id"],
    )


def downgrade() -> None:
    with op.batch_alter_table(
        "financial_transactions",
        copy_from=_ledger_table(with_purchase=True),
    ) as batch_op:
        batch_op.drop_index("ix_financial_transactions_purchase_id")
        batch_op.drop_constraint(
            "fk_financial_transactions_purchase_id_purchases",
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            op.f(_NEW_SOURCE_CHECK_NAME),
            type_="check",
        )
        batch_op.create_check_constraint(
            op.f(_OLD_SOURCE_CHECK_NAME),
            _OLD_SINGLE_SOURCE_CHECK,
        )
        batch_op.drop_column("purchase_id")

    op.drop_index(
        "ix_purchase_cost_allocations_purchase_item_id",
        table_name="purchase_cost_allocations",
    )
    op.drop_table("purchase_cost_allocations")

    op.drop_index(
        "ix_purchase_costs_purchase_id", table_name="purchase_costs"
    )
    op.drop_table("purchase_costs")

    op.drop_index(
        "ix_purchase_items_variant_id", table_name="purchase_items"
    )
    op.drop_index(
        "ix_purchase_items_purchase_id", table_name="purchase_items"
    )
    op.drop_table("purchase_items")

    op.drop_index("ix_purchases_supplier_id", table_name="purchases")
    op.drop_index("ix_purchases_status", table_name="purchases")
    op.drop_index("ix_purchases_purchase_date", table_name="purchases")
    op.drop_table("purchases")

    op.drop_table("suppliers")
