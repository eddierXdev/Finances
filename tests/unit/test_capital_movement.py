"""Capital movement entity tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.domain.entities.account import Account
from app.domain.entities.capital_movement import CapitalMovement
from app.domain.entities.currency import Currency
from app.domain.enums.capital_movement_type import CapitalMovementType
from app.domain.exceptions import AccountCurrencyMismatchError
from app.domain.value_objects.money import Money

USD = Currency(code="USD", name="US Dollar", decimal_places=2)
CUP = Currency(code="CUP", name="Cuban Peso", decimal_places=2)
ACCOUNT = Account(name="Cash USD", currency=USD, id=1)
NOW = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)


def _movement(
    movement_type: CapitalMovementType,
    amount: str = "100.00",
    *,
    currency: Currency = USD,
) -> CapitalMovement:
    return CapitalMovement(
        account=ACCOUNT,
        movement_type=movement_type,
        amount=Money(amount, currency),
        movement_date=NOW,
    )


def test_capital_history_stores_positive_amounts_and_derives_the_sign() -> None:
    contribution = _movement(CapitalMovementType.CONTRIBUTION)
    withdrawal = _movement(CapitalMovementType.WITHDRAWAL)

    assert contribution.amount == Money("100.00", USD)
    assert contribution.signed_amount == Money("100.00", USD)
    assert withdrawal.amount == Money("100.00", USD)
    assert withdrawal.signed_amount == Money("-100.00", USD)


def test_capital_rejects_non_positive_amounts_and_wrong_currency() -> None:
    with pytest.raises(ValueError):
        _movement(CapitalMovementType.CONTRIBUTION, "-1.00")

    with pytest.raises(ValueError):
        _movement(CapitalMovementType.CONTRIBUTION, "0.00")

    with pytest.raises(AccountCurrencyMismatchError):
        _movement(
            CapitalMovementType.CONTRIBUTION,
            "10.00",
            currency=CUP,
        )
