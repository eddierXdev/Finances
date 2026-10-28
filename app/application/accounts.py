"""Shared application helpers for account-backed operations."""

from app.domain.entities.account import Account
from app.domain.exceptions import AccountNotFoundError, InactiveAccountError
from app.domain.repositories.account_repository import AccountRepository


def require_active_account(
    accounts: AccountRepository,
    account_id: int,
    *,
    label: str = "Account",
) -> Account:
    """Return an active account or raise a domain error."""
    account = accounts.get_by_id(account_id)
    if account is None:
        raise AccountNotFoundError(
            f"{label} {account_id} does not exist."
        )
    if not account.is_active:
        raise InactiveAccountError(
            f"{label} {account_id} is inactive."
        )
    return account
