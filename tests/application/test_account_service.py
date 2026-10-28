"""Account application-service tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.application.finances.account_service import AccountService
from app.application.finances.create_account import CreateAccountRequest
from app.domain.entities.financial_transaction import FinancialTransaction
from app.domain.enums.financial_transaction_type import (
    FinancialTransactionType,
)
from app.domain.exceptions import AccountNotFoundError
from app.domain.value_objects.money import Money
from app.infrastructure.database.session import create_session_factory
from app.infrastructure.database.unit_of_work import (
    SqlAlchemyUnitOfWorkFactory,
)


@pytest.fixture
def unit_of_work_factory(migrated_engine) -> SqlAlchemyUnitOfWorkFactory:
    return SqlAlchemyUnitOfWorkFactory(
        create_session_factory(migrated_engine)
    )


@pytest.fixture
def accounts(unit_of_work_factory) -> AccountService:
    return AccountService(unit_of_work_factory)


def _usd(accounts: AccountService):
    return next(
        currency
        for currency in accounts.list_enabled_currencies()
        if currency.code == "USD"
    )


def test_account_can_be_created_and_listed_with_zero_balance(
    accounts,
) -> None:
    usd = _usd(accounts)

    created = accounts.create_account(
        CreateAccountRequest(
            name="Main Cash",
            currency=usd,
            account_type="Cash",
            notes="Daily use",
        )
    )

    rows = accounts.list_accounts()

    assert created.id is not None
    assert len(rows) == 1
    row = rows[0]
    assert row.account_id == created.id
    assert row.name == "Main Cash"
    assert row.account_type == "Cash"
    assert row.currency_code == "USD"
    assert row.balance == Money("0", usd)
    assert row.is_active is True
    assert row.notes == "Daily use"


def test_balance_is_derived_from_the_native_ledger(
    accounts, unit_of_work_factory
) -> None:
    usd = _usd(accounts)
    created = accounts.create_account(
        CreateAccountRequest(name="Bank", currency=usd)
    )
    assert created.id is not None

    with unit_of_work_factory.unit_of_work() as uow:
        account = uow.accounts.get_by_id(created.id)
        assert account is not None
        uow.transactions.add(
            FinancialTransaction(
                account=account,
                amount=Money("125.50", usd),
                transaction_type=(
                    FinancialTransactionType.CAPITAL_CONTRIBUTION
                ),
                transaction_date=datetime.now(UTC),
                description="Opening capital",
            )
        )
        uow.commit()

    row = accounts.list_accounts()[0]
    assert row.balance == Money("125.50", usd)


def test_accounts_can_be_deactivated_and_reactivated(accounts) -> None:
    usd = _usd(accounts)
    created = accounts.create_account(
        CreateAccountRequest(name="Old Wallet", currency=usd)
    )
    assert created.id is not None

    deactivated = accounts.set_account_active(
        created.id, is_active=False
    )
    assert deactivated.is_active is False
    assert accounts.list_accounts() == ()

    inactive = accounts.list_accounts(include_inactive=True)
    assert len(inactive) == 1
    assert inactive[0].is_active is False

    activated = accounts.set_account_active(created.id, is_active=True)
    assert activated.is_active is True
    assert len(accounts.list_accounts()) == 1


def test_missing_account_raises_clear_error(accounts) -> None:
    with pytest.raises(AccountNotFoundError):
        accounts.set_account_active(999, is_active=False)
