"""SQLAlchemy supplier repository."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.supplier import Supplier
from app.domain.exceptions import SupplierNotFoundError
from app.infrastructure.database.models import SupplierModel
from app.infrastructure.database.repositories.mapping import supplier_to_domain


class SqlAlchemySupplierRepository:
    """Supplier persistence using SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, supplier: Supplier) -> Supplier:
        model = SupplierModel(
            name=supplier.name,
            supplier_type=supplier.supplier_type,
            website=supplier.website,
            contact=supplier.contact,
            notes=supplier.notes,
            is_active=supplier.is_active,
        )
        self._session.add(model)
        self._session.flush()
        return supplier_to_domain(model)

    def save(self, supplier: Supplier) -> Supplier:
        if supplier.id is None:
            raise ValueError("Cannot save a supplier without an id.")

        model = self._session.get(SupplierModel, supplier.id)
        if model is None:
            raise SupplierNotFoundError(
                f"Supplier {supplier.id} does not exist."
            )

        model.name = supplier.name
        model.supplier_type = supplier.supplier_type
        model.website = supplier.website
        model.contact = supplier.contact
        model.notes = supplier.notes
        model.is_active = supplier.is_active
        self._session.flush()
        return supplier_to_domain(model)

    def get_by_id(self, supplier_id: int) -> Supplier | None:
        model = self._session.get(SupplierModel, supplier_id)
        return supplier_to_domain(model) if model is not None else None

    def list_all(self, *, include_inactive: bool = False) -> list[Supplier]:
        statement = select(SupplierModel).order_by(SupplierModel.name)
        if not include_inactive:
            statement = statement.where(SupplierModel.is_active.is_(True))

        return [
            supplier_to_domain(model)
            for model in self._session.scalars(statement)
        ]
