"""Product application use cases."""

from app.application.products.catalog import ProductCatalogService
from app.application.products.categories import (
    CreateCategory,
    CreateCategoryRequest,
)
from app.application.products.create_product import (
    CreateProduct,
    CreateProductRequest,
    ProductVariantRequest,
)
from app.application.products.list_products import ListProducts, ProductListItem
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

__all__ = [
    "CreateCategory",
    "CreateCategoryRequest",
    "CreateProduct",
    "CreateProductRequest",
    "CreateVariant",
    "CreateVariantRequest",
    "ListProductVariants",
    "ListProducts",
    "ProductCatalogService",
    "ProductListItem",
    "ProductVariantRequest",
    "SetProductActive",
    "SetVariantActive",
    "UpdateProduct",
    "UpdateProductRequest",
    "UpdateVariant",
    "UpdateVariantRequest",
    "VariantListItem",
]
