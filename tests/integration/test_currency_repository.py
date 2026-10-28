"""Currency repository tests against a migrated database."""

from __future__ import annotations

from app.domain.entities.currency import Currency
from app.infrastructure.database.repositories import SqlAlchemyCurrencyRepository

INITIAL_CURRENCY_CODES = {"CAD", "CUP", "EUR", "GBP", "MLC", "MXN", "USD"}


def test_initial_currencies_are_seeded(db_session) -> None:
    repository = SqlAlchemyCurrencyRepository(db_session)

    currencies = repository.list_all()

    assert {currency.code for currency in currencies} == INITIAL_CURRENCY_CODES
    assert all(currency.decimal_places == 2 for currency in currencies)
    assert all(currency.is_enabled for currency in currencies)
    assert all(currency.id is not None for currency in currencies)


def test_currency_lookup_normalizes_the_code(db_session) -> None:
    repository = SqlAlchemyCurrencyRepository(db_session)

    currency = repository.get_by_code(" usd ")

    assert currency is not None
    assert currency.code == "USD"
    assert currency.name == "US Dollar"


def test_unknown_currency_returns_none(db_session) -> None:
    repository = SqlAlchemyCurrencyRepository(db_session)

    assert repository.get_by_code("XYZ") is None


def test_custom_currency_can_be_added(db_session) -> None:
    repository = SqlAlchemyCurrencyRepository(db_session)
    currency = Currency(
        code="XYZ",
        name="Test Currency",
        decimal_places=3,
        symbol="X",
    )

    stored = repository.add(currency)

    assert stored.id is not None
    assert repository.get_by_code("XYZ") == stored


def test_enabled_only_filter_excludes_disabled_currencies(db_session) -> None:
    repository = SqlAlchemyCurrencyRepository(db_session)
    repository.add(
        Currency(code="ZZZ", name="Disabled Currency", decimal_places=2, is_enabled=False)
    )

    enabled_codes = {currency.code for currency in repository.list_all(enabled_only=True)}
    all_codes = {currency.code for currency in repository.list_all()}

    assert "ZZZ" not in enabled_codes
    assert "ZZZ" in all_codes
