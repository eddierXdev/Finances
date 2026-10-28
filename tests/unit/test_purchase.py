"""Purchase header and lifecycle rules."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.domain.entities.account import Account
from app.domain.entities.currency import Currency
from app.domain.entities.purchase import Purchase
from app.domain.enums.purchase_status import PurchaseStatus
from app.domain.exceptions import (
    AccountCurrencyMismatchError,
    InactiveAccountError,
    InvalidPurchaseError,
    InvalidPurchaseTransitionError,
    PurchasePaymentError,
)

USD = Currency(code="USD", name="US Dollar", decimal_places=2, id=1)
EUR = Currency(code="EUR", name="Euro", decimal_places=2, id=2)
USD_ACCOUNT = Account(name="Cash USD", currency=USD, id=1)
EUR_ACCOUNT = Account(name="Cash EUR", currency=EUR, id=2)
NOW = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)


def _purchase(**kwargs) -> Purchase:
    return Purchase(
        currency=USD,
        purchase_date=NOW,
        **kwargs,
    )


def test_pending_purchase_has_no_account_and_normalizes_text() -> None:
    purchase = _purchase(
        order_number="  ORDER-1 ",
        tracking_number="  TRACK-1 ",
        notes="  Check customs ",
    )

    assert purchase.status is PurchaseStatus.PENDING
    assert purchase.account is None
    assert purchase.order_number == "ORDER-1"
    assert purchase.tracking_number == "TRACK-1"
    assert purchase.notes == "Check customs"


def test_paid_status_requires_a_matching_active_account() -> None:
    with pytest.raises(InvalidPurchaseError):
        _purchase(status=PurchaseStatus.PURCHASED)

    with pytest.raises(AccountCurrencyMismatchError):
        _purchase(status=PurchaseStatus.PURCHASED, account=EUR_ACCOUNT)

    inactive = Account(
        name="Cash USD", currency=USD, is_active=False, id=3
    )
    purchase = _purchase(
        status=PurchaseStatus.PURCHASED, account=inactive
    )
    assert purchase.account_id == 3


def test_pending_purchase_cannot_already_have_an_account() -> None:
    with pytest.raises(InvalidPurchaseError):
        _purchase(account=USD_ACCOUNT)


def test_register_payment_returns_a_paid_copy() -> None:
    purchase = _purchase()

    paid = purchase.register_payment(USD_ACCOUNT)

    assert paid.status is PurchaseStatus.PURCHASED
    assert paid.account == USD_ACCOUNT
    assert paid.id == purchase.id
    assert purchase.status is PurchaseStatus.PENDING
    assert purchase.account is None


def test_register_payment_rejects_invalid_state_and_account() -> None:
    with pytest.raises(PurchasePaymentError):
        _purchase(
            status=PurchaseStatus.PURCHASED, account=USD_ACCOUNT
        ).register_payment(USD_ACCOUNT)

    inactive = Account(
        name="Cash USD", currency=USD, is_active=False, id=3
    )
    with pytest.raises(InactiveAccountError):
        _purchase().register_payment(inactive)

    with pytest.raises(AccountCurrencyMismatchError):
        _purchase().register_payment(EUR_ACCOUNT)


def test_logistics_transitions_follow_the_state_machine() -> None:
    paid = _purchase().register_payment(USD_ACCOUNT)

    shipped = paid.transition_to(PurchaseStatus.SHIPPED)
    in_transit = shipped.transition_to(PurchaseStatus.IN_TRANSIT)
    received = in_transit.transition_to(PurchaseStatus.RECEIVED)

    assert shipped.status is PurchaseStatus.SHIPPED
    assert in_transit.status is PurchaseStatus.IN_TRANSIT
    assert received.status is PurchaseStatus.RECEIVED
    with pytest.raises(InvalidPurchaseTransitionError):
        received.transition_to(PurchaseStatus.SHIPPED)


def test_pending_can_be_cancelled_but_paid_purchases_cannot() -> None:
    cancelled = _purchase().transition_to(PurchaseStatus.CANCELLED)
    assert cancelled.status is PurchaseStatus.CANCELLED

    paid = _purchase().register_payment(USD_ACCOUNT)
    with pytest.raises(InvalidPurchaseTransitionError):
        paid.transition_to(PurchaseStatus.CANCELLED)


def test_skipping_logistics_steps_is_rejected() -> None:
    with pytest.raises(InvalidPurchaseTransitionError):
        _purchase().transition_to(PurchaseStatus.SHIPPED)

    in_transit = (
        _purchase()
        .register_payment(USD_ACCOUNT)
        .transition_to(PurchaseStatus.IN_TRANSIT)
    )
    partially = in_transit.transition_to(
        PurchaseStatus.PARTIALLY_RECEIVED
    )
    assert partially.transition_to(
        PurchaseStatus.RECEIVED
    ).status is PurchaseStatus.RECEIVED


def test_purchase_date_must_be_timezone_aware() -> None:
    with pytest.raises(InvalidPurchaseError):
        Purchase(
            currency=USD,
            purchase_date=datetime(2026, 10, 27, 12, 0),
        )
