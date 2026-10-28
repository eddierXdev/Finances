"""Financial transaction sign and compatibility rules."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.domain.entities.account import Account
from app.domain.entities.currency import Currency
from app.domain.entities.financial_transaction import FinancialTransaction
from app.domain.enums.financial_transaction_type import (
    FinancialTransactionType,
)
from app.domain.exceptions import (
    AccountCurrencyMismatchError,
    InvalidLedgerEntryError,
)
from app.domain.value_objects.money import Money

USD = Currency(code="USD", name="US Dollar", decimal_places=2)
CUP = Currency(code="CUP", name="Cuban Peso", decimal_places=2)
NOW = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)
ACCOUNT = Account(name="Cash USD", currency=USD, id=1)


def _transaction(
    transaction_type: FinancialTransactionType,
    amount: str,
    *,
    currency: Currency = USD,
    **kwargs,
) -> FinancialTransaction:
    return FinancialTransaction(
        account=ACCOUNT,
        amount=Money(amount, currency),
        transaction_type=transaction_type,
        transaction_date=NOW,
        **kwargs,
    )


def test_inflows_are_positive_and_outflows_are_negative() -> None:
    contribution = _transaction(
        FinancialTransactionType.CAPITAL_CONTRIBUTION, "100.00"
    )
    withdrawal = _transaction(
        FinancialTransactionType.CAPITAL_WITHDRAWAL, "-40.00"
    )

    assert contribution.amount == Money("100.00", USD)
    assert withdrawal.amount == Money("-40.00", USD)


@pytest.mark.parametrize(
    ("transaction_type", "amount"),
    [
        (FinancialTransactionType.SALE, "-1.00"),
        (FinancialTransactionType.SUPPLIER_REFUND, "-1.00"),
        (FinancialTransactionType.PURCHASE, "1.00"),
        (FinancialTransactionType.EXPENSE, "1.00"),
        (FinancialTransactionType.CUSTOMER_REFUND, "1.00"),
        (FinancialTransactionType.CAPITAL_CONTRIBUTION, "-1.00"),
        (FinancialTransactionType.CAPITAL_WITHDRAWAL, "1.00"),
    ],
)
def test_fixed_direction_types_reject_wrong_signs(
    transaction_type: FinancialTransactionType, amount: str
) -> None:
    with pytest.raises(InvalidLedgerEntryError):
        _transaction(transaction_type, amount)


def test_transfer_and_exchange_accept_either_sign() -> None:
    for transaction_type in (
        FinancialTransactionType.TRANSFER,
        FinancialTransactionType.CURRENCY_EXCHANGE,
        FinancialTransactionType.ADJUSTMENT,
    ):
        assert _transaction(transaction_type, "5.00").amount.amount > 0
        assert _transaction(transaction_type, "-5.00").amount.amount < 0


def test_transaction_currency_must_match_the_account() -> None:
    with pytest.raises(AccountCurrencyMismatchError):
        _transaction(
            FinancialTransactionType.CAPITAL_CONTRIBUTION,
            "10.00",
            currency=CUP,
        )


def test_zero_and_naive_transactions_are_rejected() -> None:
    with pytest.raises(InvalidLedgerEntryError):
        _transaction(FinancialTransactionType.ADJUSTMENT, "0.00")

    with pytest.raises(InvalidLedgerEntryError):
        FinancialTransaction(
            account=ACCOUNT,
            amount=Money("10.00", USD),
            transaction_type=FinancialTransactionType.ADJUSTMENT,
            transaction_date=datetime(2026, 10, 27, 12, 0),
        )


def test_a_transaction_can_reference_at_most_one_business_source() -> None:
    with pytest.raises(InvalidLedgerEntryError):
        _transaction(
            FinancialTransactionType.CAPITAL_CONTRIBUTION,
            "10.00",
            capital_movement_id=1,
            account_transfer_id=2,
        )


@pytest.mark.parametrize(
    "other_source",
    [{"capital_movement_id": 1}, {"account_transfer_id": 2}],
)
def test_purchase_is_an_exclusive_business_source(
    other_source: dict[str, int],
) -> None:
    with pytest.raises(InvalidLedgerEntryError):
        _transaction(
            FinancialTransactionType.PURCHASE,
            "-10.00",
            purchase_id=3,
            **other_source,
        )


@pytest.mark.parametrize(
    "other_source",
    [
        {"purchase_id": 3},
        {"capital_movement_id": 1},
        {"account_transfer_id": 2},
    ],
)
def test_sale_is_an_exclusive_business_source(
    other_source: dict[str, int],
) -> None:
    with pytest.raises(InvalidLedgerEntryError):
        _transaction(
            FinancialTransactionType.SALE,
            "10.00",
            sale_id=4,
            **other_source,
        )


def test_sale_source_id_must_be_positive() -> None:
    for sale_id in (0, -1, True, "4"):
        with pytest.raises(InvalidLedgerEntryError):
            _transaction(
                FinancialTransactionType.SALE,
                "10.00",
                sale_id=sale_id,
            )


def test_customer_return_is_an_exclusive_business_source() -> None:
    transaction = _transaction(
        FinancialTransactionType.CUSTOMER_REFUND,
        "-10.00",
        customer_return_id=5,
    )
    assert transaction.customer_return_id == 5

    for other_source in (
        {"purchase_id": 3},
        {"sale_id": 4},
        {"expense_id": 7},
        {"capital_movement_id": 1},
        {"account_transfer_id": 2},
    ):
        with pytest.raises(InvalidLedgerEntryError):
            _transaction(
                FinancialTransactionType.CUSTOMER_REFUND,
                "-10.00",
                customer_return_id=5,
                **other_source,
            )


def test_customer_return_source_id_must_be_positive() -> None:
    for return_id in (0, -1, True, "5"):
        with pytest.raises(InvalidLedgerEntryError):
            _transaction(
                FinancialTransactionType.CUSTOMER_REFUND,
                "-10.00",
                customer_return_id=return_id,
            )


def test_supplier_return_is_an_exclusive_business_source() -> None:
    transaction = _transaction(
        FinancialTransactionType.SUPPLIER_REFUND,
        "10.00",
        supplier_return_id=6,
    )
    assert transaction.supplier_return_id == 6

    for other_source in (
        {"purchase_id": 3},
        {"sale_id": 4},
        {"expense_id": 7},
        {"customer_return_id": 5},
        {"capital_movement_id": 1},
        {"account_transfer_id": 2},
    ):
        with pytest.raises(InvalidLedgerEntryError):
            _transaction(
                FinancialTransactionType.SUPPLIER_REFUND,
                "10.00",
                supplier_return_id=6,
                **other_source,
            )


def test_supplier_return_source_id_must_be_positive() -> None:
    for return_id in (0, -1, True, "6"):
        with pytest.raises(InvalidLedgerEntryError):
            _transaction(
                FinancialTransactionType.SUPPLIER_REFUND,
                "10.00",
                supplier_return_id=return_id,
            )


def test_expense_is_an_exclusive_business_source() -> None:
    transaction = _transaction(
        FinancialTransactionType.EXPENSE,
        "-10.00",
        expense_id=7,
    )
    assert transaction.expense_id == 7

    for other_source in (
        {"purchase_id": 3},
        {"sale_id": 4},
        {"customer_return_id": 5},
        {"supplier_return_id": 6},
        {"capital_movement_id": 1},
        {"account_transfer_id": 2},
    ):
        with pytest.raises(InvalidLedgerEntryError):
            _transaction(
                FinancialTransactionType.EXPENSE,
                "-10.00",
                expense_id=7,
                **other_source,
            )


def test_expense_source_id_must_be_positive() -> None:
    for expense_id in (0, -1, True, "7"):
        with pytest.raises(InvalidLedgerEntryError):
            _transaction(
                FinancialTransactionType.EXPENSE,
                "-10.00",
                expense_id=expense_id,
            )


def test_description_is_trimmed() -> None:
    transaction = _transaction(
        FinancialTransactionType.ADJUSTMENT,
        "1.00",
        description="  Correction  ",
    )

    assert transaction.description == "Correction"
