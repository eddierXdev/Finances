"""Add key/value application settings.

Revision ID: 0011_settings
Revises: 0010_expenses
Create Date: 2026-10-28

The first setting is the backup directory. Values are stored as text so future
simple preferences do not require a schema change.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0011_settings"
down_revision: str | Sequence[str] | None = "0010_expenses"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "settings",
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("key", name="pk_settings"),
    )


def downgrade() -> None:
    op.drop_table("settings")
