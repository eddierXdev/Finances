"""Account transfer repository contract."""

from typing import Protocol

from app.domain.entities.account_transfer import AccountTransfer


class AccountTransferRepository(Protocol):
    """Append-only persistence boundary for account transfers."""

    def add(self, transfer: AccountTransfer) -> AccountTransfer:
        """Persist a transfer."""
        ...

    def get_by_id(self, transfer_id: int) -> AccountTransfer | None:
        """Return a transfer by identifier, if it exists."""
        ...

    def list_for_account(self, account_id: int) -> list[AccountTransfer]:
        """Return transfers involving an account, newest first."""
        ...
