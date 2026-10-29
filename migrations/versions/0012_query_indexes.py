"""Add indexes for inventory history and purchase-item lookups.

Revision ID: 0012_query_indexes
Revises: 0011_settings
Create Date: 2026-10-28

These compound indexes cover ordered repository queries used by the inventory
screens and by FIFO/costing lookups, avoiding an extra sort step on SQLite.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0012_query_indexes"
down_revision: str | Sequence[str] | None = "0011_settings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_inventory_lots_purchase_item_id_received_at",
        "inventory_lots",
        ["purchase_item_id", "received_at"],
    )
    op.create_index(
        "ix_inventory_movements_variant_id_movement_date",
        "inventory_movements",
        ["variant_id", "movement_date"],
    )
    op.create_index(
        "ix_inventory_movements_inventory_lot_id_movement_date",
        "inventory_movements",
        ["inventory_lot_id", "movement_date"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_inventory_movements_inventory_lot_id_movement_date",
        table_name="inventory_movements",
    )
    op.drop_index(
        "ix_inventory_movements_variant_id_movement_date",
        table_name="inventory_movements",
    )
    op.drop_index(
        "ix_inventory_lots_purchase_item_id_received_at",
        table_name="inventory_lots",
    )
