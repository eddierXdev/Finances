"""SQLAlchemy purchase-cost allocation repository."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.purchase_cost_allocation import (
    PurchaseCostAllocation,
)
from app.domain.exceptions import (
    InvalidCostAllocationError,
    PurchaseCostNotFoundError,
    PurchaseItemNotFoundError,
)
from app.infrastructure.database.models import (
    PurchaseCostAllocationModel,
    PurchaseCostModel,
    PurchaseItemModel,
)
from app.infrastructure.database.repositories.mapping import (
    purchase_cost_allocation_to_domain,
)


class SqlAlchemyPurchaseCostAllocationRepository:
    """Normalized purchase-cost allocation persistence using SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(
        self, allocation: PurchaseCostAllocation
    ) -> PurchaseCostAllocation:
        if (
            allocation.purchase_cost.id is None
            or allocation.purchase_item.id is None
        ):
            raise ValueError(
                "Cannot persist an allocation without persisted cost and "
                "item."
            )

        cost = self._require_cost(allocation.purchase_cost.id)
        item = self._require_item(allocation.purchase_item.id)
        if cost.purchase_id != item.purchase_id:
            raise InvalidCostAllocationError(
                "Cost and item must belong to the same purchase."
            )

        existing = self._session.scalar(
            select(PurchaseCostAllocationModel.id).where(
                PurchaseCostAllocationModel.purchase_cost_id == cost.id,
                PurchaseCostAllocationModel.purchase_item_id == item.id,
            )
        )
        if existing is not None:
            raise InvalidCostAllocationError(
                "This cost has already been allocated to this item."
            )

        model = PurchaseCostAllocationModel(
            purchase_cost=cost,
            purchase_item=item,
            allocated_original_amount=(
                allocation.allocated_original_amount.amount
            ),
            allocated_purchase_currency_amount=(
                allocation.allocated_purchase_currency_amount.amount
            ),
        )
        self._session.add(model)
        self._session.flush()
        return purchase_cost_allocation_to_domain(model)

    def list_for_cost(
        self, cost_id: int
    ) -> list[PurchaseCostAllocation]:
        statement = (
            select(PurchaseCostAllocationModel)
            .where(PurchaseCostAllocationModel.purchase_cost_id == cost_id)
            .order_by(PurchaseCostAllocationModel.id.asc())
        )
        return [
            purchase_cost_allocation_to_domain(model)
            for model in self._session.scalars(statement)
        ]

    def list_for_item(
        self, item_id: int
    ) -> list[PurchaseCostAllocation]:
        statement = (
            select(PurchaseCostAllocationModel)
            .where(PurchaseCostAllocationModel.purchase_item_id == item_id)
            .order_by(PurchaseCostAllocationModel.id.asc())
        )
        return [
            purchase_cost_allocation_to_domain(model)
            for model in self._session.scalars(statement)
        ]

    def list_for_purchase(
        self, purchase_id: int
    ) -> list[PurchaseCostAllocation]:
        statement = (
            select(PurchaseCostAllocationModel)
            .join(
                PurchaseCostModel,
                PurchaseCostAllocationModel.purchase_cost_id
                == PurchaseCostModel.id,
            )
            .where(PurchaseCostModel.purchase_id == purchase_id)
            .order_by(PurchaseCostAllocationModel.id.asc())
        )
        return [
            purchase_cost_allocation_to_domain(model)
            for model in self._session.scalars(statement)
        ]

    def _require_cost(self, cost_id: int) -> PurchaseCostModel:
        model = self._session.get(PurchaseCostModel, cost_id)
        if model is None:
            raise PurchaseCostNotFoundError(
                f"Purchase cost {cost_id} does not exist."
            )
        return model

    def _require_item(self, item_id: int) -> PurchaseItemModel:
        model = self._session.get(PurchaseItemModel, item_id)
        if model is None:
            raise PurchaseItemNotFoundError(
                f"Purchase item {item_id} does not exist."
            )
        return model
