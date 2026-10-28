"""Account repository tests against a migrated database."""

from __future__ import annotations

import pytest

from app.domain.entities.account import Account
from app.domain.entities.currency import Currency
from app.domain.exceptions import (
    AccountNotFoundError,
    CurrencyNotFoundError,
)
from app.infrastructure.database.repositories import (
    SqlAlchemyAccountRepository,
    SqlAlchemyCurrencyRepository,
)


def _currency(db_session, code: str = "USD") -> Currency:
    currency = SqlAlchemyCurrencyRepository(db_session).get_by_code(code)
    assert currency is not None
    return currency


def test_account_is_stored_with_its_native_currency(db_session) -> None:
    usd = _currency(db_session)
    repository = SqlAlchemyAccountRepository(db_session)

    stored = repository.add(
        Account(name="  Cash USD  ", currency=usd, account_type="CASH")
    )

    assert stored.id is not None
    fetched = repository.get_by_id(stored.id)
    assert fetched == stored
    assert fetched is not None
    assert fetched.name == "Cash USD"
    assert fetched.currency.code == "USD"
    assert fetched.account_type == "CASH"


def test_account_deactivation_is_non_destructive_and_filtered(db_session) -> None:
    repository = SqlAlchemyAccountRepository(db_session)
    stored = repository.add(
        Account(name="Old Account", currency=_currency(db_session))
    )

    repository.save(stored.deactivate())

    assert repository.list_all() == []
    inactive = repository.list_all(include_inactive=True)
    assert [account.name for account in inactive] == ["Old Account"]
    fetched = repository.get_by_id(stored.id)
    assert fetched is not None
    assert fetched.is_active is False


def test_account_currency_cannot_be_changed(db_session) -> None:
    repository = SqlAlchemyAccountRepository(db_session)
    stored = repository.add(
        Account(name="Cash USD", currency=_currency(db_session))
    )

    with pytest.raises(ValueError):
        repository.save(
            Account(
                id=stored.id,
                name="Cash USD",
                currency=_currency(db_session, "CUP"),
            )
        )


def test_account_requires_a_registered_currency(db_session) -> None:
    repository = SqlAlchemyAccountRepository(db_session)

    with pytest.raises(CurrencyNotFoundError):
        repository.add(
            Account(
                name="Unknown",
                currency=Currency(
                    code="ZZZ", name="Unknown", decimal_places=2
                ),
            )
        )


def test_saving_an_unknown_account_fails(db_session) -> None:
    repository = SqlAlchemyAccountRepository(db_session)

    with pytest.raises(AccountNotFoundError):
        repository.save(
            Account(
                id=999999,
                name="Missing",
                currency=_currency(db_session),
            )
        )
