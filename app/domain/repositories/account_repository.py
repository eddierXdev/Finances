"""Account repository contract."""

from typing import Protocol

from app.domain.entities.account import Account


class AccountRepository(Protocol):
    """Persistence boundary for accounts."""

    def add(self, account: Account) -> Account:
        """Persist an account and return it with its identifier."""
        ...

    def save(self, account: Account) -> Account:
        """Update mutable account fields; the native currency is immutable."""
        ...

    def get_by_id(self, account_id: int) -> Account | None:
        """Return an account by identifier, if it exists."""
        ...

    def list_all(self, *, include_inactive: bool = False) -> list[Account]:
        """Return accounts, optionally including inactive ones."""
        ...
