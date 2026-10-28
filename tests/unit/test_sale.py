"""Sale header and lifecycle rules."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.domain.entities.account import Account
from app.domain.entities.currency import Currency
from app.domain.entities.sale import Sale
from app.domain.enums.sale_status import SaleStatus
from app.domain.exceptions import (
    AccountCurrencyMismatchError,
    InvalidSaleError,
    InvalidSaleTransitionError,
    SaleCurrencyMismatchError,
)
from app.domain.value_objects.money import Money

USD = Currency(code="USD", name="US Dollar", decimal_places=2, id=1)
EUR = Currency(code="EUR", name="Euro", decimal_places=2, id=2)
USD_ACCOUNT = Account(name="Cash USD", currency=USD, id=1)
EUR_ACCOUNT = Account(name="Cash EUR", currency=EUR, id=2)
NOW = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)


def _sale(**kwargs) -> Sale:
    values = {
        "account": USD_ACCOUNT,
        "currency": USD,
        "sale_date": NOW,
    }
    values.update(kwargs)
    return Sale(**values)


def test_sale_defaults_to_completed_and_normalizes_text() -> None:
    sale = _sale(notes="  Counter sale ")

    assert sale.status is SaleStatus.COMPLETED
    assert sale.customer_id is None
    assert sale.discount_amount is None
    assert sale.notes == "Counter sale"


def test_sale_account_must_be_persisted_and_match_the_sale_currency() -> None:
    with pytest.raises(InvalidSaleError):
        _sale(account=Account(name="Cash USD", currency=USD))

    with pytest.raises(AccountCurrencyMismatchError):
        _sale(account=EUR_ACCOUNT)

    assert _sale(account=USD_ACCOUNT).account is USD_ACCOUNT


def test_sale_date_must_be_timezone_aware_and_is_normalized_to_utc() -> None:
    local_time = datetime(
        2026, 10, 27, 7, 0, tzinfo=timezone(timedelta(hours=-5))
    )

    sale = _sale(sale_date=local_time)

    assert sale.sale_date == NOW
    assert sale.sale_date.tzinfo is UTC
    with pytest.raises(InvalidSaleError):
        _sale(sale_date=datetime(2026, 10, 27, 12, 0))


def test_sale_discount_must_be_non_negative_money_in_sale_currency() -> None:
    assert _sale(discount_amount=Money("2", USD)).discount_amount == Money(
        "2", USD
    )

    with pytest.raises(InvalidSaleError):
        _sale(discount_amount=Money("-1", USD))
    with pytest.raises(SaleCurrencyMismatchError):
        _sale(discount_amount=Money("1", EUR))
    with pytest.raises(TypeError):
        _sale(discount_amount="1")


def test_customer_id_must_be_a_positive_integer_when_present() -> None:
    assert _sale(customer_id=3).customer_id == 3

    for customer_id in (0, -1, True, "3"):
        with pytest.raises(InvalidSaleError):
            _sale(customer_id=customer_id)


def test_status_must_be_a_sale_status() -> None:
    assert _sale(status=SaleStatus.REFUNDED).status is SaleStatus.REFUNDED

    with pytest.raises(TypeError):
        _sale(status="COMPLETED")


def test_sale_id_must_be_a_positive_integer_when_present() -> None:
    assert _sale(id=1).id == 1

    for sale_id in (0, -1, True, "1"):
        with pytest.raises(ValueError):
            _sale(id=sale_id)


def test_sale_status_transitions_follow_the_refund_flow() -> None:
    completed = _sale()
    partially_refunded = completed.transition_to(
        SaleStatus.PARTIALLY_REFUNDED
    )
    refunded = partially_refunded.transition_to(SaleStatus.REFUNDED)

    assert completed.status is SaleStatus.COMPLETED
    assert partially_refunded.status is SaleStatus.PARTIALLY_REFUNDED
    assert refunded.status is SaleStatus.REFUNDED
    assert refunded.id == completed.id

    assert (
        completed.transition_to(SaleStatus.REFUNDED).status
        is SaleStatus.REFUNDED
    )


def test_sale_status_transitions_reject_skipped_or_backwards_steps() -> None:
    completed = _sale()
    refunded = _sale(status=SaleStatus.REFUNDED)
    cancelled = _sale(status=SaleStatus.CANCELLED)

    for sale, target in (
        (completed, SaleStatus.COMPLETED),
        (completed, SaleStatus.CANCELLED),
        (refunded, SaleStatus.PARTIALLY_REFUNDED),
        (refunded, SaleStatus.REFUNDED),
        (cancelled, SaleStatus.PARTIALLY_REFUNDED),
    ):
        with pytest.raises(InvalidSaleTransitionError):
            sale.transition_to(target)

    with pytest.raises(TypeError):
        completed.transition_to("REFUNDED")
