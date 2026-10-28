"""SQLAlchemy return lot allocation repository."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.return_lot_allocation import ReturnLotAllocation
from app.domain.exceptions import (
    CustomerReturnItemNotFoundError,
    InvalidCustomerReturnError,
    SaleItemLotAllocationNotFoundError,
)
from app.infrastructure.database.models import (
    CustomerReturnItemModel,
    CustomerReturnModel,
    ReturnLotAllocationModel,
    SaleItemLotAllocationModel,
)
from app.infrastructure.database.repositories.mapping import (
    return_lot_allocation_to_domain,
)


class SqlAlchemyReturnLotAllocationRepository:
    """Immutable return allocation persistence using SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(
        self, allocation: ReturnLotAllocation
    ) -> ReturnLotAllocation:
        if allocation.customer_return_item.id is None:
            raise ValueError(
                "Cannot allocate a return line without a persisted id."
            )
        if allocation.sale_item_lot_allocation.id is None:
            raise ValueError(
                "Cannot reverse an allocation without a persisted id."
            )

        return_item = self._require_return_item(
            allocation.customer_return_item.id
        )
        original = self._require_original(
            allocation.sale_item_lot_allocation.id
        )
        if original.sale_item_id != return_item.sale_item_id:
            raise InvalidCustomerReturnError(
                "A return allocation must match the original sale item."
            )
        if (
            allocation.unit_cost_snapshot.amount
            != original.unit_cost_snapshot
            or allocation.unit_cost_snapshot.currency.code
            != original.inventory_lot.currency.code
        ):
            raise InvalidCustomerReturnError(
                "A return allocation must preserve the original historical "
                "unit cost."
            )

        model = ReturnLotAllocationModel(
            customer_return_item=return_item,
            sale_item_lot_allocation=original,
            quantity=allocation.quantity,
            unit_cost_snapshot=allocation.unit_cost_snapshot.amount,
        )
        self._session.add(model)
        self._session.flush()
        return return_lot_allocation_to_domain(model)

    def get_by_id(
        self, allocation_id: int
    ) -> ReturnLotAllocation | None:
        model = self._session.get(
            ReturnLotAllocationModel, allocation_id
        )
        return (
            return_lot_allocation_to_domain(model)
            if model is not None
            else None
        )

    def list_for_return_item(
        self, item_id: int
    ) -> list[ReturnLotAllocation]:
        statement = (
            select(ReturnLotAllocationModel)
            .where(
                ReturnLotAllocationModel.customer_return_item_id == item_id
            )
            .order_by(ReturnLotAllocationModel.id.asc())
        )
        return [
            return_lot_allocation_to_domain(model)
            for model in self._session.scalars(statement)
        ]

    def list_for_sale(self, sale_id: int) -> list[ReturnLotAllocation]:
        statement = (
            select(ReturnLotAllocationModel)
            .join(
                CustomerReturnItemModel,
                ReturnLotAllocationModel.customer_return_item_id
                == CustomerReturnItemModel.id,
            )
            .join(
                CustomerReturnModel,
                CustomerReturnItemModel.customer_return_id
                == CustomerReturnModel.id,
            )
            .where(CustomerReturnModel.sale_id == sale_id)
            .order_by(ReturnLotAllocationModel.id.asc())
        )
        return [
            return_lot_allocation_to_domain(model)
            for model in self._session.scalars(statement)
        ]

    def list_for_sale_item_lot_allocation(
        self, sale_allocation_id: int
    ) -> list[ReturnLotAllocation]:
        statement = (
            select(ReturnLotAllocationModel)
            .where(
                ReturnLotAllocationModel.sale_item_lot_allocation_id
                == sale_allocation_id
            )
            .order_by(ReturnLotAllocationModel.id.asc())
        )
        return [
            return_lot_allocation_to_domain(model)
            for model in self._session.scalars(statement)
        ]

    def _require_return_item(
        self, item_id: int
    ) -> CustomerReturnItemModel:
        model = self._session.get(CustomerReturnItemModel, item_id)
        if model is None:
            raise CustomerReturnItemNotFoundError(
                f"Customer return item {item_id} does not exist."
            )
        return model

    def _require_original(
        self, allocation_id: int
    ) -> SaleItemLotAllocationModel:
        model = self._session.get(
            SaleItemLotAllocationModel, allocation_id
        )
        if model is None:
            raise SaleItemLotAllocationNotFoundError(
                f"Sale item lot allocation {allocation_id} does not exist."
            )
        return model
