"""Account/operation currency compatibility tests."""

from __future__ import annotations

import pytest

from app.domain.currency_rules import ensure_account_currency_matches
from app.domain.entities.currency import Currency
from app.domain.exceptions import AccountCurrencyMismatchError

USD = Currency(code="USD", name="US Dollar", decimal_places=2)
CUP = Currency(code="CUP", name="Cuban Peso", decimal_places=2)


def test_matching_account_currency_is_accepted() -> None:
    ensure_account_currency_matches(USD, USD)


def test_mismatched_account_currency_is_rejected() -> None:
    with pytest.raises(AccountCurrencyMismatchError) as exc_info:
        ensure_account_currency_matches(USD, CUP)

    message = str(exc_info.value)
    assert "USD" in message
    assert "CUP" in message
