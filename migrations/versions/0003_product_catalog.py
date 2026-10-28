"""Create the product catalog schema.

Revision ID: 0003_product_catalog
Revises: 0002_currency_and_exchange_rates
Create Date: 2026-10-27
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_product_catalog"
down_revision: str | Sequence[str] | None = "0002_currency_and_exchange_rates"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_categories"),
    )

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("brand", sa.String(length=100), nullable=True),
        # ExactDecimal stores text on SQLite to avoid floating-point values.
        sa.Column("default_selling_price", sa.String(), nullable=True),
        sa.Column("selling_currency_id", sa.Integer(), nullable=True),
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
        sa.CheckConstraint(
            "(default_selling_price IS NULL) = (selling_currency_id IS NULL)",
            name="ck_products_selling_price_currency_pair",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            name="fk_products_category_id_categories",
        ),
        sa.ForeignKeyConstraint(
            ["selling_currency_id"],
            ["currencies.id"],
            name="fk_products_selling_currency_id_currencies",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_products"),
    )
    op.create_index("ix_products_category_id", "products", ["category_id"])

    op.create_table(
        "product_variants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("sku", sa.String(length=100), nullable=True),
        sa.Column("variant_name", sa.String(length=150), nullable=True),
        sa.Column("barcode", sa.String(length=100), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name="fk_product_variants_product_id_products",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_product_variants"),
        sa.UniqueConstraint("sku", name="uq_product_variants_sku"),
    )
    op.create_index(
        "ix_product_variants_product_id",
        "product_variants",
        ["product_id"],
    )

    op.create_table(
        "attributes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_attributes"),
    )

    op.create_table(
        "attribute_values",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("attribute_id", sa.Integer(), nullable=False),
        sa.Column("value", sa.String(length=150), nullable=False),
        sa.ForeignKeyConstraint(
            ["attribute_id"],
            ["attributes.id"],
            name="fk_attribute_values_attribute_id_attributes",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_attribute_values"),
    )
    op.create_index(
        "ix_attribute_values_attribute_id",
        "attribute_values",
        ["attribute_id"],
    )

    op.create_table(
        "variant_attribute_values",
        sa.Column("variant_id", sa.Integer(), nullable=False),
        sa.Column("attribute_value_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["variant_id"],
            ["product_variants.id"],
            name="fk_variant_attribute_values_variant_id_product_variants",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["attribute_value_id"],
            ["attribute_values.id"],
            name=(
                "fk_variant_attribute_values_attribute_value_id_"
                "attribute_values"
            ),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "variant_id",
            "attribute_value_id",
            name="pk_variant_attribute_values",
        ),
    )
    op.create_index(
        "ix_variant_attribute_values_attribute_value_id",
        "variant_attribute_values",
        ["attribute_value_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_variant_attribute_values_attribute_value_id",
        table_name="variant_attribute_values",
    )
    op.drop_table("variant_attribute_values")
    op.drop_index("ix_attribute_values_attribute_id", table_name="attribute_values")
    op.drop_table("attribute_values")
    op.drop_table("attributes")
    op.drop_index("ix_product_variants_product_id", table_name="product_variants")
    op.drop_table("product_variants")
    op.drop_index("ix_products_category_id", table_name="products")
    op.drop_table("products")
    op.drop_table("categories")
