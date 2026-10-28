"""SQLAlchemy customer reference repository."""

from sqlalchemy.orm import Session

from app.infrastructure.database.models import CustomerModel


class SqlAlchemyCustomerRepository:
    """Minimal customer lookup used to validate sale references."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def exists(self, customer_id: int) -> bool:
        return self._session.get(CustomerModel, customer_id) is not None
