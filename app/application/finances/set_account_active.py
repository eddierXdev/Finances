"""Account activation use case."""

from __future__ import annotations

from app.domain.entities.account import Account
from app.domain.exceptions import AccountNotFoundError
from app.domain.repositories.account_repository import AccountRepository


class SetAccountActive:
    """Activate or deactivate an account without deleting its history."""

    def __init__(self, accounts: AccountRepository) -> None:
        self._accounts = accounts

    def execute(self, account_id: int, *, is_active: bool) -> Account:
        if not isinstance(is_active, bool):
            raise TypeError("is_active must be a boolean.")

        existing = self._accounts.get_by_id(account_id)
        if existing is None:
            raise AccountNotFoundError(
                f"Account {account_id} does not exist."
            )

        updated = existing.activate() if is_active else existing.deactivate()
        return self._accounts.save(updated)
