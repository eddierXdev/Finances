"""SQLAlchemy sale FIFO allocation repository."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.sale_item_lot_allocation import (
    SaleItemLotAllocation,
)
from app.domain.exceptions import (
    InvalidSaleError,
    InventoryLotNotFoundError,
    SaleItemNotFoundError,
)
from app.infrastructure.database.models import (
    InventoryLotModel,
    SaleItemLotAllocationModel,
    SaleItemModel,
)
from app.infrastructure.database.repositories.mapping import (
    sale_item_lot_allocation_to_domain,
)


class SqlAlchemySaleItemLotAllocationRepository:
    """Immutable FIFO allocation persistence using SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(
        self, allocation: SaleItemLotAllocation
    ) -> SaleItemLotAllocation:
        if allocation.sale_item.id is None:
            raise ValueError(
                "Cannot allocate an item without a persisted id."
            )
        if allocation.inventory_lot.id is None:
            raise ValueError(
                "Cannot allocate from a lot without a persisted id."
            )

        item = self._require_sale_item(allocation.sale_item.id)
        lot = self._require_lot(allocation.inventory_lot.id)
        if lot.variant_id != item.variant_id:
            raise InvalidSaleError(
                "Allocation variant must match the sale item variant."
            )
        if (
            allocation.unit_cost_snapshot.amount != lot.unit_cost
            or allocation.unit_cost_snapshot.currency.code
            != lot.currency.code
        ):
            raise InvalidSaleError(
                "Allocation unit_cost_snapshot must match the lot cost."
            )

        model = SaleItemLotAllocationModel(
            sale_item=item,
            inventory_lot=lot,
            quantity=allocation.quantity,
            unit_cost_snapshot=allocation.unit_cost_snapshot.amount,
        )
        self._session.add(model)
        self._session.flush()
        return sale_item_lot_allocation_to_domain(model)

    def get_by_id(
        self, allocation_id: int
    ) -> SaleItemLotAllocation | None:
        model = self._session.get(
            SaleItemLotAllocationModel, allocation_id
        )
        return (
            sale_item_lot_allocation_to_domain(model)
            if model is not None
            else None
        )

    def list_for_sale_item(
        self, sale_item_id: int
    ) -> list[SaleItemLotAllocation]:
        statement = (
            select(SaleItemLotAllocationModel)
            .where(
                SaleItemLotAllocationModel.sale_item_id == sale_item_id
            )
            .order_by(SaleItemLotAllocationModel.id.asc())
        )
        return [
            sale_item_lot_allocation_to_domain(model)
            for model in self._session.scalars(statement)
        ]

    def list_for_sale(
        self, sale_id: int
    ) -> list[SaleItemLotAllocation]:
        statement = (
            select(SaleItemLotAllocationModel)
            .join(
                SaleItemModel,
                SaleItemLotAllocationModel.sale_item_id
                == SaleItemModel.id,
            )
            .where(SaleItemModel.sale_id == sale_id)
            .order_by(SaleItemLotAllocationModel.id.asc())
        )
        return [
            sale_item_lot_allocation_to_domain(model)
            for model in self._session.scalars(statement)
        ]

    def list_for_lot(
        self, lot_id: int
    ) -> list[SaleItemLotAllocation]:
        statement = (
            select(SaleItemLotAllocationModel)
            .where(
                SaleItemLotAllocationModel.inventory_lot_id == lot_id
            )
            .order_by(SaleItemLotAllocationModel.id.asc())
        )
        return [
            sale_item_lot_allocation_to_domain(model)
            for model in self._session.scalars(statement)
        ]

    def _require_sale_item(self, item_id: int) -> SaleItemModel:
        model = self._session.get(SaleItemModel, item_id)
        if model is None:
            raise SaleItemNotFoundError(
                f"Sale item {item_id} does not exist."
            )
        return model

    def _require_lot(self, lot_id: int) -> InventoryLotModel:
        model = self._session.get(InventoryLotModel, lot_id)
        if model is None:
            raise InventoryLotNotFoundError(
                f"Inventory lot {lot_id} does not exist."
            )
        return model
