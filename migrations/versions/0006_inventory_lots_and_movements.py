"""Create inventory lots and their traceable stock movements.

Revision ID: 0006_inventory_lots_and_movements
Revises: 0005_purchases
Create Date: 2026-10-27

On SQLite, monetary amounts are stored as text to preserve exact decimal
arithmetic. Received quantity is derived from ``inventory_lots``; no separate
received-quantity column is stored on ``purchase_items``.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006_inventory_lots_and_movements"
down_revision: str | Sequence[str] | None = "0005_purchases"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_MOVEMENT_TYPES = (
    "PURCHASE_RECEIVED",
    "SALE",
    "CUSTOMER_RETURN",
    "SUPPLIER_RETURN",
    "ADJUSTMENT_IN",
    "ADJUSTMENT_OUT",
    "DAMAGED",
    "LOST",
)
_POSITIVE_TYPES = (
    "PURCHASE_RECEIVED",
    "CUSTOMER_RETURN",
    "ADJUSTMENT_IN",
)
_NEGATIVE_TYPES = (
    "SALE",
    "SUPPLIER_RETURN",
    "ADJUSTMENT_OUT",
    "DAMAGED",
    "LOST",
)


def _in_list(values: tuple[str, ...]) -> str:
    return "(" + ", ".join(f"'{value}'" for value in values) + ")"


def upgrade() -> None:
    op.create_table(
        "inventory_lots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("purchase_item_id", sa.Integer(), nullable=False),
        sa.Column("variant_id", sa.Integer(), nullable=False),
        sa.Column("acquired_quantity", sa.Integer(), nullable=False),
        sa.Column("remaining_quantity", sa.Integer(), nullable=False),
        # ExactDecimal stores text on SQLite to avoid floating-point values.
        sa.Column("unit_cost", sa.String(), nullable=False),
        sa.Column("currency_id", sa.Integer(), nullable=False),
        sa.Column("received_at", sa.DateTime(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "acquired_quantity > 0",
            name="ck_inventory_lots_acquired_quantity_positive",
        ),
        sa.CheckConstraint(
            "remaining_quantity >= 0",
            name="ck_inventory_lots_remaining_quantity_non_negative",
        ),
        sa.CheckConstraint(
            "remaining_quantity <= acquired_quantity",
            name="ck_inventory_lots_remaining_within_acquired",
        ),
        sa.CheckConstraint(
            "unit_cost >= 0",
            name="ck_inventory_lots_unit_cost_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["purchase_item_id"],
            ["purchase_items.id"],
            name="fk_inventory_lots_purchase_item_id_purchase_items",
        ),
        sa.ForeignKeyConstraint(
            ["variant_id"],
            ["product_variants.id"],
            name="fk_inventory_lots_variant_id_product_variants",
        ),
        sa.ForeignKeyConstraint(
            ["currency_id"],
            ["currencies.id"],
            name="fk_inventory_lots_currency_id_currencies",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_inventory_lots"),
    )
    op.create_index(
        "ix_inventory_lots_variant_id_received_at",
        "inventory_lots",
        ["variant_id", "received_at"],
    )

    op.create_table(
        "inventory_movements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("variant_id", sa.Integer(), nullable=False),
        sa.Column("inventory_lot_id", sa.Integer(), nullable=True),
        sa.Column("movement_type", sa.String(length=32), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_cost", sa.String(), nullable=True),
        sa.Column("currency_id", sa.Integer(), nullable=True),
        sa.Column("reference_type", sa.String(length=32), nullable=True),
        sa.Column("reference_id", sa.Integer(), nullable=True),
        sa.Column("movement_date", sa.DateTime(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "movement_type IN " + _in_list(_MOVEMENT_TYPES),
            name="ck_inventory_movements_movement_type_valid",
        ),
        sa.CheckConstraint(
            "(quantity > 0 AND movement_type IN "
            + _in_list(_POSITIVE_TYPES)
            + ") OR (quantity < 0 AND movement_type IN "
            + _in_list(_NEGATIVE_TYPES)
            + ")",
            name="ck_inventory_movements_quantity_sign_valid",
        ),
        sa.CheckConstraint(
            "unit_cost IS NULL OR unit_cost >= 0",
            name="ck_inventory_movements_unit_cost_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["variant_id"],
            ["product_variants.id"],
            name="fk_inventory_movements_variant_id_product_variants",
        ),
        sa.ForeignKeyConstraint(
            ["inventory_lot_id"],
            ["inventory_lots.id"],
            name="fk_inventory_movements_inventory_lot_id_inventory_lots",
        ),
        sa.ForeignKeyConstraint(
            ["currency_id"],
            ["currencies.id"],
            name="fk_inventory_movements_currency_id_currencies",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_inventory_movements"),
    )
    op.create_index(
        "ix_inventory_movements_variant_id",
        "inventory_movements",
        ["variant_id"],
    )
    op.create_index(
        "ix_inventory_movements_movement_date",
        "inventory_movements",
        ["movement_date"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_inventory_movements_movement_date",
        table_name="inventory_movements",
    )
    op.drop_index(
        "ix_inventory_movements_variant_id",
        table_name="inventory_movements",
    )
    op.drop_table("inventory_movements")

    op.drop_index(
        "ix_inventory_lots_variant_id_received_at",
        table_name="inventory_lots",
    )
    op.drop_table("inventory_lots")
