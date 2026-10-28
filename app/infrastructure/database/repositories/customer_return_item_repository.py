"""SQLAlchemy customer return item repository."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.customer_return_item import CustomerReturnItem
from app.domain.exceptions import (
    CustomerReturnNotFoundError,
    InvalidCustomerReturnError,
    SaleItemNotFoundError,
)
from app.infrastructure.database.models import (
    CustomerReturnItemModel,
    CustomerReturnModel,
    SaleItemModel,
)
from app.infrastructure.database.repositories.mapping import (
    customer_return_item_to_domain,
)


class SqlAlchemyCustomerReturnItemRepository:
    """Customer return line persistence using SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, item: CustomerReturnItem) -> CustomerReturnItem:
        if item.customer_return.id is None:
            raise ValueError(
                "Cannot add a line to a return without an id."
            )
        if item.sale_item.id is None:
            raise ValueError(
                "Cannot add a line without a persisted sale item."
            )

        customer_return = self._require_return(
            item.customer_return.id
        )
        sale_item = self._require_sale_item(item.sale_item.id)
        if sale_item.sale_id != customer_return.sale_id:
            raise InvalidCustomerReturnError(
                "A returned item must belong to the original sale."
            )

        model = CustomerReturnItemModel(
            customer_return=customer_return,
            sale_item=sale_item,
            quantity=item.quantity,
            condition=item.condition.value,
        )
        self._session.add(model)
        self._session.flush()
        return customer_return_item_to_domain(model)

    def get_by_id(self, item_id: int) -> CustomerReturnItem | None:
        model = self._session.get(CustomerReturnItemModel, item_id)
        return (
            customer_return_item_to_domain(model)
            if model is not None
            else None
        )

    def list_for_return(
        self, return_id: int
    ) -> list[CustomerReturnItem]:
        statement = (
            select(CustomerReturnItemModel)
            .where(
                CustomerReturnItemModel.customer_return_id == return_id
            )
            .order_by(CustomerReturnItemModel.id.asc())
        )
        return [
            customer_return_item_to_domain(model)
            for model in self._session.scalars(statement)
        ]

    def list_for_sale(self, sale_id: int) -> list[CustomerReturnItem]:
        statement = (
            select(CustomerReturnItemModel)
            .join(
                CustomerReturnModel,
                CustomerReturnItemModel.customer_return_id
                == CustomerReturnModel.id,
            )
            .where(CustomerReturnModel.sale_id == sale_id)
            .order_by(CustomerReturnItemModel.id.asc())
        )
        return [
            customer_return_item_to_domain(model)
            for model in self._session.scalars(statement)
        ]

    def _require_return(self, return_id: int) -> CustomerReturnModel:
        model = self._session.get(CustomerReturnModel, return_id)
        if model is None:
            raise CustomerReturnNotFoundError(
                f"Customer return {return_id} does not exist."
            )
        return model

    def _require_sale_item(self, item_id: int) -> SaleItemModel:
        model = self._session.get(SaleItemModel, item_id)
        if model is None:
            raise SaleItemNotFoundError(
                f"Sale item {item_id} does not exist."
            )
        return model
