"""Application service for the Accounts screen."""

from __future__ import annotations

from app.application.finances.create_account import (
    CreateAccount,
    CreateAccountRequest,
)
from app.application.finances.list_accounts import (
    AccountListItem,
    ListAccounts,
)
from app.application.finances.set_account_active import SetAccountActive
from app.application.unit_of_work import UnitOfWorkFactory
from app.domain.entities.account import Account
from app.domain.entities.currency import Currency


class AccountService:
    """Read and write accounts with explicit transaction boundaries."""

    def __init__(self, unit_of_work: UnitOfWorkFactory) -> None:
        self._unit_of_work = unit_of_work

    def list_accounts(
        self, *, include_inactive: bool = False
    ) -> tuple[AccountListItem, ...]:
        with self._unit_of_work.unit_of_work() as uow:
            return ListAccounts(
                uow.accounts,
                uow.transactions,
            ).execute(include_inactive=include_inactive)

    def create_account(self, request: CreateAccountRequest) -> Account:
        with self._unit_of_work.unit_of_work() as uow:
            account = CreateAccount(uow.accounts).execute(request)
            uow.commit()
            return account

    def set_account_active(
        self, account_id: int, *, is_active: bool
    ) -> Account:
        with self._unit_of_work.unit_of_work() as uow:
            account = SetAccountActive(uow.accounts).execute(
                account_id, is_active=is_active
            )
            uow.commit()
            return account

    def list_enabled_currencies(self) -> tuple[Currency, ...]:
        with self._unit_of_work.unit_of_work() as uow:
            return tuple(uow.currencies.list_all(enabled_only=True))
