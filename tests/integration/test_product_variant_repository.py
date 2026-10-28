"""Product-variant repository tests against a migrated database."""

from __future__ import annotations

import pytest

from app.domain.entities.attribute import Attribute, AttributeValue
from app.domain.entities.product import Product
from app.domain.entities.product_variant import ProductVariant
from app.domain.exceptions import (
    AttributeValueNotFoundError,
    DuplicateSkuError,
    ProductNotFoundError,
    VariantNotFoundError,
)
from app.infrastructure.database.repositories import (
    SqlAlchemyAttributeRepository,
    SqlAlchemyAttributeValueRepository,
    SqlAlchemyProductRepository,
    SqlAlchemyProductVariantRepository,
)


def _product(db_session, name: str = "T-Shirt") -> Product:
    product = SqlAlchemyProductRepository(db_session).add(Product(name=name))
    assert product.id is not None
    return product


def test_variant_is_stored_and_queried_by_id_and_sku(db_session) -> None:
    product = _product(db_session)
    repository = SqlAlchemyProductVariantRepository(db_session)

    stored = repository.add(
        ProductVariant(
            product_id=product.id,
            sku="TS-BLUE-M",
            variant_name="Blue / M",
            barcode="123456",
        )
    )

    assert stored.id is not None
    assert repository.get_by_id(stored.id) == stored
    assert repository.get_by_sku(" TS-BLUE-M ") == stored


def test_sku_uniqueness_is_enforced_across_products(db_session) -> None:
    first_product = _product(db_session, "First")
    second_product = _product(db_session, "Second")
    repository = SqlAlchemyProductVariantRepository(db_session)
    repository.add(ProductVariant(product_id=first_product.id, sku="SHARED-SKU"))

    with pytest.raises(DuplicateSkuError):
        repository.add(
            ProductVariant(product_id=second_product.id, sku="SHARED-SKU")
        )


def test_multiple_variants_without_sku_are_allowed(db_session) -> None:
    product = _product(db_session)
    repository = SqlAlchemyProductVariantRepository(db_session)

    first = repository.add(ProductVariant.default_for(product.id))
    second = repository.add(ProductVariant.default_for(product.id))

    assert first.id != second.id
    assert first.sku is None
    assert second.sku is None


def test_variant_with_unknown_product_is_rejected(db_session) -> None:
    repository = SqlAlchemyProductVariantRepository(db_session)

    with pytest.raises(ProductNotFoundError):
        repository.add(ProductVariant.default_for(999))


def test_inactive_variants_are_excluded_from_active_listing(db_session) -> None:
    product = _product(db_session)
    repository = SqlAlchemyProductVariantRepository(db_session)
    stored = repository.add(ProductVariant(product_id=product.id, sku="OLD-SKU"))

    repository.save(stored.deactivate())

    assert repository.list_for_product(product.id) == []
    inactive_variants = repository.list_for_product(
        product.id, include_inactive=True
    )
    assert [variant.sku for variant in inactive_variants] == ["OLD-SKU"]


def test_variant_update_rejects_a_duplicate_sku(db_session) -> None:
    product = _product(db_session)
    repository = SqlAlchemyProductVariantRepository(db_session)
    repository.add(ProductVariant(product_id=product.id, sku="FIRST"))
    second = repository.add(
        ProductVariant(product_id=product.id, sku="SECOND")
    )

    with pytest.raises(DuplicateSkuError):
        repository.save(ProductVariant(product_id=product.id, id=second.id, sku="FIRST"))


def test_unknown_variant_update_is_rejected(db_session) -> None:
    repository = SqlAlchemyProductVariantRepository(db_session)

    with pytest.raises(VariantNotFoundError):
        repository.save(ProductVariant(product_id=1, id=999))


def test_attribute_values_can_be_replaced_and_queried(db_session) -> None:
    product = _product(db_session)
    variant = SqlAlchemyProductVariantRepository(db_session).add(
        ProductVariant(product_id=product.id, sku="TS-RED")
    )
    color = SqlAlchemyAttributeRepository(db_session).add(Attribute(name="Color"))
    value_repository = SqlAlchemyAttributeValueRepository(db_session)
    red = value_repository.add(AttributeValue(attribute_id=color.id, value="Red"))
    blue = value_repository.add(AttributeValue(attribute_id=color.id, value="Blue"))
    repository = SqlAlchemyProductVariantRepository(db_session)

    repository.set_attribute_values(variant.id, [blue.id, red.id, red.id])
    assert repository.get_attribute_value_ids(variant.id) == sorted(
        [red.id, blue.id]
    )

    repository.set_attribute_values(variant.id, [red.id])
    assert repository.get_attribute_value_ids(variant.id) == [red.id]


def test_unknown_attribute_value_is_rejected(db_session) -> None:
    product = _product(db_session)
    variant = SqlAlchemyProductVariantRepository(db_session).add(
        ProductVariant.default_for(product.id)
    )
    repository = SqlAlchemyProductVariantRepository(db_session)

    with pytest.raises(AttributeValueNotFoundError):
        repository.set_attribute_values(variant.id, [999])
