"""Establish the initial migration baseline.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-10-27

Phase 0 bootstraps the tooling only. Domain tables are introduced by the
migration belonging to the phase that defines them, keeping the schema
history aligned with the roadmap.
"""

from __future__ import annotations

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "0001_baseline"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Baseline revision: no domain tables yet."""


def downgrade() -> None:
    """Nothing to revert for the baseline revision."""
