"""SQLAlchemy inventory-lot repository."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.entities.inventory_lot import InventoryLot
from app.domain.exceptions import (
    CurrencyNotFoundError,
    InventoryLotNotFoundError,
    InvalidInventoryError,
    PurchaseCurrencyMismatchError,
    PurchaseItemNotFoundError,
    VariantNotFoundError,
)
from app.infrastructure.database.models import (
    CurrencyModel,
    InventoryLotModel,
    ProductVariantModel,
    PurchaseItemModel,
)
from app.infrastructure.database.repositories.mapping import (
    inventory_lot_to_domain,
)


class SqlAlchemyInventoryLotRepository:
    """Inventory lot persistence using SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, lot: InventoryLot) -> InventoryLot:
        if lot.purchase_item.id is None:
            raise ValueError(
                "Cannot persist a lot without a persisted purchase item."
            )

        item = self._require_item(lot.purchase_item.id)
        if lot.variant_id != item.variant_id:
            raise InvalidInventoryError(
                "Inventory lot variant must match its purchase item variant."
            )
        self._require_variant(lot.variant_id)

        currency = self._require_currency(lot.unit_cost.currency.code)
        if currency.code != item.purchase.currency.code:
            raise PurchaseCurrencyMismatchError(
                f"Lot currency {currency.code} does not match purchase "
                f"currency {item.purchase.currency.code}."
            )

        model = InventoryLotModel(
            purchase_item=item,
            variant_id=lot.variant_id,
            acquired_quantity=lot.acquired_quantity,
            remaining_quantity=lot.remaining_quantity,
            unit_cost=lot.unit_cost.amount,
            currency=currency,
            received_at=lot.received_at,
        )
        self._session.add(model)
        self._session.flush()
        return inventory_lot_to_domain(model)

    def save(self, lot: InventoryLot) -> InventoryLot:
        if lot.id is None:
            raise ValueError("Cannot save a lot without an id.")

        model = self._session.get(InventoryLotModel, lot.id)
        if model is None:
            raise InventoryLotNotFoundError(
                f"Inventory lot {lot.id} does not exist."
            )

        if (
            model.purchase_item_id != lot.purchase_item_id
            or model.variant_id != lot.variant_id
            or model.acquired_quantity != lot.acquired_quantity
            or model.unit_cost != lot.unit_cost.amount
            or model.currency.code != lot.unit_cost.currency.code
            or model.received_at != lot.received_at
        ):
            raise ValueError(
                "A lot's acquisition data cannot change after creation."
            )

        model.remaining_quantity = lot.remaining_quantity
        self._session.flush()
        return inventory_lot_to_domain(model)

    def get_by_id(self, lot_id: int) -> InventoryLot | None:
        model = self._session.get(InventoryLotModel, lot_id)
        return inventory_lot_to_domain(model) if model is not None else None

    def list_by_variant(self, variant_id: int) -> list[InventoryLot]:
        statement = (
            select(InventoryLotModel)
            .where(InventoryLotModel.variant_id == variant_id)
            .order_by(
                InventoryLotModel.received_at.asc(),
                InventoryLotModel.id.asc(),
            )
        )
        return [
            inventory_lot_to_domain(model)
            for model in self._session.scalars(statement)
        ]

    def list_available_by_variant(
        self, variant_id: int
    ) -> list[InventoryLot]:
        statement = (
            select(InventoryLotModel)
            .where(
                InventoryLotModel.variant_id == variant_id,
                InventoryLotModel.remaining_quantity > 0,
            )
            .order_by(
                InventoryLotModel.received_at.asc(),
                InventoryLotModel.id.asc(),
            )
        )
        return [
            inventory_lot_to_domain(model)
            for model in self._session.scalars(statement)
        ]

    def list_for_purchase_item(
        self, purchase_item_id: int
    ) -> list[InventoryLot]:
        statement = (
            select(InventoryLotModel)
            .where(InventoryLotModel.purchase_item_id == purchase_item_id)
            .order_by(
                InventoryLotModel.received_at.asc(),
                InventoryLotModel.id.asc(),
            )
        )
        return [
            inventory_lot_to_domain(model)
            for model in self._session.scalars(statement)
        ]

    def list_for_purchase(self, purchase_id: int) -> list[InventoryLot]:
        statement = (
            select(InventoryLotModel)
            .join(
                PurchaseItemModel,
                InventoryLotModel.purchase_item_id
                == PurchaseItemModel.id,
            )
            .where(PurchaseItemModel.purchase_id == purchase_id)
            .order_by(
                InventoryLotModel.received_at.asc(),
                InventoryLotModel.id.asc(),
            )
        )
        return [
            inventory_lot_to_domain(model)
            for model in self._session.scalars(statement)
        ]

    def total_remaining_by_variant(self, variant_id: int) -> int:
        total = self._session.scalar(
            select(
                func.coalesce(
                    func.sum(InventoryLotModel.remaining_quantity), 0
                )
            ).where(InventoryLotModel.variant_id == variant_id)
        )
        return int(total)

    def _require_item(self, item_id: int) -> PurchaseItemModel:
        model = self._session.get(PurchaseItemModel, item_id)
        if model is None:
            raise PurchaseItemNotFoundError(
                f"Purchase item {item_id} does not exist."
            )
        return model

    def _require_variant(self, variant_id: int) -> None:
        if self._session.get(ProductVariantModel, variant_id) is None:
            raise VariantNotFoundError(
                f"Product variant {variant_id} does not exist."
            )

    def _require_currency(self, code: str) -> CurrencyModel:
        normalized_code = code.strip().upper()
        model = self._session.scalar(
            select(CurrencyModel).where(
                CurrencyModel.code == normalized_code
            )
        )
        if model is None:
            raise CurrencyNotFoundError(
                f"Currency {normalized_code} is not registered."
            )
        return model
