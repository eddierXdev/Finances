"""Account entity tests."""

from __future__ import annotations

import pytest

from app.domain.entities.account import Account
from app.domain.entities.currency import Currency

USD = Currency(code="USD", name="US Dollar", decimal_places=2)


def test_account_requires_a_name_and_currency() -> None:
    account = Account(name="  Cash USD  ", currency=USD, notes="  Main  ")

    assert account.name == "Cash USD"
    assert account.notes == "Main"
    assert account.is_active is True

    with pytest.raises(ValueError):
        Account(name="   ", currency=USD)

    with pytest.raises(TypeError):
        Account(name="Cash", currency="USD")  # type: ignore[arg-type]


def test_deactivation_returns_a_copy_and_preserves_history() -> None:
    account = Account(name="Cash USD", currency=USD, id=1)

    inactive = account.deactivate()

    assert inactive.is_active is False
    assert account.is_active is True
    assert inactive.id == account.id
    assert inactive.activate().is_active is True
