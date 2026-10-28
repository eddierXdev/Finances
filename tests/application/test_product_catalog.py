"""Product catalog application-service tests."""

from __future__ import annotations

import pytest

from app.application.attributes.manage_attributes import (
    CreateAttributeRequest,
    CreateAttributeValueRequest,
)
from app.application.products.catalog import ProductCatalogService
from app.application.products.categories import CreateCategoryRequest
from app.application.products.create_product import (
    CreateProductRequest,
    ProductVariantRequest,
)
from app.application.products.update_product import UpdateProductRequest
from app.application.products.variants import (
    CreateVariantRequest,
    UpdateVariantRequest,
)
from app.domain.exceptions import (
    DuplicateSkuError,
    ProductNotFoundError,
    VariantNotFoundError,
)
from app.domain.value_objects.money import Money
from app.infrastructure.database.session import create_session_factory
from app.infrastructure.database.unit_of_work import (
    SqlAlchemyUnitOfWorkFactory,
)


@pytest.fixture
def unit_of_work_factory(migrated_engine) -> SqlAlchemyUnitOfWorkFactory:
    return SqlAlchemyUnitOfWorkFactory(
        create_session_factory(migrated_engine)
    )


@pytest.fixture
def catalog(unit_of_work_factory) -> ProductCatalogService:
    return ProductCatalogService(unit_of_work_factory)


def _usd(catalog: ProductCatalogService):
    return next(
        currency
        for currency in catalog.list_enabled_currencies()
        if currency.code == "USD"
    )


def test_categories_can_be_created_and_listed(catalog) -> None:
    created = catalog.create_category(
        CreateCategoryRequest(name="Clothing", description="Apparel")
    )

    categories = catalog.list_categories()

    assert created.id is not None
    assert [category.name for category in categories] == ["Clothing"]
    assert categories[0].description == "Apparel"


def test_product_creation_and_listing_with_descriptive_data(catalog) -> None:
    category = catalog.create_category(
        CreateCategoryRequest(name="Clothing")
    )
    usd = _usd(catalog)

    product = catalog.create_product(
        CreateProductRequest(
            name="T-Shirt",
            category_id=category.id,
            description="Cotton shirt",
            brand="North",
            default_selling_price=Money("19.99", usd),
            variants=(ProductVariantRequest(sku="TS-001", variant_name="Red"),),
        )
    )

    rows = catalog.list_products()

    assert product.id is not None
    assert len(rows) == 1
    row = rows[0]
    assert row.product_id == product.id
    assert row.name == "T-Shirt"
    assert row.brand == "North"
    assert row.category_id == category.id
    assert row.category_name == "Clothing"
    assert row.description == "Cotton shirt"
    assert row.default_selling_price == Money("19.99", usd)
    assert row.variant_count == 1
    assert row.is_active is True


def test_product_without_variants_lists_the_default_variant(catalog) -> None:
    catalog.create_product(CreateProductRequest(name="Plain Mug"))

    rows = catalog.list_products()

    assert rows[0].variant_count == 1
    assert rows[0].default_selling_price is None


def test_inactive_products_are_excluded_unless_requested(
    catalog, unit_of_work_factory
) -> None:
    created = catalog.create_product(CreateProductRequest(name="Old Stock"))
    assert created.id is not None

    with unit_of_work_factory.unit_of_work() as uow:
        product = uow.products.get_by_id(created.id)
        assert product is not None
        uow.products.save(product.deactivate())
        uow.commit()

    assert catalog.list_products() == ()
    rows = catalog.list_products(include_inactive=True)
    assert len(rows) == 1
    assert rows[0].is_active is False


def test_duplicate_sku_rolls_back_the_whole_product(catalog) -> None:
    with pytest.raises(DuplicateSkuError):
        catalog.create_product(
            CreateProductRequest(
                name="Duplicate",
                variants=(
                    ProductVariantRequest(sku="SAME"),
                    ProductVariantRequest(sku="SAME"),
                ),
            )
        )

    assert catalog.list_products(include_inactive=True) == ()


