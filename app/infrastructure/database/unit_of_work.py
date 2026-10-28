"""SQLAlchemy unit-of-work implementation."""

from __future__ import annotations

from types import TracebackType

from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.database.repositories import (
    SqlAlchemyAccountRepository,
    SqlAlchemyAttributeRepository,
    SqlAlchemyAttributeValueRepository,
    SqlAlchemyCategoryRepository,
    SqlAlchemyCurrencyRepository,
    SqlAlchemyExchangeRateRepository,
    SqlAlchemyFinancialTransactionRepository,
    SqlAlchemyProductRepository,
    SqlAlchemyProductVariantRepository,
    SqlAlchemyPurchaseCostAllocationRepository,
    SqlAlchemyPurchaseCostRepository,
    SqlAlchemyPurchaseItemRepository,
    SqlAlchemyPurchaseRepository,
    SqlAlchemySupplierRepository,
)


class SqlAlchemyUnitOfWork:
    """One session with catalog and finance repositories.

    ``commit`` is explicit so read-only queries do not create write
    transactions. Exiting without a commit rolls back uncommitted work.
    """

    def __init__(self, session: Session) -> None:
        self._session = session
        self.products = SqlAlchemyProductRepository(session)
        self.variants = SqlAlchemyProductVariantRepository(session)
        self.categories = SqlAlchemyCategoryRepository(session)
        self.currencies = SqlAlchemyCurrencyRepository(session)
        self.attributes = SqlAlchemyAttributeRepository(session)
        self.attribute_values = SqlAlchemyAttributeValueRepository(session)
        self.accounts = SqlAlchemyAccountRepository(session)
        self.transactions = SqlAlchemyFinancialTransactionRepository(session)
        self.suppliers = SqlAlchemySupplierRepository(session)
        self.purchases = SqlAlchemyPurchaseRepository(session)
        self.purchase_items = SqlAlchemyPurchaseItemRepository(session)
        self.purchase_costs = SqlAlchemyPurchaseCostRepository(session)
        self.purchase_allocations = (
            SqlAlchemyPurchaseCostAllocationRepository(session)
        )
        self.exchange_rates = SqlAlchemyExchangeRateRepository(session)

    def __enter__(self) -> SqlAlchemyUnitOfWork:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        if exc_type is not None:
            self._session.rollback()
        self._session.close()
        return False

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()


class SqlAlchemyUnitOfWorkFactory:
    """Create one unit of work per business operation."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def unit_of_work(self) -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(self._session_factory())
