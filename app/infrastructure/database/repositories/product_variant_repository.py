"""SQLAlchemy product-variant repository."""

from collections.abc import Iterable

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.domain.entities.product_variant import ProductVariant
from app.domain.exceptions import (
    AttributeValueNotFoundError,
    DuplicateSkuError,
    ProductNotFoundError,
    VariantNotFoundError,
)
from app.infrastructure.database.models import (
    AttributeValueModel,
    ProductModel,
    ProductVariantModel,
    VariantAttributeValueModel,
)
from app.infrastructure.database.repositories.mapping import (
    product_variant_to_domain,
)


class SqlAlchemyProductVariantRepository:
    """Product-variant and attribute-assignment persistence."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, variant: ProductVariant) -> ProductVariant:
        self._require_product(variant.product_id)
        self._ensure_sku_available(variant.sku)

        model = ProductVariantModel(
            product_id=variant.product_id,
            sku=variant.sku,
            variant_name=variant.variant_name,
            barcode=variant.barcode,
            is_active=variant.is_active,
        )
        self._session.add(model)
        self._session.flush()
        return product_variant_to_domain(model)

    def save(self, variant: ProductVariant) -> ProductVariant:
        if variant.id is None:
            raise ValueError("Cannot save a variant without an id.")

        model = self._session.get(ProductVariantModel, variant.id)
        if model is None:
            raise VariantNotFoundError(f"Variant {variant.id} does not exist.")
        if model.product_id != variant.product_id:
            raise ValueError("A product variant cannot be moved to another product.")

        self._ensure_sku_available(variant.sku, exclude_variant_id=model.id)

        model.sku = variant.sku
        model.variant_name = variant.variant_name
        model.barcode = variant.barcode
        model.is_active = variant.is_active
        self._session.flush()
        return product_variant_to_domain(model)

    def get_by_id(self, variant_id: int) -> ProductVariant | None:
        model = self._session.get(ProductVariantModel, variant_id)
        return product_variant_to_domain(model) if model is not None else None

    def get_by_sku(self, sku: str) -> ProductVariant | None:
        normalized_sku = sku.strip()
        if not normalized_sku:
            return None

        model = self._session.scalar(
            select(ProductVariantModel).where(
                ProductVariantModel.sku == normalized_sku
            )
        )
        return product_variant_to_domain(model) if model is not None else None

    def list_for_product(
        self, product_id: int, *, include_inactive: bool = False
    ) -> list[ProductVariant]:
        statement = (
            select(ProductVariantModel)
            .where(ProductVariantModel.product_id == product_id)
            .order_by(ProductVariantModel.id)
        )
        if not include_inactive:
            statement = statement.where(
                ProductVariantModel.is_active.is_(True)
            )

        return [
            product_variant_to_domain(model)
            for model in self._session.scalars(statement)
        ]

    def set_attribute_values(
        self, variant_id: int, attribute_value_ids: Iterable[int]
    ) -> None:
        if self._session.get(ProductVariantModel, variant_id) is None:
            raise VariantNotFoundError(f"Variant {variant_id} does not exist.")

        value_ids = sorted(set(attribute_value_ids))
        if any(
            isinstance(value_id, bool)
            or not isinstance(value_id, int)
            or value_id <= 0
            for value_id in value_ids
        ):
            raise ValueError(
                "Attribute value ids must be positive integers."
            )

        if value_ids:
            existing_ids = set(
                self._session.scalars(
                    select(AttributeValueModel.id).where(
                        AttributeValueModel.id.in_(value_ids)
                    )
                )
            )
            missing_ids = [
                value_id for value_id in value_ids if value_id not in existing_ids
            ]
            if missing_ids:
                raise AttributeValueNotFoundError(
                    "Unknown attribute value ids: "
                    + ", ".join(str(value_id) for value_id in missing_ids)
                )

        self._session.execute(
            delete(VariantAttributeValueModel).where(
                VariantAttributeValueModel.variant_id == variant_id
            )
        )
        if value_ids:
            self._session.add_all(
                [
                    VariantAttributeValueModel(
                        variant_id=variant_id,
                        attribute_value_id=value_id,
                    )
                    for value_id in value_ids
                ]
            )
        self._session.flush()

    def get_attribute_value_ids(self, variant_id: int) -> list[int]:
        return list(
            self._session.scalars(
                select(VariantAttributeValueModel.attribute_value_id)
                .where(VariantAttributeValueModel.variant_id == variant_id)
                .order_by(VariantAttributeValueModel.attribute_value_id)
            )
        )

    def _require_product(self, product_id: int) -> None:
        if self._session.get(ProductModel, product_id) is None:
            raise ProductNotFoundError(
                f"Product {product_id} does not exist."
            )

    def _ensure_sku_available(
        self, sku: str | None, *, exclude_variant_id: int | None = None
    ) -> None:
        if sku is None:
            return

        statement = select(ProductVariantModel.id).where(
            ProductVariantModel.sku == sku
        )
        if exclude_variant_id is not None:
            statement = statement.where(
                ProductVariantModel.id != exclude_variant_id
            )
        if self._session.scalar(statement) is not None:
            raise DuplicateSkuError(f"SKU {sku!r} is already in use.")