def test_product_data_can_be_updated_without_losing_activation(
    catalog,
) -> None:
    created = catalog.create_product(CreateProductRequest(name="Old Name"))
    assert created.id is not None
    usd = _usd(catalog)

    updated = catalog.update_product(
        UpdateProductRequest(
            product_id=created.id,
            name="New Name",
            description="Updated description",
            brand="New Brand",
            default_selling_price=Money("15.00", usd),
        )
    )

    assert updated.name == "New Name"
    assert updated.description == "Updated description"
    assert updated.brand == "New Brand"
    assert updated.default_selling_price == Money("15.00", usd)
    assert updated.is_active is True

    deactivated = catalog.set_product_active(created.id, is_active=False)
    assert deactivated.is_active is False
    assert catalog.list_products() == ()
    assert catalog.list_products(include_inactive=True)[0].is_active is False

    activated = catalog.set_product_active(created.id, is_active=True)
    assert activated.is_active is True


def test_missing_products_raise_clear_errors(catalog) -> None:
    with pytest.raises(ProductNotFoundError):
        catalog.update_product(
            UpdateProductRequest(product_id=999, name="Missing")
        )
    with pytest.raises(ProductNotFoundError):
        catalog.set_product_active(999, is_active=False)


def test_variants_support_attributes_and_activation(catalog) -> None:
    product = catalog.create_product(
        CreateProductRequest(
            name="T-Shirt",
            variants=(ProductVariantRequest(sku="TS-001", variant_name="Red"),),
        )
    )
    assert product.id is not None

    color = catalog.create_attribute(CreateAttributeRequest(name="Color"))
    assert color.id is not None
    red = catalog.create_attribute_value(
        CreateAttributeValueRequest(attribute_id=color.id, value="Red")
    )
    blue = catalog.create_attribute_value(
        CreateAttributeValueRequest(attribute_id=color.id, value="Blue")
    )

    variant_id = catalog.list_variants(product.id)[0].variant_id
    catalog.update_variant(
        UpdateVariantRequest(
            variant_id=variant_id,
            sku="TS-001",
            variant_name="Red",
            attribute_value_ids=(red.id,),
        )
    )

    rows = catalog.list_variants(product.id)
    assert len(rows) == 1
    assert rows[0].attribute_value_ids == (red.id,)
    assert rows[0].attribute_labels == ("Color: Red",)

    catalog.update_variant(
        UpdateVariantRequest(
            variant_id=variant_id,
            sku="TS-001",
            variant_name="Blue",
            attribute_value_ids=(blue.id,),
        )
    )
    rows = catalog.list_variants(product.id)
    assert rows[0].variant_name == "Blue"
    assert rows[0].attribute_labels == ("Color: Blue",)

    catalog.set_variant_active(variant_id, is_active=False)
    assert catalog.list_variants(product.id) == ()
    inactive = catalog.list_variants(
        product.id, include_inactive=True
    )
    assert inactive[0].is_active is False

    catalog.set_variant_active(variant_id, is_active=True)
    assert catalog.list_variants(product.id)[0].is_active is True


def test_new_variant_can_assign_existing_attribute_values(catalog) -> None:
    product = catalog.create_product(
        CreateProductRequest(name="Mug", variants=(ProductVariantRequest(),))
    )
    assert product.id is not None
    size = catalog.create_attribute(CreateAttributeRequest(name="Size"))
    assert size.id is not None
    large = catalog.create_attribute_value(
        CreateAttributeValueRequest(attribute_id=size.id, value="Large")
    )
    assert large.id is not None

    created = catalog.create_variant(
        CreateVariantRequest(
            product_id=product.id,
            sku="MUG-L",
            variant_name="Large",
            attribute_value_ids=(large.id,),
        )
    )

    rows = catalog.list_variants(product.id)
    assert len(rows) == 2
    assert any(row.variant_id == created.id for row in rows)
    assert any(
        row.attribute_labels == ("Size: Large",) for row in rows
    )


def test_missing_variants_raise_clear_errors(catalog) -> None:
    with pytest.raises(VariantNotFoundError):
        catalog.update_variant(
            UpdateVariantRequest(variant_id=999, sku="MISSING")
        )
    with pytest.raises(VariantNotFoundError):
        catalog.set_variant_active(999, is_active=False)
