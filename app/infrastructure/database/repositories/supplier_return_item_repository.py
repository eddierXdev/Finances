"""SQLAlchemy supplier return item repository."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.supplier_return_item import SupplierReturnItem
from app.domain.exceptions import (
    InvalidSupplierReturnError,
    InvalidSupplierReturnLotError,
    InventoryLotNotFoundError,
    PurchaseItemNotFoundError,
    SupplierReturnNotFoundError,
)
from app.infrastructure.database.models import (
    InventoryLotModel,
    PurchaseItemModel,
    SupplierReturnItemModel,
    SupplierReturnModel,
)
from app.infrastructure.database.repositories.mapping import (
    supplier_return_item_to_domain,
)


class SqlAlchemySupplierReturnItemRepository:
    """Supplier return line persistence using SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, item: SupplierReturnItem) -> SupplierReturnItem:
        if item.supplier_return.id is None:
            raise ValueError(
                "Cannot add a line to a supplier return without an id."
            )
        if item.purchase_item.id is None:
            raise ValueError(
                "Cannot add a line without a persisted purchase item."
            )
        if item.inventory_lot.id is None:
            raise ValueError(
                "Cannot add a line without a persisted inventory lot."
            )

        supplier_return = self._require_return(
            item.supplier_return.id
        )
        purchase_item = self._require_purchase_item(
            item.purchase_item.id
        )
        lot = self._require_lot(item.inventory_lot.id)

        if purchase_item.purchase_id != supplier_return.purchase_id:
            raise InvalidSupplierReturnError(
                "A returned item must belong to the original purchase."
            )
        if lot.purchase_item_id != purchase_item.id:
            raise InvalidSupplierReturnLotError(
                "A supplier return lot must belong to the original "
                "purchase item."
            )
        if (
            item.unit_cost_snapshot.amount != lot.unit_cost
            or item.unit_cost_snapshot.currency.code
            != lot.currency.code
        ):
            raise InvalidSupplierReturnError(
                "A supplier return must preserve the lot's historical unit "
                "cost."
            )

        model = SupplierReturnItemModel(
            supplier_return=supplier_return,
            purchase_item=purchase_item,
            inventory_lot=lot,
            quantity=item.quantity,
            unit_cost_snapshot=item.unit_cost_snapshot.amount,
        )
        self._session.add(model)
        self._session.flush()
        return supplier_return_item_to_domain(model)

    def get_by_id(self, item_id: int) -> SupplierReturnItem | None:
        model = self._session.get(SupplierReturnItemModel, item_id)
        return (
            supplier_return_item_to_domain(model)
            if model is not None
            else None
        )

    def list_for_return(
        self, return_id: int
    ) -> list[SupplierReturnItem]:
        statement = (
            select(SupplierReturnItemModel)
            .where(
                SupplierReturnItemModel.supplier_return_id == return_id
            )
            .order_by(SupplierReturnItemModel.id.asc())
        )
        return [
            supplier_return_item_to_domain(model)
            for model in self._session.scalars(statement)
        ]

    def list_for_purchase(
        self, purchase_id: int
    ) -> list[SupplierReturnItem]:
        statement = (
            select(SupplierReturnItemModel)
            .join(
                SupplierReturnModel,
                SupplierReturnItemModel.supplier_return_id
                == SupplierReturnModel.id,
            )
            .where(SupplierReturnModel.purchase_id == purchase_id)
            .order_by(SupplierReturnItemModel.id.asc())
        )
        return [
            supplier_return_item_to_domain(model)
            for model in self._session.scalars(statement)
        ]

    def _require_return(
        self, return_id: int
    ) -> SupplierReturnModel:
        model = self._session.get(SupplierReturnModel, return_id)
        if model is None:
            raise SupplierReturnNotFoundError(
                f"Supplier return {return_id} does not exist."
            )
        return model

    def _require_purchase_item(
        self, item_id: int
    ) -> PurchaseItemModel:
        model = self._session.get(PurchaseItemModel, item_id)
        if model is None:
            raise PurchaseItemNotFoundError(
                f"Purchase item {item_id} does not exist."
            )
        return model

    def _require_lot(self, lot_id: int) -> InventoryLotModel:
        model = self._session.get(InventoryLotModel, lot_id)
        if model is None:
            raise InventoryLotNotFoundError(
                f"Inventory lot {lot_id} does not exist."
            )
        return model
