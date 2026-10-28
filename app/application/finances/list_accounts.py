"""Account list query with native-currency balances."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.repositories.account_repository import AccountRepository
from app.domain.repositories.financial_transaction_repository import (
    FinancialTransactionRepository,
)
from app.domain.value_objects.money import Money


@dataclass(frozen=True, slots=True)
class AccountListItem:
    """One account row ready for presentation."""

    account_id: int
    name: str
    account_type: str | None
    currency_code: str
    balance: Money
    is_active: bool
    notes: str | None


class ListAccounts:
    """Return accounts with balances derived from their native ledgers."""

    def __init__(
        self,
        accounts: AccountRepository,
        transactions: FinancialTransactionRepository,
    ) -> None:
        self._accounts = accounts
        self._transactions = transactions

    def execute(
        self, *, include_inactive: bool = False
    ) -> tuple[AccountListItem, ...]:
        rows: list[AccountListItem] = []
        for account in self._accounts.list_all(
            include_inactive=include_inactive
        ):
            if account.id is None:
                raise RuntimeError("Stored account has no identifier.")

            rows.append(
                AccountListItem(
                    account_id=account.id,
                    name=account.name,
                    account_type=account.account_type,
                    currency_code=account.currency.code,
                    balance=self._transactions.get_balance(account),
                    is_active=account.is_active,
                    notes=account.notes,
                )
            )
        return tuple(rows)
