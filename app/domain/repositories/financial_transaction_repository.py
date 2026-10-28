"""Financial transaction repository contract."""

from datetime import datetime
from typing import Protocol

from app.domain.entities.account import Account
from app.domain.entities.financial_transaction import FinancialTransaction
from app.domain.value_objects.money import Money


class FinancialTransactionRepository(Protocol):
    """Persistence boundary for signed ledger entries."""

    def add(
        self, transaction: FinancialTransaction
    ) -> FinancialTransaction:
        """Persist a ledger entry."""
        ...

    def get_by_id(
        self, transaction_id: int
    ) -> FinancialTransaction | None:
        """Return a ledger entry by identifier, if it exists."""
        ...

    def list_for_account(
        self,
        account_id: int,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[FinancialTransaction]:
        """Return an account's ledger entries, oldest first."""
        ...

    def get_balance(self, account: Account) -> Money:
        """Derive the account balance by summing signed amounts."""
        ...
