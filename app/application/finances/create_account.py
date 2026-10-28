"""Create-account use case."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.entities.account import Account
from app.domain.entities.currency import Currency
from app.domain.repositories.account_repository import AccountRepository


@dataclass(frozen=True, slots=True)
class CreateAccountRequest:
    """Input for account creation."""

    name: str
    currency: Currency
    account_type: str | None = None
    notes: str | None = None


class CreateAccount:
    """Create an account with one native currency."""

    def __init__(self, accounts: AccountRepository) -> None:
        self._accounts = accounts

    def execute(self, request: CreateAccountRequest) -> Account:
        return self._accounts.add(
            Account(
                name=request.name,
                currency=request.currency,
                account_type=request.account_type,
                notes=request.notes,
            )
        )
