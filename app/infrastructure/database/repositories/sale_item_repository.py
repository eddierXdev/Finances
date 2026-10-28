"""SQLAlchemy sale-item repository."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.sale_item import SaleItem
from app.domain.exceptions import (
    SaleCurrencyMismatchError,
    SaleNotFoundError,
    VariantNotFoundError,
)
from app.infrastructure.database.models import (
    ProductVariantModel,
    SaleItemModel,
    SaleModel,
)
from app.infrastructure.database.repositories.mapping import (
    sale_item_to_domain,
)


class SqlAlchemySaleItemRepository:
    """Sale item persistence using SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, item: SaleItem) -> SaleItem:
        if item.sale.id is None:
            raise ValueError("Cannot add an item to a sale without an id.")

        sale = self._require_sale(item.sale.id)
        if item.unit_price.currency.code != sale.currency.code:
            raise SaleCurrencyMismatchError(
                f"Unit price currency {item.unit_price.currency.code} does "
                f"not match sale currency {sale.currency.code}."
            )
        self._require_variant(item.variant_id)

        model = SaleItemModel(
            sale=sale,
            variant_id=item.variant_id,
            quantity=item.quantity,
            unit_price=item.unit_price.amount,
            discount_amount=(
                item.discount_amount.amount
                if item.discount_amount is not None
                else None
            ),
        )
        self._session.add(model)
        self._session.flush()
        return sale_item_to_domain(model)

    def get_by_id(self, item_id: int) -> SaleItem | None:
        model = self._session.get(SaleItemModel, item_id)
        return sale_item_to_domain(model) if model is not None else None

    def list_for_sale(self, sale_id: int) -> list[SaleItem]:
        statement = (
            select(SaleItemModel)
            .where(SaleItemModel.sale_id == sale_id)
            .order_by(SaleItemModel.id.asc())
        )
        return [
            sale_item_to_domain(model)
            for model in self._session.scalars(statement)
        ]

    def _require_sale(self, sale_id: int) -> SaleModel:
        model = self._session.get(SaleModel, sale_id)
        if model is None:
            raise SaleNotFoundError(f"Sale {sale_id} does not exist.")
        return model

    def _require_variant(self, variant_id: int) -> None:
        if self._session.get(ProductVariantModel, variant_id) is None:
            raise VariantNotFoundError(
                f"Product variant {variant_id} does not exist."
            )
