"""SQLAlchemy financial-transaction repository."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.account import Account
from app.domain.entities.financial_transaction import FinancialTransaction
from app.domain.exceptions import (
    AccountCurrencyMismatchError,
    AccountNotFoundError,
)
from app.domain.value_objects.money import Money
from app.infrastructure.database.models import (
    AccountModel,
    FinancialTransactionModel,
)
from app.infrastructure.database.repositories.mapping import (
    financial_transaction_to_domain,
)


class SqlAlchemyFinancialTransactionRepository:
    """Append-only persistence for signed ledger entries."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(
        self, transaction: FinancialTransaction
    ) -> FinancialTransaction:
        if transaction.account.id is None:
            raise ValueError(
                "Cannot record a transaction for an account without an id."
            )

        account = self._session.get(AccountModel, transaction.account.id)
        if account is None:
            raise AccountNotFoundError(
                f"Account {transaction.account.id} does not exist."
            )

        if account.currency.code != transaction.amount.currency.code:
            raise AccountCurrencyMismatchError(
                f"Transaction currency "
                f"{transaction.amount.currency.code} does not match "
                f"account currency {account.currency.code}."
            )

        model = FinancialTransactionModel(
            account=account,
            amount=transaction.amount.amount,
            currency=account.currency,
            transaction_type=transaction.transaction_type.value,
            description=transaction.description,
            transaction_date=transaction.transaction_date,
            purchase_id=transaction.purchase_id,
            sale_id=transaction.sale_id,
            expense_id=transaction.expense_id,
            customer_return_id=transaction.customer_return_id,
            supplier_return_id=transaction.supplier_return_id,
            capital_movement_id=transaction.capital_movement_id,
            account_transfer_id=transaction.account_transfer_id,
            exchange_rate_id=transaction.exchange_rate_id,
        )
        self._session.add(model)
        self._session.flush()
        return financial_transaction_to_domain(model)

    def get_by_id(
        self, transaction_id: int
    ) -> FinancialTransaction | None:
        model = self._session.get(FinancialTransactionModel, transaction_id)
        return (
            financial_transaction_to_domain(model)
            if model is not None
            else None
        )

    def list_for_account(
        self,
        account_id: int,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[FinancialTransaction]:
        if start is not None and start.tzinfo is None:
            raise ValueError("Ledger start must be timezone-aware.")
        if end is not None and end.tzinfo is None:
            raise ValueError("Ledger end must be timezone-aware.")
        if start is not None and end is not None and end < start:
            raise ValueError("Ledger end must not be before start.")

        statement = select(FinancialTransactionModel).where(
            FinancialTransactionModel.account_id == account_id
        )
        if start is not None:
            statement = statement.where(
                FinancialTransactionModel.transaction_date >= start
            )
        if end is not None:
            statement = statement.where(
                FinancialTransactionModel.transaction_date <= end
            )
        statement = statement.order_by(
            FinancialTransactionModel.transaction_date.asc(),
            FinancialTransactionModel.id.asc(),
        )

        return [
            financial_transaction_to_domain(model)
            for model in self._session.scalars(statement)
        ]

    def get_balance(self, account: Account) -> Money:
        """Sum signed amounts in Python to keep decimal arithmetic exact."""
        if account.id is None:
            raise ValueError(
                "Cannot calculate a balance for an account without an id."
            )

        statement = select(FinancialTransactionModel.amount).where(
            FinancialTransactionModel.account_id == account.id
        )
        amounts = self._session.scalars(statement)
        total = sum(amounts, Decimal("0"))
        return Money(total, account.currency)
