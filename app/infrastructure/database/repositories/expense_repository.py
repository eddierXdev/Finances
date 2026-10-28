"""SQLAlchemy expense repository."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.expense import Expense
from app.domain.exceptions import AccountNotFoundError
from app.infrastructure.database.models import AccountModel, ExpenseModel
from app.infrastructure.database.repositories.mapping import expense_to_domain


class SqlAlchemyExpenseRepository:
    """Expense persistence using SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, expense: Expense) -> Expense:
        if expense.account.id is None:
            raise ValueError(
                "Cannot record an expense for an account without an id."
            )

        account = self._session.get(AccountModel, expense.account.id)
        if account is None:
            raise AccountNotFoundError(
                f"Account {expense.account.id} does not exist."
            )

        model = ExpenseModel(
            account=account,
            expense_type=expense.expense_type.value,
            amount=expense.amount.amount,
            currency=account.currency,
            expense_date=expense.expense_date,
            description=expense.description,
            notes=expense.notes,
        )
        self._session.add(model)
        self._session.flush()
        return expense_to_domain(model)

    def get_by_id(self, expense_id: int) -> Expense | None:
        model = self._session.get(ExpenseModel, expense_id)
        return expense_to_domain(model) if model is not None else None

    def list_all(self) -> list[Expense]:
        statement = select(ExpenseModel).order_by(
            ExpenseModel.expense_date.desc(),
            ExpenseModel.id.desc(),
        )
        return [
            expense_to_domain(model)
            for model in self._session.scalars(statement)
        ]

    def list_for_account(self, account_id: int) -> list[Expense]:
        statement = (
            select(ExpenseModel)
            .where(ExpenseModel.account_id == account_id)
            .order_by(
                ExpenseModel.expense_date.asc(),
                ExpenseModel.id.asc(),
            )
        )
        return [
            expense_to_domain(model)
            for model in self._session.scalars(statement)
        ]
