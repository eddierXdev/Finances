"""Expense application use cases against a migrated SQLite database."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.application.finances import (
    AddCapital,
    CapitalMovementRequest,
    GetAccountBalance,
    RegisterExpense,
    RegisterExpenseRequest,
)
from app.domain.entities.account import Account
from app.domain.entities.currency import Currency
from app.domain.enums.expense_type import ExpenseType
from app.domain.enums.financial_transaction_type import (
    FinancialTransactionType,
)
from app.domain.exceptions import (
    AccountCurrencyMismatchError,
    AccountNotFoundError,
    InactiveAccountError,
    InvalidExpenseError,
)
from app.domain.value_objects.money import Money
from app.infrastructure.database.repositories import (
    SqlAlchemyAccountRepository,
    SqlAlchemyCapitalMovementRepository,
    SqlAlchemyCurrencyRepository,
    SqlAlchemyExpenseRepository,
    SqlAlchemyFinancialTransactionRepository,
)

NOW = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)
EARLIER = NOW - timedelta(days=2)


def _currency(db_session, code: str = "USD") -> Currency:
    currency = SqlAlchemyCurrencyRepository(db_session).get_by_code(code)
    assert currency is not None
    return currency


def _account(
    db_session,
    name: str = "Cash USD",
    code: str = "USD",
    *,
    active: bool = True,
) -> Account:
    return SqlAlchemyAccountRepository(db_session).add(
        Account(
            name=name,
            currency=_currency(db_session, code),
            is_active=active,
        )
    )


def _expense_service(db_session) -> RegisterExpense:
    return RegisterExpense(
        accounts=SqlAlchemyAccountRepository(db_session),
        expenses=SqlAlchemyExpenseRepository(db_session),
        transactions=SqlAlchemyFinancialTransactionRepository(
            db_session
        ),
    )


def _expenses(db_session) -> SqlAlchemyExpenseRepository:
    return SqlAlchemyExpenseRepository(db_session)


def _entries(db_session, account: Account):
    return SqlAlchemyFinancialTransactionRepository(
        db_session
    ).list_for_account(account.id)


def _balance(db_session, account: Account) -> Money:
    return GetAccountBalance(
        SqlAlchemyAccountRepository(db_session),
        SqlAlchemyFinancialTransactionRepository(db_session),
    ).execute(account.id)


def _add_capital(db_session, account: Account, amount: str) -> None:
    AddCapital(
        SqlAlchemyAccountRepository(db_session),
        SqlAlchemyCapitalMovementRepository(db_session),
        SqlAlchemyFinancialTransactionRepository(db_session),
    ).execute(
        CapitalMovementRequest(
            account_id=account.id,
            amount=Money(amount, account.currency),
            movement_date=EARLIER,
        )
    )


def test_register_expense_persists_and_creates_a_negative_ledger_entry(
    db_session,
) -> None:
    account = _account(db_session)
    _add_capital(db_session, account, "100.00")

    stored = _expense_service(db_session).execute(
        RegisterExpenseRequest(
            account_id=account.id,
            expense_type=ExpenseType.ADVERTISING,
            amount=Money("25.00", account.currency),
            expense_date=NOW,
            description="  Facebook ads ",
            notes="  October campaign ",
        )
    )

    assert stored.id is not None
    assert stored.account_id == account.id
    assert stored.expense_type is ExpenseType.ADVERTISING
    assert stored.amount == Money("25.00", account.currency)
    assert stored.signed_amount == Money("-25.00", account.currency)
    assert stored.description == "Facebook ads"
    assert stored.notes == "October campaign"

    repository = _expenses(db_session)
    assert repository.get_by_id(stored.id) == stored
    assert repository.list_for_account(account.id) == [stored]
    assert repository.list_all() == [stored]

    entries = _entries(db_session, account)
    assert [entry.transaction_type for entry in entries] == [
        FinancialTransactionType.CAPITAL_CONTRIBUTION,
        FinancialTransactionType.EXPENSE,
    ]
    assert entries[1].amount == Money("-25.00", account.currency)
    assert entries[1].expense_id == stored.id
    assert entries[1].description == "Facebook ads"
    assert entries[1].purchase_id is None
    assert entries[1].sale_id is None
    assert entries[1].customer_return_id is None
    assert entries[1].supplier_return_id is None
    assert entries[1].capital_movement_id is None
    assert _balance(db_session, account) == Money(
        "75.00", account.currency
    )


def test_expense_without_description_uses_its_category_in_the_ledger(
    db_session,
) -> None:
    account = _account(db_session)

    stored = _expense_service(db_session).execute(
        RegisterExpenseRequest(
            account_id=account.id,
            expense_type=ExpenseType.INTERNET,
            amount=Money("10.00", account.currency),
            expense_date=NOW,
        )
    )

    entry = _entries(db_session, account)[0]
    assert entry.description == "Expense INTERNET"
    assert entry.expense_id == stored.id
    assert _balance(db_session, account) == Money(
        "-10.00", account.currency
    )


def test_expense_requires_an_active_account_with_the_same_currency(
    db_session,
) -> None:
    usd_account = _account(db_session, "Cash USD")
    cup_account = _account(db_session, "Cash CUP", "CUP")
    inactive = _account(db_session, "Closed USD", active=False)
    service = _expense_service(db_session)

    with pytest.raises(InactiveAccountError):
        service.execute(
            RegisterExpenseRequest(
                account_id=inactive.id,
                expense_type=ExpenseType.OTHER,
                amount=Money("10.00", inactive.currency),
                expense_date=NOW,
            )
        )
    with pytest.raises(AccountCurrencyMismatchError):
        service.execute(
            RegisterExpenseRequest(
                account_id=cup_account.id,
                expense_type=ExpenseType.OTHER,
                amount=Money("10.00", usd_account.currency),
                expense_date=NOW,
            )
        )
    with pytest.raises(AccountNotFoundError):
        service.execute(
            RegisterExpenseRequest(
                account_id=999999,
                expense_type=ExpenseType.OTHER,
                amount=Money("10.00", usd_account.currency),
                expense_date=NOW,
            )
        )

    assert _expenses(db_session).list_all() == []
    assert _entries(db_session, usd_account) == []
    assert _entries(db_session, cup_account) == []


def test_expense_rejects_non_positive_amounts_and_invalid_input(
    db_session,
) -> None:
    account = _account(db_session)
    service = _expense_service(db_session)

    for amount in ("0.00", "-1.00"):
        with pytest.raises(InvalidExpenseError):
            service.execute(
                RegisterExpenseRequest(
                    account_id=account.id,
                    expense_type=ExpenseType.OTHER,
                    amount=Money(amount, account.currency),
                    expense_date=NOW,
                )
            )

    with pytest.raises(TypeError):
        service.execute(
            RegisterExpenseRequest(
                account_id=account.id,
                expense_type="OTHER",
                amount=Money("1.00", account.currency),
                expense_date=NOW,
            )
        )
    with pytest.raises(InvalidExpenseError):
        service.execute(
            RegisterExpenseRequest(
                account_id=account.id,
                expense_type=ExpenseType.OTHER,
                amount=Money("1.00", account.currency),
                expense_date=datetime(2026, 10, 27, 12, 0),
            )
        )

    assert _expenses(db_session).list_all() == []
    assert _entries(db_session, account) == []


def test_expense_lists_are_ordered_by_date(db_session) -> None:
    account = _account(db_session)
    service = _expense_service(db_session)

    first = service.execute(
        RegisterExpenseRequest(
            account_id=account.id,
            expense_type=ExpenseType.PACKAGING,
            amount=Money("4.00", account.currency),
            expense_date=EARLIER,
        )
    )
    second = service.execute(
        RegisterExpenseRequest(
            account_id=account.id,
            expense_type=ExpenseType.DELIVERY,
            amount=Money("6.00", account.currency),
            expense_date=NOW,
        )
    )

    repository = _expenses(db_session)
    assert repository.list_for_account(account.id) == [first, second]
    assert repository.list_all() == [second, first]
    assert [entry.amount for entry in _entries(db_session, account)] == [
        Money("-4.00", account.currency),
        Money("-6.00", account.currency),
    ]
    assert _balance(db_session, account) == Money(
        "-10.00", account.currency
    )
