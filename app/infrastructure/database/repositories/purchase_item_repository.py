"""SQLAlchemy purchase-item repository."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.purchase_item import PurchaseItem
from app.domain.exceptions import (
    PurchaseCurrencyMismatchError,
    PurchaseNotFoundError,
    VariantNotFoundError,
)
from app.infrastructure.database.models import (
    ProductVariantModel,
    PurchaseItemModel,
    PurchaseModel,
)
from app.infrastructure.database.repositories.mapping import (
    purchase_item_to_domain,
)


class SqlAlchemyPurchaseItemRepository:
    """Purchase item persistence using SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, item: PurchaseItem) -> PurchaseItem:
        if item.purchase.id is None:
            raise ValueError(
                "Cannot add an item to a purchase without an id."
            )

        purchase = self._require_purchase(item.purchase.id)
        if item.unit_price.currency.code != purchase.currency.code:
            raise PurchaseCurrencyMismatchError(
                f"Unit price currency {item.unit_price.currency.code} "
                f"does not match purchase currency "
                f"{purchase.currency.code}."
            )
        self._require_variant(item.variant_id)

        model = PurchaseItemModel(
            purchase=purchase,
            variant_id=item.variant_id,
            quantity=item.quantity,
            unit_price=item.unit_price.amount,
            weight=item.weight,
        )
        self._session.add(model)
        self._session.flush()
        return purchase_item_to_domain(model)

    def get_by_id(self, item_id: int) -> PurchaseItem | None:
        model = self._session.get(PurchaseItemModel, item_id)
        return purchase_item_to_domain(model) if model is not None else None

    def list_for_purchase(self, purchase_id: int) -> list[PurchaseItem]:
        statement = (
            select(PurchaseItemModel)
            .where(PurchaseItemModel.purchase_id == purchase_id)
            .order_by(PurchaseItemModel.id.asc())
        )
        return [
            purchase_item_to_domain(model)
            for model in self._session.scalars(statement)
        ]

    def _require_purchase(self, purchase_id: int) -> PurchaseModel:
        model = self._session.get(PurchaseModel, purchase_id)
        if model is None:
            raise PurchaseNotFoundError(
                f"Purchase {purchase_id} does not exist."
            )
        return model

    def _require_variant(self, variant_id: int) -> None:
        if self._session.get(ProductVariantModel, variant_id) is None:
            raise VariantNotFoundError(
                f"Product variant {variant_id} does not exist."
            )
