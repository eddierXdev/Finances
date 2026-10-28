"""Create-product use case tests."""

from __future__ import annotations

import pytest

from app.application.products.create_product import (
    CreateProduct,
    CreateProductRequest,
    ProductVariantRequest,
)
from app.domain.entities.attribute import Attribute, AttributeValue
from app.domain.entities.category import Category
from app.domain.entities.currency import Currency
from app.domain.entities.product import Product
from app.domain.exceptions import DuplicateSkuError
from app.domain.value_objects.money import Money
from app.infrastructure.database.repositories import (
    SqlAlchemyAttributeRepository,
    SqlAlchemyAttributeValueRepository,
    SqlAlchemyCategoryRepository,
    SqlAlchemyCurrencyRepository,
    SqlAlchemyProductRepository,
    SqlAlchemyProductVariantRepository,
)


def _service(db_session) -> tuple[CreateProduct, SqlAlchemyProductVariantRepository]:
    variants = SqlAlchemyProductVariantRepository(db_session)
    return (
        CreateProduct(SqlAlchemyProductRepository(db_session), variants),
        variants,
    )


def test_creating_a_product_without_variants_adds_a_default_variant(
    db_session,
) -> None:
    service, variants = _service(db_session)

    product = service.execute(CreateProductRequest(name="Plain T-Shirt"))

    assert product.id is not None
    stored_variants = variants.list_for_product(product.id)
    assert len(stored_variants) == 1
    assert stored_variants[0].variant_name is None
    assert stored_variants[0].sku is None


def test_creating_a_product_with_explicit_variants_and_attributes(
    db_session,
) -> None:
    attribute = SqlAlchemyAttributeRepository(db_session).add(
        Attribute(name="Color")
    )
    red = SqlAlchemyAttributeValueRepository(db_session).add(
        AttributeValue(attribute_id=attribute.id, value="Red")
    )
    service, variants = _service(db_session)

    product = service.execute(
        CreateProductRequest(
            name="T-Shirt",
            variants=(
                ProductVariantRequest(
                    sku="TS-RED",
                    variant_name="Red",
                    attribute_value_ids=(red.id,),
                ),
                ProductVariantRequest(sku="TS-BLANK"),
            ),
        )
    )

    stored_variants = variants.list_for_product(product.id)
    assert [variant.sku for variant in stored_variants] == ["TS-RED", "TS-BLANK"]
    red_variant = variants.get_by_sku("TS-RED")
    assert red_variant is not None
    assert variants.get_attribute_value_ids(red_variant.id) == [red.id]


def test_creating_a_product_persists_category_and_default_price(db_session) -> None:
    category = SqlAlchemyCategoryRepository(db_session).add(
        Category(name="Clothing")
    )
    usd = SqlAlchemyCurrencyRepository(db_session).get_by_code("USD")
    assert usd is not None
    service, _ = _service(db_session)

    product = service.execute(
        CreateProductRequest(
            name="T-Shirt",
            category_id=category.id,
            default_selling_price=Money("19.99", usd),
        )
    )

    stored = SqlAlchemyProductRepository(db_session).get_by_id(product.id)
    assert stored is not None
    assert stored.category_id == category.id
    assert stored.default_selling_price == Money("19.99", usd)


def test_duplicate_skus_roll_back_the_whole_product_creation(db_session) -> None:
    service, _ = _service(db_session)
    repository = SqlAlchemyProductRepository(db_session)

    with pytest.raises(DuplicateSkuError):
        service.execute(
            CreateProductRequest(
                name="Duplicate SKUs",
                variants=(
                    ProductVariantRequest(sku="DUPLICATED"),
                    ProductVariantRequest(sku="DUPLICATED"),
                ),
            )
        )

    db_session.rollback()
    assert repository.list_all(include_inactive=True) == []
