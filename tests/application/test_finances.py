"""Financial use-case tests against a migrated database."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.application.finances import (
    AddCapital,
    CapitalMovementRequest,
    CreateAccount,
    CreateAccountRequest,
    ExchangeCurrency,
    ExchangeCurrencyRequest,
    GetAccountBalance,
    TransferMoney,
    TransferMoneyRequest,
    WithdrawCapital,
)
from app.domain.entities.account import Account
from app.domain.entities.currency import Currency
from app.domain.entities.exchange_rate import ExchangeRate
from app.domain.enums.exchange_rate_source import ExchangeRateSource
from app.domain.enums.financial_transaction_type import (
    FinancialTransactionType,
)
from app.domain.exceptions import (
    AccountCurrencyMismatchError,
    AccountNotFoundError,
    ExchangeRateNotFoundError,
    InactiveAccountError,
    InvalidTransferError,
)
from app.domain.value_objects.money import Money
from app.infrastructure.database.repositories import (
    SqlAlchemyAccountRepository,
    SqlAlchemyAccountTransferRepository,
    SqlAlchemyCapitalMovementRepository,
    SqlAlchemyCurrencyRepository,
    SqlAlchemyExchangeRateRepository,
    SqlAlchemyFinancialTransactionRepository,
)

NOW = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)
EARLIER = datetime(2026, 10, 26, 12, 0, tzinfo=UTC)


def _currency(db_session, code: str = "USD") -> Currency:
    currency = SqlAlchemyCurrencyRepository(db_session).get_by_code(code)
    assert currency is not None
    return currency


def _account(
    db_session, name: str, code: str = "USD"
) -> Account:
    return SqlAlchemyAccountRepository(db_session).add(
        Account(name=name, currency=_currency(db_session, code))
    )


def _repositories(db_session):
    return {
        "accounts": SqlAlchemyAccountRepository(db_session),
        "movements": SqlAlchemyCapitalMovementRepository(db_session),
        "transfers": SqlAlchemyAccountTransferRepository(db_session),
        "transactions": SqlAlchemyFinancialTransactionRepository(db_session),
        "rates": SqlAlchemyExchangeRateRepository(db_session),
    }


def _capital_service(db_session, name: str = "AddCapital"):
    repositories = _repositories(db_session)
    service_class = AddCapital if name == "AddCapital" else WithdrawCapital
    return (
        service_class(
            repositories["accounts"],
            repositories["movements"],
            repositories["transactions"],
        ),
        repositories,
    )


def _entries(db_session, account_id: int):
    return SqlAlchemyFinancialTransactionRepository(
        db_session
    ).list_for_account(account_id)


def test_create_account_persists_its_native_currency(db_session) -> None:
    usd = _currency(db_session)
    repository = SqlAlchemyAccountRepository(db_session)

    account = CreateAccount(repository).execute(
        CreateAccountRequest(
            name="  Wallet USD  ",
            currency=usd,
            account_type="CASH",
            notes="  Everyday  ",
        )
    )

    assert account.id is not None
    assert account.name == "Wallet USD"
    assert account.account_type == "CASH"
    assert account.notes == "Everyday"
    assert repository.get_by_id(account.id) == account


def test_capital_contribution_and_withdrawal_update_the_balance(
    db_session,
) -> None:
    usd = _currency(db_session)
    account = _account(db_session, "Cash USD")
    add_capital, repositories = _capital_service(db_session)
    withdraw, _ = _capital_service(db_session, "WithdrawCapital")

    add_capital.execute(
        CapitalMovementRequest(
            account_id=account.id,
            amount=Money("100.00", usd),
            movement_date=EARLIER,
        )
    )
    withdraw.execute(
        CapitalMovementRequest(
            account_id=account.id,
            amount=Money("30.00", usd),
            movement_date=NOW,
        )
    )

    balance = GetAccountBalance(
        repositories["accounts"], repositories["transactions"]
    ).execute(account.id)
    entries = _entries(db_session, account.id)
    movements = repositories["movements"].list_for_account(account.id)

    assert balance == Money("70.00", usd)
    assert [entry.amount for entry in entries] == [
        Money("100.00", usd),
        Money("-30.00", usd),
    ]
    assert [entry.transaction_type for entry in entries] == [
        FinancialTransactionType.CAPITAL_CONTRIBUTION,
        FinancialTransactionType.CAPITAL_WITHDRAWAL,
    ]
    assert [movement.signed_amount for movement in movements] == [
        Money("100.00", usd),
        Money("-30.00", usd),
    ]
    assert entries[0].capital_movement_id == movements[0].id
    assert entries[1].capital_movement_id == movements[1].id


def test_same_currency_transfer_creates_two_signed_entries(db_session) -> None:
    usd = _currency(db_session)
    source = _account(db_session, "Cash USD")
    destination = _account(db_session, "Bank USD")
    add_capital, repositories = _capital_service(db_session)
    add_capital.execute(
        CapitalMovementRequest(
            account_id=source.id,
            amount=Money("100.00", usd),
            movement_date=EARLIER,
        )
    )

    transfer = TransferMoney(
        repositories["accounts"],
        repositories["transfers"],
        repositories["transactions"],
    ).execute(
        TransferMoneyRequest(
            source_account_id=source.id,
            destination_account_id=destination.id,
            amount=Money("40.00", usd),
            transfer_date=NOW,
        )
    )

    stored = repositories["transfers"].get_by_id(transfer.id)
    source_entries = _entries(db_session, source.id)
    destination_entries = _entries(db_session, destination.id)
    source_transfer = [
        entry
        for entry in source_entries
        if entry.transaction_type is FinancialTransactionType.TRANSFER
    ]
    destination_transfer = destination_entries[0]
    balance = GetAccountBalance(
        repositories["accounts"], repositories["transactions"]
    )

    assert stored == transfer
    assert transfer.exchange_rate is None
    assert transfer.source_amount == transfer.destination_amount
    assert len(source_transfer) == 1
    assert source_transfer[0].amount == Money("-40.00", usd)
    assert source_transfer[0].account_transfer_id == transfer.id
    assert destination_transfer.amount == Money("40.00", usd)
    assert destination_transfer.account_transfer_id == transfer.id
    assert balance.execute(source.id) == Money("60.00", usd)
    assert balance.execute(destination.id) == Money("40.00", usd)


def test_cross_currency_exchange_uses_a_historical_rate(db_session) -> None:
    usd = _currency(db_session)
    cup = _currency(db_session, "CUP")
    source = _account(db_session, "Cash USD")
    destination = _account(db_session, "Cash CUP", "CUP")
    add_capital, repositories = _capital_service(db_session)
    add_capital.execute(
        CapitalMovementRequest(
            account_id=source.id,
            amount=Money("100.00", usd),
            movement_date=EARLIER,
        )
    )
    rate = repositories["rates"].add(
        ExchangeRate(
            base_currency=usd,
            quote_currency=cup,
            rate=Decimal("320"),
            source=ExchangeRateSource.MANUAL,
            rate_timestamp=NOW,
        )
    )

    transfer = ExchangeCurrency(
        repositories["accounts"],
        repositories["rates"],
        repositories["transfers"],
        repositories["transactions"],
    ).execute(
        ExchangeCurrencyRequest(
            source_account_id=source.id,
            destination_account_id=destination.id,
            source_amount=Money("10.00", usd),
            exchange_rate_id=rate.id,
            transfer_date=NOW,
        )
    )

    source_entry = _entries(db_session, source.id)[-1]
    destination_entry = _entries(db_session, destination.id)[0]
    balance = GetAccountBalance(
        repositories["accounts"], repositories["transactions"]
    )

    assert transfer.is_cross_currency is True
    assert transfer.exchange_rate == rate
    assert transfer.destination_amount == Money("3200.00", cup)
    assert source_entry.transaction_type is (
        FinancialTransactionType.CURRENCY_EXCHANGE
    )
    assert source_entry.amount == Money("-10.00", usd)
    assert destination_entry.amount == Money("3200.00", cup)
    assert source_entry.account_transfer_id == transfer.id
    assert destination_entry.account_transfer_id == transfer.id
    assert source_entry.exchange_rate_id == rate.id
    assert destination_entry.exchange_rate_id == rate.id
    assert balance.execute(source.id) == Money("90.00", usd)
    assert balance.execute(destination.id) == Money("3200.00", cup)


def test_balance_sums_decimal_amounts_exactly(db_session) -> None:
    usd = _currency(db_session)
    account = _account(db_session, "Exact USD")
    add_capital, repositories = _capital_service(db_session)

    add_capital.execute(
        CapitalMovementRequest(
            account_id=account.id,
            amount=Money("0.10", usd),
            movement_date=EARLIER,
        )
    )
    add_capital.execute(
        CapitalMovementRequest(
            account_id=account.id,
            amount=Money("0.20", usd),
            movement_date=NOW,
        )
    )

    balance = GetAccountBalance(
        repositories["accounts"], repositories["transactions"]
    ).execute(account.id)

    assert balance == Money("0.30", usd)


def test_capital_rejects_a_currency_other_than_the_account_currency(
    db_session,
) -> None:
    usd = _currency(db_session)
    cup = _currency(db_session, "CUP")
    account = _account(db_session, "Cash USD")
    add_capital, repositories = _capital_service(db_session)

    with pytest.raises(AccountCurrencyMismatchError):
        add_capital.execute(
            CapitalMovementRequest(
                account_id=account.id,
                amount=Money("10.00", cup),
            )
        )

    assert _entries(db_session, account.id) == []
    assert repositories["movements"].list_for_account(account.id) == []


def test_inactive_accounts_cannot_receive_capital(db_session) -> None:
    usd = _currency(db_session)
    repository = SqlAlchemyAccountRepository(db_session)
    account = _account(db_session, "Old USD")
    repository.save(account.deactivate())
    add_capital, repositories = _capital_service(db_session)

    with pytest.raises(InactiveAccountError):
        add_capital.execute(
            CapitalMovementRequest(
                account_id=account.id,
                amount=Money("10.00", usd),
            )
        )

    assert _entries(db_session, account.id) == []


def test_transfer_money_rejects_cross_currency_accounts(db_session) -> None:
    usd = _currency(db_session)
    source = _account(db_session, "Cash USD")
    destination = _account(db_session, "Cash CUP", "CUP")
    repositories = _repositories(db_session)

    with pytest.raises(InvalidTransferError):
        TransferMoney(
            repositories["accounts"],
            repositories["transfers"],
            repositories["transactions"],
        ).execute(
            TransferMoneyRequest(
                source_account_id=source.id,
                destination_account_id=destination.id,
                amount=Money("10.00", usd),
            )
        )

    assert repositories["transfers"].list_for_account(source.id) == []


def test_transfer_money_rejects_the_same_account(db_session) -> None:
    usd = _currency(db_session)
    account = _account(db_session, "Cash USD")
    repositories = _repositories(db_session)

    with pytest.raises(InvalidTransferError):
        TransferMoney(
            repositories["accounts"],
            repositories["transfers"],
            repositories["transactions"],
        ).execute(
            TransferMoneyRequest(
                source_account_id=account.id,
                destination_account_id=account.id,
                amount=Money("10.00", usd),
            )
        )

    assert repositories["transfers"].list_for_account(account.id) == []


def test_exchange_currency_rejects_same_currency_accounts(db_session) -> None:
    usd = _currency(db_session)
    source = _account(db_session, "Cash USD")
    destination = _account(db_session, "Bank USD")
    repositories = _repositories(db_session)

    with pytest.raises(InvalidTransferError):
        ExchangeCurrency(
            repositories["accounts"],
            repositories["rates"],
            repositories["transfers"],
            repositories["transactions"],
        ).execute(
            ExchangeCurrencyRequest(
                source_account_id=source.id,
                destination_account_id=destination.id,
                source_amount=Money("10.00", usd),
                exchange_rate_id=999999,
            )
        )

    assert repositories["transfers"].list_for_account(source.id) == []


def test_exchange_currency_requires_the_referenced_rate(db_session) -> None:
    usd = _currency(db_session)
    source = _account(db_session, "Cash USD")
    destination = _account(db_session, "Cash CUP", "CUP")
    repositories = _repositories(db_session)

    with pytest.raises(ExchangeRateNotFoundError):
        ExchangeCurrency(
            repositories["accounts"],
            repositories["rates"],
            repositories["transfers"],
            repositories["transactions"],
        ).execute(
            ExchangeCurrencyRequest(
                source_account_id=source.id,
                destination_account_id=destination.id,
                source_amount=Money("10.00", usd),
                exchange_rate_id=999999,
            )
        )

    assert repositories["transfers"].list_for_account(source.id) == []


def test_exchange_currency_rejects_a_rate_for_the_wrong_currency_pair(
    db_session,
) -> None:
    usd = _currency(db_session)
    eur = _currency(db_session, "EUR")
    source = _account(db_session, "Cash USD")
    destination = _account(db_session, "Cash CUP", "CUP")
    repositories = _repositories(db_session)
    rate = repositories["rates"].add(
        ExchangeRate(
            base_currency=usd,
            quote_currency=eur,
            rate=Decimal("0.9"),
            source=ExchangeRateSource.MANUAL,
            rate_timestamp=NOW,
        )
    )

    with pytest.raises(AccountCurrencyMismatchError):
        ExchangeCurrency(
            repositories["accounts"],
            repositories["rates"],
            repositories["transfers"],
            repositories["transactions"],
        ).execute(
            ExchangeCurrencyRequest(
                source_account_id=source.id,
                destination_account_id=destination.id,
                source_amount=Money("10.00", usd),
                exchange_rate_id=rate.id,
            )
        )

    assert repositories["transfers"].list_for_account(source.id) == []


def test_balance_for_an_unknown_account_fails(db_session) -> None:
    repositories = _repositories(db_session)

    with pytest.raises(AccountNotFoundError):
        GetAccountBalance(
            repositories["accounts"], repositories["transactions"]
        ).execute(999999)
