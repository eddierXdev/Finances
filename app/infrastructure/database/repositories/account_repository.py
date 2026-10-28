"""SQLAlchemy account repository."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.account import Account
from app.domain.exceptions import AccountNotFoundError, CurrencyNotFoundError
from app.infrastructure.database.models import AccountModel, CurrencyModel
from app.infrastructure.database.repositories.mapping import account_to_domain


class SqlAlchemyAccountRepository:
    """Account persistence using SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, account: Account) -> Account:
        currency = self._require_currency(account.currency.code)

        model = AccountModel(
            name=account.name,
            currency=currency,
            account_type=account.account_type,
            is_active=account.is_active,
            notes=account.notes,
        )
        self._session.add(model)
        self._session.flush()
        return account_to_domain(model)

    def save(self, account: Account) -> Account:
        if account.id is None:
            raise ValueError("Cannot save an account without an id.")

        model = self._session.get(AccountModel, account.id)
        if model is None:
            raise AccountNotFoundError(
                f"Account {account.id} does not exist."
            )

        if model.currency.code != account.currency.code:
            raise ValueError(
                "An account's native currency cannot be changed after "
                "creation."
            )

        model.name = account.name
        model.account_type = account.account_type
        model.is_active = account.is_active
        model.notes = account.notes
        self._session.flush()
        return account_to_domain(model)

    def get_by_id(self, account_id: int) -> Account | None:
        model = self._session.get(AccountModel, account_id)
        return account_to_domain(model) if model is not None else None

    def list_all(self, *, include_inactive: bool = False) -> list[Account]:
        statement = select(AccountModel).order_by(AccountModel.name)
        if not include_inactive:
            statement = statement.where(AccountModel.is_active.is_(True))

        return [
            account_to_domain(model)
            for model in self._session.scalars(statement)
        ]

    def _require_currency(self, code: str) -> CurrencyModel:
        normalized_code = code.strip().upper()
        model = self._session.scalar(
            select(CurrencyModel).where(CurrencyModel.code == normalized_code)
        )
        if model is None:
            raise CurrencyNotFoundError(
                f"Currency {normalized_code} is not registered."
            )
        return model
