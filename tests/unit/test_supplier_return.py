"""Supplier return header rules."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.domain.entities.account import Account
from app.domain.entities.currency import Currency
from app.domain.entities.purchase import Purchase
from app.domain.entities.supplier_return import SupplierReturn
from app.domain.enums.purchase_status import PurchaseStatus
from app.domain.exceptions import (
    AccountCurrencyMismatchError,
    InvalidSupplierReturnError,
    PurchaseCurrencyMismatchError,
    SupplierRefundError,
)
from app.domain.value_objects.money import Money

USD = Currency(code="USD", name="US Dollar", decimal_places=2, id=1)
EUR = Currency(code="EUR", name="Euro", decimal_places=2, id=2)
USD_ACCOUNT = Account(name="Cash USD", currency=USD, id=1)
EUR_ACCOUNT = Account(name="Cash EUR", currency=EUR, id=2)
INACTIVE_ACCOUNT = Account(
    name="Closed USD", currency=USD, is_active=False, id=3
)
NOW = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)
PURCHASE = Purchase(
    currency=USD,
    purchase_date=NOW,
    supplier_id=99,
    account=USD_ACCOUNT,
    status=PurchaseStatus.RECEIVED,
    id=10,
)
PURCHASE_WITHOUT_SUPPLIER = Purchase(
    currency=USD,
    purchase_date=NOW,
    account=USD_ACCOUNT,
    status=PurchaseStatus.RECEIVED,
    id=11,
)


def _return(**kwargs) -> SupplierReturn:
    values = {
        "purchase": PURCHASE,
        "return_date": NOW,
    }
    values.update(kwargs)
    return SupplierReturn(**values)


def test_supplier_return_defaults_to_no_refund_and_normalizes_text() -> None:
    returned = _return(notes="  damaged box ")

    assert returned.purchase is PURCHASE
    assert returned.purchase_id == PURCHASE.id
    assert returned.return_date == NOW
    assert returned.supplier_id is None
    assert returned.account is None
    assert returned.account_id is None
    assert returned.refund_amount is None
    assert returned.notes == "damaged box"
    assert returned.id is None
    assert returned.has_refund is False


def test_supplier_return_can_reference_the_original_supplier() -> None:
    returned = _return(supplier_id=PURCHASE.supplier_id)

    assert returned.supplier_id == PURCHASE.supplier_id


def test_supplier_return_supplier_must_match_the_purchase() -> None:
    with pytest.raises(InvalidSupplierReturnError):
        _return(supplier_id=100)

    with pytest.raises(InvalidSupplierReturnError):
        _return(purchase=PURCHASE_WITHOUT_SUPPLIER, supplier_id=99)


def test_supplier_return_requires_a_persisted_purchase() -> None:
    unpersisted = Purchase(
        currency=USD,
        purchase_date=NOW,
        account=USD_ACCOUNT,
        status=PurchaseStatus.RECEIVED,
    )

    with pytest.raises(InvalidSupplierReturnError):
        _return(purchase=unpersisted)

    with pytest.raises(TypeError):
        _return(purchase="purchase")


def test_return_date_must_be_timezone_aware_and_is_normalized_to_utc() -> None:
    local_time = datetime(
        2026, 10, 27, 7, 0, tzinfo=timezone(timedelta(hours=-5))
    )

    assert _return(return_date=local_time).return_date == NOW
    with pytest.raises(InvalidSupplierReturnError):
        _return(return_date=datetime(2026, 10, 27, 12, 0))
    with pytest.raises(TypeError):
        _return(return_date="2026-10-27")


def test_refund_requires_a_persisted_account_in_purchase_currency() -> None:
    returned = _return(
        account=USD_ACCOUNT,
        refund_amount=Money("10", USD),
    )

    assert returned.account is USD_ACCOUNT
    assert returned.account_id == USD_ACCOUNT.id
    assert returned.refund_amount == Money("10", USD)
    assert returned.has_refund is True

    with pytest.raises(InvalidSupplierReturnError):
        _return(
            account=Account(name="Cash USD", currency=USD),
            refund_amount=Money("10", USD),
        )
    with pytest.raises(AccountCurrencyMismatchError):
        _return(
            account=EUR_ACCOUNT,
            refund_amount=Money("10", USD),
        )
    with pytest.raises(PurchaseCurrencyMismatchError):
        _return(
            account=USD_ACCOUNT,
            refund_amount=Money("10", EUR),
        )


def test_historical_return_can_map_an_inactive_refund_account() -> None:
    returned = _return(
        account=INACTIVE_ACCOUNT,
        refund_amount=Money("10", USD),
    )

    assert returned.account is INACTIVE_ACCOUNT
    assert returned.account.is_active is False


def test_refund_amount_must_be_positive_money() -> None:
    for amount in ("0", "-1"):
        with pytest.raises(SupplierRefundError):
            _return(
                account=USD_ACCOUNT,
                refund_amount=Money(amount, USD),
            )

    with pytest.raises(TypeError):
        _return(account=USD_ACCOUNT, refund_amount="10")


def test_refund_account_and_amount_must_be_provided_together() -> None:
    with pytest.raises(InvalidSupplierReturnError):
        _return(account=USD_ACCOUNT)

    with pytest.raises(InvalidSupplierReturnError):
        _return(refund_amount=Money("10", USD))


def test_supplier_return_id_must_be_a_positive_integer_when_present() -> None:
    assert _return(id=1).id == 1

    for return_id in (0, -1, True, "1"):
        with pytest.raises(ValueError):
            _return(id=return_id)
