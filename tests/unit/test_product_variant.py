"""Product variant entity tests."""

from __future__ import annotations

import pytest

from app.domain.entities.product_variant import ProductVariant


def test_default_variant_has_no_sku_or_name() -> None:
    variant = ProductVariant.default_for(1)

    assert variant.product_id == 1
    assert variant.sku is None
    assert variant.variant_name is None
    assert variant.barcode is None
    assert variant.is_active is True
    assert variant.id is None


def test_variant_normalizes_optional_text() -> None:
    variant = ProductVariant(
        product_id=1,
        sku="  SKU-1  ",
        variant_name="  Blue  ",
        barcode="  123  ",
    )

    assert variant.sku == "SKU-1"
    assert variant.variant_name == "Blue"
    assert variant.barcode == "123"


def test_blank_variant_fields_become_none() -> None:
    variant = ProductVariant(
        product_id=1,
        sku="   ",
        variant_name="  ",
        barcode="  ",
    )

    assert variant.sku is None
    assert variant.variant_name is None
    assert variant.barcode is None


@pytest.mark.parametrize("product_id", [0, -1])
def test_product_id_must_be_positive(product_id: int) -> None:
    with pytest.raises(ValueError):
        ProductVariant(product_id=product_id)


def test_deactivate_and_activate_return_new_states() -> None:
    variant = ProductVariant(product_id=1, sku="SKU-1")

    inactive = variant.deactivate()

    assert inactive.is_active is False
    assert variant.is_active is True
    assert inactive.activate().is_active is True
