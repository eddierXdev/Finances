"""Financial ledger repository tests against a migrated database."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.domain.entities.account import Account
from app.domain.entities.currency import Currency
from app.domain.entities.financial_transaction import FinancialTransaction
from app.domain.enums.financial_transaction_type import (
    FinancialTransactionType,
)
from app.domain.value_objects.money import Money
from app.infrastructure.database.repositories import (
    SqlAlchemyAccountRepository,
    SqlAlchemyCurrencyRepository,
    SqlAlchemyFinancialTransactionRepository,
)

DAY_ONE = datetime(2026, 10, 25, 12, 0, tzinfo=UTC)
DAY_TWO = datetime(2026, 10, 26, 12, 0, tzinfo=UTC)
DAY_THREE = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)


def _usd(db_session) -> Currency:
    currency = SqlAlchemyCurrencyRepository(db_session).get_by_code("USD")
    assert currency is not None
    return currency


def _account(db_session, currency: Currency) -> Account:
    return SqlAlchemyAccountRepository(db_session).add(
        Account(name="Ledger USD", currency=currency)
    )


def _entry(
    db_session,
    account: Account,
    amount: str,
    transaction_date: datetime,
) -> FinancialTransaction:
    return SqlAlchemyFinancialTransactionRepository(db_session).add(
        FinancialTransaction(
            account=account,
            amount=Money(amount, account.currency),
            transaction_type=FinancialTransactionType.ADJUSTMENT,
            transaction_date=transaction_date,
        )
    )


def test_ledger_can_be_filtered_by_date_and_is_ordered(db_session) -> None:
    account = _account(db_session, _usd(db_session))
    _entry(db_session, account, "5.00", DAY_ONE)
    _entry(db_session, account, "-2.00", DAY_TWO)
    _entry(db_session, account, "1.00", DAY_THREE)
    repository = SqlAlchemyFinancialTransactionRepository(db_session)

    entries = repository.list_for_account(
        account.id, start=DAY_TWO, end=DAY_THREE
    )

    assert [entry.amount for entry in entries] == [
        Money("-2.00", account.currency),
        Money("1.00", account.currency),
    ]
    assert repository.get_balance(account) == Money("4.00", account.currency)


def test_ledger_rejects_invalid_date_ranges(db_session) -> None:
    account = _account(db_session, _usd(db_session))
    repository = SqlAlchemyFinancialTransactionRepository(db_session)

    with pytest.raises(ValueError):
        repository.list_for_account(
            account.id, start=datetime(2026, 10, 27, 12, 0)
        )

    with pytest.raises(ValueError):
        repository.list_for_account(
            account.id, start=DAY_THREE, end=DAY_ONE
        )
