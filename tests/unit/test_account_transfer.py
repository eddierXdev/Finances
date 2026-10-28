"""Account transfer and currency exchange domain rules."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.domain.entities.account import Account
from app.domain.entities.account_transfer import AccountTransfer
from app.domain.entities.currency import Currency
from app.domain.entities.exchange_rate import ExchangeRate
from app.domain.enums.exchange_rate_source import ExchangeRateSource
from app.domain.exceptions import (
    AccountCurrencyMismatchError,
    InvalidTransferError,
)
from app.domain.value_objects.money import Money

USD = Currency(code="USD", name="US Dollar", decimal_places=2)
CUP = Currency(code="CUP", name="Cuban Peso", decimal_places=2)
NOW = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)
USD_ACCOUNT = Account(name="Cash USD", currency=USD, id=1)
OTHER_USD_ACCOUNT = Account(name="Bank USD", currency=USD, id=2)
CUP_ACCOUNT = Account(name="Cash CUP", currency=CUP, id=3)
USD_CUP_RATE = ExchangeRate(
    base_currency=USD,
    quote_currency=CUP,
    rate=Decimal("320"),
    source=ExchangeRateSource.MANUAL,
    rate_timestamp=NOW,
    id=10,
)


def _same_currency_transfer(
    amount: str = "40.00",
    destination_amount: str = "40.00",
    **kwargs,
) -> AccountTransfer:
    return AccountTransfer(
        source_account=USD_ACCOUNT,
        destination_account=OTHER_USD_ACCOUNT,
        source_amount=Money(amount, USD),
        destination_amount=Money(destination_amount, USD),
        transfer_date=NOW,
        **kwargs,
    )


def _cross_currency_transfer(
    exchange_rate: ExchangeRate | None = USD_CUP_RATE,
    destination_amount: Money | None = None,
    **kwargs,
) -> AccountTransfer:
    return AccountTransfer(
        source_account=USD_ACCOUNT,
        destination_account=CUP_ACCOUNT,
        source_amount=Money("10.00", USD),
        destination_amount=(
            destination_amount
            if destination_amount is not None
            else Money("3200.00", CUP)
        ),
        transfer_date=NOW,
        exchange_rate=exchange_rate,
        **kwargs,
    )


def test_same_currency_transfer_preserves_the_amount() -> None:
    transfer = _same_currency_transfer()

    assert transfer.is_cross_currency is False
    assert transfer.source_amount == transfer.destination_amount


def test_same_currency_transfer_rejects_fx_or_amount_changes() -> None:
    with pytest.raises(InvalidTransferError):
        _same_currency_transfer(destination_amount="39.00")

    with pytest.raises(InvalidTransferError):
        _same_currency_transfer(exchange_rate=USD_CUP_RATE)


def test_cross_currency_transfer_requires_a_matching_rate_and_amount() -> None:
    transfer = _cross_currency_transfer()

    assert transfer.is_cross_currency is True
    assert transfer.destination_amount == Money("3200.00", CUP)

    with pytest.raises(InvalidTransferError):
        _cross_currency_transfer(exchange_rate=None)

    with pytest.raises(InvalidTransferError):
        _cross_currency_transfer(
            destination_amount=Money("3000.00", CUP)
        )


def test_cross_currency_transfer_rejects_a_reversed_rate() -> None:
    reversed_rate = ExchangeRate(
        base_currency=CUP,
        quote_currency=USD,
        rate=Decimal("0.003125"),
        source=ExchangeRateSource.MANUAL,
        rate_timestamp=NOW,
        id=11,
    )

    with pytest.raises(InvalidTransferError):
        AccountTransfer(
            source_account=USD_ACCOUNT,
            destination_account=CUP_ACCOUNT,
            source_amount=Money("10.00", USD),
            destination_amount=Money("0.03", CUP),
            transfer_date=NOW,
            exchange_rate=reversed_rate,
        )


def test_transfer_rejects_same_account_and_wrong_currency_amounts() -> None:
    with pytest.raises(InvalidTransferError):
        AccountTransfer(
            source_account=USD_ACCOUNT,
            destination_account=USD_ACCOUNT,
            source_amount=Money("10.00", USD),
            destination_amount=Money("10.00", USD),
            transfer_date=NOW,
        )

    with pytest.raises(AccountCurrencyMismatchError):
        AccountTransfer(
            source_account=USD_ACCOUNT,
            destination_account=OTHER_USD_ACCOUNT,
            source_amount=Money("10.00", CUP),
            destination_amount=Money("10.00", USD),
            transfer_date=NOW,
        )


def test_transfer_requires_persisted_accounts_and_positive_amounts() -> None:
    with pytest.raises(InvalidTransferError):
        AccountTransfer(
            source_account=Account(name="New", currency=USD),
            destination_account=OTHER_USD_ACCOUNT,
            source_amount=Money("10.00", USD),
            destination_amount=Money("10.00", USD),
            transfer_date=NOW,
        )

    with pytest.raises(InvalidTransferError):
        _same_currency_transfer(amount="0.00", destination_amount="0.00")
