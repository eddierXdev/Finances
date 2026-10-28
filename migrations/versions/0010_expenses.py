"""Add operating expenses and the expense ledger source.

Revision ID: 0010_expenses
Revises: 0009_supplier_returns
Create Date: 2026-10-27

Monetary amounts use the same exact-text strategy as previous migrations on
SQLite. Expenses are separate from purchase acquisition costs and always create
a negative ``EXPENSE`` financial transaction.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0010_expenses"
down_revision: str | Sequence[str] | None = "0009_supplier_returns"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OLD_SINGLE_SOURCE_CHECK = (
    "((CASE WHEN purchase_id IS NOT NULL THEN 1 ELSE 0 END) + "
    "(CASE WHEN sale_id IS NOT NULL THEN 1 ELSE 0 END) + "
    "(CASE WHEN customer_return_id IS NOT NULL THEN 1 ELSE 0 END) + "
    "(CASE WHEN supplier_return_id IS NOT NULL THEN 1 ELSE 0 END) + "
    "(CASE WHEN capital_movement_id IS NOT NULL THEN 1 ELSE 0 END) + "
    "(CASE WHEN account_transfer_id IS NOT NULL THEN 1 ELSE 0 END)) "
    "<= 1"
)
_NEW_SINGLE_SOURCE_CHECK = (
    "((CASE WHEN purchase_id IS NOT NULL THEN 1 ELSE 0 END) + "
    "(CASE WHEN sale_id IS NOT NULL THEN 1 ELSE 0 END) + "
    "(CASE WHEN expense_id IS NOT NULL THEN 1 ELSE 0 END) + "
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
_EXPENSE_TYPES = (
    "ADVERTISING",
    "TRANSPORTATION",
    "PACKAGING",
    "INTERNET",
    "DELIVERY",
    "COMMISSION",
    "OTHER",
)


def _ledger_table(*, with_expense: bool) -> sa.Table:
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
        sa.Column("supplier_return_id", sa.Integer(), nullable=True),
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
    if with_expense:
        columns.insert(
            7, sa.Column("expense_id", sa.Integer(), nullable=True)
        )

    constraints: list[sa.Constraint] = [
        sa.CheckConstraint(
            _TRANSACTION_TYPE_CHECK,
            name=_TRANSACTION_TYPE_CHECK_NAME,
        ),
        sa.CheckConstraint(
            _NEW_SINGLE_SOURCE_CHECK
            if with_expense
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
            ["supplier_return_id"],
            ["supplier_returns.id"],
            name=(
                "fk_financial_transactions_supplier_return_id_"
                "supplier_returns"
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
    if with_expense:
        constraints.append(
            sa.ForeignKeyConstraint(
                ["expense_id"],
                ["expenses.id"],
                name="fk_financial_transactions_expense_id_expenses",
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
    if with_expense:
        sa.Index(
            "ix_financial_transactions_expense_id", table.c.expense_id
        )
    sa.Index(
        "ix_financial_transactions_customer_return_id",
        table.c.customer_return_id,
    )
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
        "expenses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("expense_type", sa.String(length=32), nullable=False),
        sa.Column("amount", sa.String(), nullable=False),
        sa.Column("currency_id", sa.Integer(), nullable=False),
        sa.Column("expense_date", sa.DateTime(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "expense_type IN ("
            + ", ".join(f"'{value}'" for value in _EXPENSE_TYPES)
            + ")",
            name="ck_expenses_expense_type_valid",
        ),
        sa.CheckConstraint(
            "amount > 0",
            name="ck_expenses_amount_positive",
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
            name="fk_expenses_account_id_accounts",
        ),
        sa.ForeignKeyConstraint(
            ["currency_id"],
            ["currencies.id"],
            name="fk_expenses_currency_id_currencies",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_expenses"),
    )
    op.create_index(
        "ix_expenses_account_id",
        "expenses",
        ["account_id"],
    )
    op.create_index(
        "ix_expenses_expense_date",
        "expenses",
        ["expense_date"],
    )

    with op.batch_alter_table(
        "financial_transactions",
        copy_from=_ledger_table(with_expense=False),
    ) as batch_op:
        batch_op.add_column(
            sa.Column("expense_id", sa.Integer(), nullable=True)
        )
        batch_op.drop_constraint(
            op.f(_SOURCE_CHECK_NAME), type_="check"
        )
        batch_op.create_check_constraint(
            op.f(_SOURCE_CHECK_NAME), _NEW_SINGLE_SOURCE_CHECK
        )
        batch_op.create_foreign_key(
            "fk_financial_transactions_expense_id_expenses",
            "expenses",
            ["expense_id"],
            ["id"],
        )
    op.create_index(
        "ix_financial_transactions_expense_id",
        "financial_transactions",
        ["expense_id"],
    )


def downgrade() -> None:
    with op.batch_alter_table(
        "financial_transactions",
        copy_from=_ledger_table(with_expense=True),
    ) as batch_op:
        batch_op.drop_index("ix_financial_transactions_expense_id")
        batch_op.drop_constraint(
            "fk_financial_transactions_expense_id_expenses",
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            op.f(_SOURCE_CHECK_NAME), type_="check"
        )
        batch_op.create_check_constraint(
            op.f(_SOURCE_CHECK_NAME), _OLD_SINGLE_SOURCE_CHECK
        )
        batch_op.drop_column("expense_id")

    op.drop_index("ix_expenses_expense_date", table_name="expenses")
    op.drop_index("ix_expenses_account_id", table_name="expenses")
    op.drop_table("expenses")
