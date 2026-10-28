"""Expense entity rules."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.domain.entities.account import Account
from app.domain.entities.currency import Currency
from app.domain.entities.expense import Expense
from app.domain.enums.expense_type import ExpenseType
from app.domain.exceptions import (
    AccountCurrencyMismatchError,
    InvalidExpenseError,
)
from app.domain.value_objects.money import Money

USD = Currency(code="USD", name="US Dollar", decimal_places=2, id=1)
CUP = Currency(code="CUP", name="Cuban Peso", decimal_places=2, id=2)
ACCOUNT = Account(name="Cash USD", currency=USD, id=1)
NOW = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)


def _expense(**kwargs) -> Expense:
    values = {
        "account": ACCOUNT,
        "expense_type": ExpenseType.ADVERTISING,
        "amount": Money("25.00", USD),
        "expense_date": NOW,
    }
    values.update(kwargs)
    return Expense(**values)


def test_expense_stores_positive_amount_and_derives_negative_ledger_sign() -> None:
    expense = _expense(
        description="  Facebook ads ",
        notes="  October campaign ",
    )

    assert expense.account is ACCOUNT
    assert expense.account_id == ACCOUNT.id
    assert expense.expense_type is ExpenseType.ADVERTISING
    assert expense.amount == Money("25.00", USD)
    assert expense.signed_amount == Money("-25.00", USD)
    assert expense.currency_code == "USD"
    assert expense.description == "Facebook ads"
    assert expense.notes == "October campaign"
    assert expense.id is None


def test_expense_date_is_normalized_to_utc() -> None:
    local_time = datetime(
        2026, 10, 27, 7, 0, tzinfo=timezone(timedelta(hours=-5))
    )

    assert _expense(expense_date=local_time).expense_date == NOW


def test_expense_rejects_non_positive_amounts() -> None:
    for amount in ("0.00", "-1.00"):
        with pytest.raises(InvalidExpenseError):
            _expense(amount=Money(amount, USD))


def test_expense_currency_must_match_the_account() -> None:
    with pytest.raises(AccountCurrencyMismatchError):
        _expense(amount=Money("25.00", CUP))


def test_expense_requires_an_account_and_money() -> None:
    with pytest.raises(TypeError):
        _expense(account="account")

    with pytest.raises(TypeError):
        _expense(amount="25.00")


def test_expense_requires_a_known_category() -> None:
    with pytest.raises(TypeError):
        _expense(expense_type="ADVERTISING")


def test_expense_date_must_be_timezone_aware() -> None:
    with pytest.raises(InvalidExpenseError):
        _expense(expense_date=datetime(2026, 10, 27, 12, 0))

    with pytest.raises(TypeError):
        _expense(expense_date="2026-10-27")


def test_expense_id_must_be_a_positive_integer() -> None:
    assert _expense(id=1).id == 1

    for expense_id in (0, -1, True, "1"):
        with pytest.raises(ValueError):
            _expense(id=expense_id)
