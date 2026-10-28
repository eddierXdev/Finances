"""Exchange-rate repository tests against a migrated database."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import text

from app.domain.entities.currency import Currency
from app.domain.entities.exchange_rate import ExchangeRate
from app.domain.enums.exchange_rate_source import ExchangeRateSource
from app.domain.exceptions import (
    CurrencyNotFoundError,
    ImmutableExchangeRateError,
)
from app.infrastructure.database.models import ExchangeRateModel
from app.infrastructure.database.repositories import (
    SqlAlchemyCurrencyRepository,
    SqlAlchemyExchangeRateRepository,
)

TIMESTAMP = datetime(2026, 10, 20, 14, 30, tzinfo=UTC)


def _currency_pair(db_session) -> tuple[Currency, Currency]:
    repository = SqlAlchemyCurrencyRepository(db_session)
    usd = repository.get_by_code("USD")
    cup = repository.get_by_code("CUP")
    assert usd is not None
    assert cup is not None
    return usd, cup


def _manual_rate(
    base: Currency,
    quote: Currency,
    rate: str = "320.50",
    timestamp: datetime = TIMESTAMP,
) -> ExchangeRate:
    return ExchangeRate(
        base_currency=base,
        quote_currency=quote,
        rate=Decimal(rate),
        source=ExchangeRateSource.MANUAL,
        rate_timestamp=timestamp,
    )


def test_manual_rate_is_stored_and_read_back_exactly(db_session) -> None:
    usd, cup = _currency_pair(db_session)
    repository = SqlAlchemyExchangeRateRepository(db_session)
    exchange_rate = ExchangeRate(
        base_currency=usd,
        quote_currency=cup,
        rate=Decimal("320.123456789012"),
        source=ExchangeRateSource.MANUAL,
        rate_timestamp=TIMESTAMP,
        notes="  street rate  ",
    )

    stored = repository.add(exchange_rate)

    assert stored.id is not None
    assert stored.notes == "street rate"

    latest = repository.get_latest("usd", "cup")
    assert latest is not None
    assert latest.rate == Decimal("320.123456789012")
    assert latest.rate_timestamp == TIMESTAMP
    assert latest.source is ExchangeRateSource.MANUAL
    assert latest.base_currency.code == "USD"
    assert latest.quote_currency.code == "CUP"

    storage_type = db_session.execute(
        text("SELECT typeof(rate) FROM exchange_rates WHERE id = :id"),
        {"id": stored.id},
    ).scalar_one()
    assert storage_type == "text"


def test_rate_history_is_ordered_oldest_first(db_session) -> None:
    usd, cup = _currency_pair(db_session)
    repository = SqlAlchemyExchangeRateRepository(db_session)
    older_timestamp = datetime(2026, 10, 1, 9, 0, tzinfo=UTC)
    newer_timestamp = datetime(2026, 10, 20, 14, 30, tzinfo=UTC)

    repository.add(_manual_rate(usd, cup, "300.00", newer_timestamp))
    repository.add(_manual_rate(usd, cup, "290.00", older_timestamp))

    history = repository.list_for_pair("USD", "CUP")
    latest = repository.get_latest("USD", "CUP")

    assert [rate.rate for rate in history] == [
        Decimal("290.00"),
        Decimal("300.00"),
    ]
    assert latest is not None
    assert latest.rate == Decimal("300.00")


def test_latest_by_source_filters_the_rate_history(db_session) -> None:
    usd, cup = _currency_pair(db_session)
    repository = SqlAlchemyExchangeRateRepository(db_session)
    manual = repository.add(
        _manual_rate(usd, cup, "300.00", TIMESTAMP)
    )
    automatic = repository.add(
        ExchangeRate(
            base_currency=usd,
            quote_currency=cup,
            rate=Decimal("320.00"),
            source=ExchangeRateSource.ELTOQUE,
            rate_timestamp=TIMESTAMP + timedelta(hours=1),
        )
    )

    latest_manual = repository.get_latest_by_source(
        "USD", "CUP", ExchangeRateSource.MANUAL
    )
    latest_automatic = repository.get_latest_by_source(
        "USD", "CUP", ExchangeRateSource.ELTOQUE
    )

    assert latest_manual is not None
    assert latest_manual.id == manual.id
    assert latest_manual.rate == Decimal("300.00")
    assert latest_automatic is not None
    assert latest_automatic.id == automatic.id
    assert latest_automatic.rate == Decimal("320.00")


def test_latest_at_or_before_respects_the_historical_cutoff(db_session) -> None:
    usd, cup = _currency_pair(db_session)
    repository = SqlAlchemyExchangeRateRepository(db_session)
    older_timestamp = datetime(2026, 10, 1, 9, 0, tzinfo=UTC)
    newer_timestamp = datetime(2026, 10, 20, 14, 30, tzinfo=UTC)

    older = repository.add(
        _manual_rate(usd, cup, "290.00", older_timestamp)
    )
    newer = repository.add(
        _manual_rate(usd, cup, "300.00", newer_timestamp)
    )

    at_older = repository.get_latest_at_or_before(
        "USD", "CUP", older_timestamp
    )
    between = repository.get_latest_at_or_before(
        "USD", "CUP", older_timestamp + timedelta(days=1)
    )
    at_newer = repository.get_latest_at_or_before(
        "USD", "CUP", newer_timestamp
    )
    before_history = repository.get_latest_at_or_before(
        "USD", "CUP", older_timestamp - timedelta(days=1)
    )

    assert at_older is not None
    assert at_older.id == older.id
    assert between is not None
    assert between.id == older.id
    assert at_newer is not None
    assert at_newer.id == newer.id
    assert before_history is None


def test_latest_at_or_before_rejects_a_naive_cutoff(db_session) -> None:
    repository = SqlAlchemyExchangeRateRepository(db_session)

    with pytest.raises(ValueError, match="timezone-aware"):
        repository.get_latest_at_or_before(
            "USD", "CUP", datetime(2026, 10, 20, 14, 30)
        )


def test_unknown_currency_pair_returns_no_rate(db_session) -> None:
    repository = SqlAlchemyExchangeRateRepository(db_session)

    assert repository.get_latest("USD", "XYZ") is None
    assert repository.list_for_pair("USD", "XYZ") == []


def test_adding_rate_with_unknown_currency_is_rejected(db_session) -> None:
    usd, _ = _currency_pair(db_session)
    unknown = Currency(code="XYZ", name="Unknown Currency", decimal_places=2)
    repository = SqlAlchemyExchangeRateRepository(db_session)

    with pytest.raises(CurrencyNotFoundError):
        repository.add(_manual_rate(usd, unknown))


def test_orm_updates_to_historical_rates_are_rejected(db_session) -> None:
    usd, cup = _currency_pair(db_session)
    repository = SqlAlchemyExchangeRateRepository(db_session)
    stored = repository.add(_manual_rate(usd, cup))

    model = db_session.get(ExchangeRateModel, stored.id)
    assert model is not None
    model.notes = "changed"
    with pytest.raises(ImmutableExchangeRateError):
        db_session.flush()


def test_orm_deletes_of_historical_rates_are_rejected(db_session) -> None:
    usd, cup = _currency_pair(db_session)
    repository = SqlAlchemyExchangeRateRepository(db_session)
    stored = repository.add(_manual_rate(usd, cup))

    model = db_session.get(ExchangeRateModel, stored.id)
    assert model is not None
    db_session.delete(model)
    with pytest.raises(ImmutableExchangeRateError):
        db_session.flush()
