"""SQLAlchemy exchange-rate repository (append-only)."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.exchange_rate import ExchangeRate
from app.domain.enums.exchange_rate_source import ExchangeRateSource
from app.domain.exceptions import CurrencyNotFoundError
from app.infrastructure.database.models import CurrencyModel, ExchangeRateModel
from app.infrastructure.database.repositories.mapping import (
    exchange_rate_to_domain,
)


class SqlAlchemyExchangeRateRepository:
    """Historical exchange-rate persistence using SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, exchange_rate: ExchangeRate) -> ExchangeRate:
        base_currency = self._require_currency(exchange_rate.base_currency.code)
        quote_currency = self._require_currency(exchange_rate.quote_currency.code)

        model = ExchangeRateModel(
            base_currency=base_currency,
            quote_currency=quote_currency,
            rate=exchange_rate.rate,
            source=exchange_rate.source.value,
            rate_timestamp=exchange_rate.rate_timestamp,
            notes=exchange_rate.notes,
        )
        self._session.add(model)
        self._session.flush()
        return exchange_rate_to_domain(model)

    def get_by_id(self, exchange_rate_id: int) -> ExchangeRate | None:
        model = self._session.get(ExchangeRateModel, exchange_rate_id)
        return exchange_rate_to_domain(model) if model is not None else None

    def get_latest(
        self, base_code: str, quote_code: str
    ) -> ExchangeRate | None:
        base_currency = self._find_currency(base_code)
        quote_currency = self._find_currency(quote_code)
        if base_currency is None or quote_currency is None:
            return None

        statement = (
            select(ExchangeRateModel)
            .where(
                ExchangeRateModel.base_currency_id == base_currency.id,
                ExchangeRateModel.quote_currency_id == quote_currency.id,
            )
            .order_by(
                ExchangeRateModel.rate_timestamp.desc(),
                ExchangeRateModel.id.desc(),
            )
            .limit(1)
        )
        model = self._session.scalar(statement)
        return exchange_rate_to_domain(model) if model is not None else None

    def get_latest_at_or_before(
        self,
        base_code: str,
        quote_code: str,
        as_of: datetime,
    ) -> ExchangeRate | None:
        if as_of.tzinfo is None or as_of.utcoffset() is None:
            raise ValueError("Exchange-rate cutoff must be timezone-aware.")

        base_currency = self._find_currency(base_code)
        quote_currency = self._find_currency(quote_code)
        if base_currency is None or quote_currency is None:
            return None

        statement = (
            select(ExchangeRateModel)
            .where(
                ExchangeRateModel.base_currency_id == base_currency.id,
                ExchangeRateModel.quote_currency_id == quote_currency.id,
                ExchangeRateModel.rate_timestamp <= as_of,
            )
            .order_by(
                ExchangeRateModel.rate_timestamp.desc(),
                ExchangeRateModel.id.desc(),
            )
            .limit(1)
        )
        model = self._session.scalar(statement)
        return exchange_rate_to_domain(model) if model is not None else None

    def get_latest_by_source(
        self,
        base_code: str,
        quote_code: str,
        source: ExchangeRateSource,
    ) -> ExchangeRate | None:
        base_currency = self._find_currency(base_code)
        quote_currency = self._find_currency(quote_code)
        if base_currency is None or quote_currency is None:
            return None

        statement = (
            select(ExchangeRateModel)
            .where(
                ExchangeRateModel.base_currency_id == base_currency.id,
                ExchangeRateModel.quote_currency_id == quote_currency.id,
                ExchangeRateModel.source == source.value,
            )
            .order_by(
                ExchangeRateModel.rate_timestamp.desc(),
                ExchangeRateModel.id.desc(),
            )
            .limit(1)
        )
        model = self._session.scalar(statement)
        return exchange_rate_to_domain(model) if model is not None else None

    def list_for_pair(
        self, base_code: str, quote_code: str
    ) -> list[ExchangeRate]:
        base_currency = self._find_currency(base_code)
        quote_currency = self._find_currency(quote_code)
        if base_currency is None or quote_currency is None:
            return []

        statement = (
            select(ExchangeRateModel)
            .where(
                ExchangeRateModel.base_currency_id == base_currency.id,
                ExchangeRateModel.quote_currency_id == quote_currency.id,
            )
            .order_by(
                ExchangeRateModel.rate_timestamp.asc(),
                ExchangeRateModel.id.asc(),
            )
        )
        return [
            exchange_rate_to_domain(model)
            for model in self._session.scalars(statement)
        ]

    def _find_currency(self, code: str) -> CurrencyModel | None:
        normalized_code = code.strip().upper()
        return self._session.scalar(
            select(CurrencyModel).where(CurrencyModel.code == normalized_code)
        )

    def _require_currency(self, code: str) -> CurrencyModel:
        model = self._find_currency(code)
        if model is None:
            raise CurrencyNotFoundError(
                f"Currency {code.strip().upper()} is not registered."
            )
        return model
