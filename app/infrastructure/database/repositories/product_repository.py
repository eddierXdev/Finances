"""SQLAlchemy product repository."""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.product import Product
from app.domain.exceptions import (
    CategoryNotFoundError,
    CurrencyNotFoundError,
    ProductNotFoundError,
)
from app.domain.value_objects.money import Money
from app.infrastructure.database.models import (
    CategoryModel,
    CurrencyModel,
    ProductModel,
)
from app.infrastructure.database.repositories.mapping import product_to_domain


class SqlAlchemyProductRepository:
    """Product persistence using SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, product: Product) -> Product:
        self._require_category(product.category_id)
        currency = self._resolve_selling_currency(product.default_selling_price)

        model = ProductModel(
            name=product.name,
            category_id=product.category_id,
            description=product.description,
            brand=product.brand,
            default_selling_price=self._price_amount(product.default_selling_price),
            selling_currency=currency,
            is_active=product.is_active,
        )
        self._session.add(model)
        self._session.flush()
        return product_to_domain(model)

    def save(self, product: Product) -> Product:
        if product.id is None:
            raise ValueError("Cannot save a product without an id.")

        model = self._session.get(ProductModel, product.id)
        if model is None:
            raise ProductNotFoundError(f"Product {product.id} does not exist.")

        self._require_category(product.category_id)
        currency = self._resolve_selling_currency(product.default_selling_price)

        model.name = product.name
        model.category_id = product.category_id
        model.description = product.description
        model.brand = product.brand
        model.default_selling_price = self._price_amount(
            product.default_selling_price
        )
        model.selling_currency = currency
        model.is_active = product.is_active
        self._session.flush()
        return product_to_domain(model)

    def get_by_id(self, product_id: int) -> Product | None:
        model = self._session.get(ProductModel, product_id)
        return product_to_domain(model) if model is not None else None

    def list_all(self, *, include_inactive: bool = False) -> list[Product]:
        statement = select(ProductModel).order_by(ProductModel.name)
        if not include_inactive:
            statement = statement.where(ProductModel.is_active.is_(True))

        return [
            product_to_domain(model)
            for model in self._session.scalars(statement)
        ]

    def _require_category(self, category_id: int | None) -> None:
        if category_id is None:
            return
        if self._session.get(CategoryModel, category_id) is None:
            raise CategoryNotFoundError(
                f"Category {category_id} does not exist."
            )

    def _resolve_selling_currency(
        self, price: Money | None
    ) -> CurrencyModel | None:
        if price is None:
            return None
        model = self._session.scalar(
            select(CurrencyModel).where(
                CurrencyModel.code == price.currency.code
            )
        )
        if model is None:
            raise CurrencyNotFoundError(
                f"Currency {price.currency.code} is not registered."
            )
        return model

    @staticmethod
    def _price_amount(price: Money | None) -> Decimal | None:
        return price.amount if price is not None else None
