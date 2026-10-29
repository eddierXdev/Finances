"""SQLAlchemy unit-of-work implementation."""

from __future__ import annotations

from types import TracebackType

from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.database.repositories import (
    SqlAlchemyAccountRepository,
    SqlAlchemyAccountTransferRepository,
    SqlAlchemyAnalyticsRepository,
    SqlAlchemyAttributeRepository,
    SqlAlchemyAttributeValueRepository,
    SqlAlchemyCapitalMovementRepository,
    SqlAlchemyCategoryRepository,
    SqlAlchemyCurrencyRepository,
    SqlAlchemyCustomerRepository,
    SqlAlchemyCustomerReturnItemRepository,
    SqlAlchemyCustomerReturnRepository,
    SqlAlchemyExchangeRateRepository,
    SqlAlchemyExpenseRepository,
    SqlAlchemyFinancialTransactionRepository,
    SqlAlchemyInventoryLotRepository,
    SqlAlchemyInventoryMovementRepository,
    SqlAlchemyProductRepository,
    SqlAlchemyProductVariantRepository,
    SqlAlchemyPurchaseCostAllocationRepository,
    SqlAlchemyPurchaseCostRepository,
    SqlAlchemyPurchaseItemRepository,
    SqlAlchemyPurchaseRepository,
    SqlAlchemyReturnLotAllocationRepository,
    SqlAlchemySaleItemLotAllocationRepository,
    SqlAlchemySaleItemRepository,
    SqlAlchemySaleRepository,
    SqlAlchemySettingsRepository,
    SqlAlchemySupplierRepository,
    SqlAlchemySupplierReturnItemRepository,
    SqlAlchemySupplierReturnRepository,
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
        self.inventory_lots = SqlAlchemyInventoryLotRepository(session)
        self.inventory_movements = SqlAlchemyInventoryMovementRepository(session)
        self.customers = SqlAlchemyCustomerRepository(session)
        self.sales = SqlAlchemySaleRepository(session)
        self.sale_items = SqlAlchemySaleItemRepository(session)
        self.sale_allocations = SqlAlchemySaleItemLotAllocationRepository(
            session
        )
        self.customer_returns = SqlAlchemyCustomerReturnRepository(session)
        self.customer_return_items = (
            SqlAlchemyCustomerReturnItemRepository(session)
        )
        self.return_allocations = SqlAlchemyReturnLotAllocationRepository(
            session
        )
        self.supplier_returns = SqlAlchemySupplierReturnRepository(session)
        self.supplier_return_items = (
            SqlAlchemySupplierReturnItemRepository(session)
        )
        self.expenses = SqlAlchemyExpenseRepository(session)
        self.capital_movements = SqlAlchemyCapitalMovementRepository(session)
        self.transfers = SqlAlchemyAccountTransferRepository(session)
        self.analytics = SqlAlchemyAnalyticsRepository(session)
        self.settings = SqlAlchemySettingsRepository(session)

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
