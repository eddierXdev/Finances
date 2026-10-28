"""SQLAlchemy attribute repository."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.attribute import Attribute
from app.infrastructure.database.models import AttributeModel
from app.infrastructure.database.repositories.mapping import attribute_to_domain


class SqlAlchemyAttributeRepository:
    """Attribute persistence using SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, attribute: Attribute) -> Attribute:
        model = AttributeModel(name=attribute.name)
        self._session.add(model)
        self._session.flush()
        return attribute_to_domain(model)

    def get_by_id(self, attribute_id: int) -> Attribute | None:
        model = self._session.get(AttributeModel, attribute_id)
        return attribute_to_domain(model) if model is not None else None

    def list_all(self) -> list[Attribute]:
        statement = select(AttributeModel).order_by(AttributeModel.name)
        return [
            attribute_to_domain(model)
            for model in self._session.scalars(statement)
        ]
