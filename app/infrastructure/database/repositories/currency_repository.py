"""SQLAlchemy currency repository."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.currency import Currency
from app.infrastructure.database.models import CurrencyModel
from app.infrastructure.database.repositories.mapping import currency_to_domain


class SqlAlchemyCurrencyRepository:
    """Currency persistence using SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, currency: Currency) -> Currency:
        model = CurrencyModel(
            code=currency.code,
            name=currency.name,
            symbol=currency.symbol,
            decimal_places=currency.decimal_places,
            is_enabled=currency.is_enabled,
        )
        self._session.add(model)
        self._session.flush()
        return currency_to_domain(model)

    def get_by_code(self, code: str) -> Currency | None:
        normalized_code = code.strip().upper()
        model = self._session.scalar(
            select(CurrencyModel).where(CurrencyModel.code == normalized_code)
        )
        return currency_to_domain(model) if model is not None else None

    def list_all(self, *, enabled_only: bool = False) -> list[Currency]:
        statement = select(CurrencyModel).order_by(CurrencyModel.code)
        if enabled_only:
            statement = statement.where(CurrencyModel.is_enabled.is_(True))

        return [
            currency_to_domain(model)
            for model in self._session.scalars(statement)
        ]
