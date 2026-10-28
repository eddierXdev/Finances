"""Application service for the catalog screen.

The service owns transaction boundaries so the presentation layer never sees a
database session and never commits on its own.
"""

from __future__ import annotations

from app.application.attributes.manage_attributes import (
    AttributeSummary,
    CreateAttribute,
    CreateAttributeRequest,
    CreateAttributeValue,
    CreateAttributeValueRequest,
    ListAttributes,
)
from app.application.products.categories import (
    CreateCategory,
    CreateCategoryRequest,
)
from app.application.products.create_product import (
    CreateProduct,
    CreateProductRequest,
)
from app.application.products.list_products import (
    ListProducts,
    ProductListItem,
)
from app.application.products.set_product_active import SetProductActive
from app.application.products.update_product import (
    UpdateProduct,
    UpdateProductRequest,
)
from app.application.products.variants import (
    CreateVariant,
    CreateVariantRequest,
    ListProductVariants,
    SetVariantActive,
    UpdateVariant,
    UpdateVariantRequest,
    VariantListItem,
)
from app.application.unit_of_work import UnitOfWorkFactory
from app.domain.entities.attribute import Attribute, AttributeValue
from app.domain.entities.category import Category
from app.domain.entities.currency import Currency
from app.domain.entities.product import Product
from app.domain.entities.product_variant import ProductVariant


class ProductCatalogService:
    """Read and write catalog data for the Products screen."""

    def __init__(self, unit_of_work: UnitOfWorkFactory) -> None:
        self._unit_of_work = unit_of_work

    def list_products(
        self, *, include_inactive: bool = False
    ) -> tuple[ProductListItem, ...]:
        with self._unit_of_work.unit_of_work() as uow:
            return ListProducts(
                uow.products,
                uow.variants,
                uow.categories,
            ).execute(include_inactive=include_inactive)

    def create_product(self, request: CreateProductRequest) -> Product:
        with self._unit_of_work.unit_of_work() as uow:
            product = CreateProduct(uow.products, uow.variants).execute(
                request
            )
            uow.commit()
            return product

    def update_product(self, request: UpdateProductRequest) -> Product:
        with self._unit_of_work.unit_of_work() as uow:
            product = UpdateProduct(uow.products).execute(request)
            uow.commit()
            return product

    def set_product_active(
        self, product_id: int, *, is_active: bool
    ) -> Product:
        with self._unit_of_work.unit_of_work() as uow:
            product = SetProductActive(uow.products).execute(
                product_id, is_active=is_active
            )
            uow.commit()
            return product

    def list_categories(self) -> tuple[Category, ...]:
        with self._unit_of_work.unit_of_work() as uow:
            return tuple(uow.categories.list_all())

    def create_category(self, request: CreateCategoryRequest) -> Category:
        with self._unit_of_work.unit_of_work() as uow:
            category = CreateCategory(uow.categories).execute(request)
            uow.commit()
            return category

    def list_enabled_currencies(self) -> tuple[Currency, ...]:
        with self._unit_of_work.unit_of_work() as uow:
            return tuple(uow.currencies.list_all(enabled_only=True))

    def list_variants(
        self, product_id: int, *, include_inactive: bool = False
    ) -> tuple[VariantListItem, ...]:
        with self._unit_of_work.unit_of_work() as uow:
            return ListProductVariants(
                uow.variants,
                uow.attribute_values,
                uow.attributes,
            ).execute(product_id, include_inactive=include_inactive)

    def create_variant(
        self, request: CreateVariantRequest
    ) -> ProductVariant:
        with self._unit_of_work.unit_of_work() as uow:
            variant = CreateVariant(uow.variants).execute(request)
            uow.commit()
            return variant

    def update_variant(
        self, request: UpdateVariantRequest
    ) -> ProductVariant:
        with self._unit_of_work.unit_of_work() as uow:
            variant = UpdateVariant(uow.variants).execute(request)
            uow.commit()
            return variant

    def set_variant_active(
        self, variant_id: int, *, is_active: bool
    ) -> ProductVariant:
        with self._unit_of_work.unit_of_work() as uow:
            variant = SetVariantActive(uow.variants).execute(
                variant_id, is_active=is_active
            )
            uow.commit()
            return variant

    def list_attributes(self) -> tuple[AttributeSummary, ...]:
        with self._unit_of_work.unit_of_work() as uow:
            return ListAttributes(
                uow.attributes,
                uow.attribute_values,
            ).execute()

    def create_attribute(
        self, request: CreateAttributeRequest
    ) -> Attribute:
        with self._unit_of_work.unit_of_work() as uow:
            attribute = CreateAttribute(uow.attributes).execute(request)
            uow.commit()
            return attribute

    def create_attribute_value(
        self, request: CreateAttributeValueRequest
    ) -> AttributeValue:
        with self._unit_of_work.unit_of_work() as uow:
            value = CreateAttributeValue(uow.attribute_values).execute(request)
            uow.commit()
            return value
