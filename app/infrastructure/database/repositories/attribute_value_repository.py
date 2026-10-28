"""SQLAlchemy attribute-value repository."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.attribute import AttributeValue
from app.domain.exceptions import AttributeNotFoundError
from app.infrastructure.database.models import AttributeModel, AttributeValueModel
from app.infrastructure.database.repositories.mapping import (
    attribute_value_to_domain,
)


class SqlAlchemyAttributeValueRepository:
    """Attribute-value persistence using SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, attribute_value: AttributeValue) -> AttributeValue:
        if (
            self._session.get(AttributeModel, attribute_value.attribute_id)
            is None
        ):
            raise AttributeNotFoundError(
                f"Attribute {attribute_value.attribute_id} does not exist."
            )

        model = AttributeValueModel(
            attribute_id=attribute_value.attribute_id,
            value=attribute_value.value,
        )
        self._session.add(model)
        self._session.flush()
        return attribute_value_to_domain(model)

    def get_by_id(self, attribute_value_id: int) -> AttributeValue | None:
        model = self._session.get(AttributeValueModel, attribute_value_id)
        return attribute_value_to_domain(model) if model is not None else None

    def list_for_attribute(self, attribute_id: int) -> list[AttributeValue]:
        statement = (
            select(AttributeValueModel)
            .where(AttributeValueModel.attribute_id == attribute_id)
            .order_by(AttributeValueModel.value)
        )
        return [
            attribute_value_to_domain(model)
            for model in self._session.scalars(statement)
        ]
