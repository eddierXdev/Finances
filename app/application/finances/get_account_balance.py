"""Account-balance query use case."""

from app.domain.exceptions import AccountNotFoundError
from app.domain.repositories.account_repository import AccountRepository
from app.domain.repositories.financial_transaction_repository import (
    FinancialTransactionRepository,
)
from app.domain.value_objects.money import Money


class GetAccountBalance:
    """Derive an account balance from its signed ledger entries."""

    def __init__(
        self,
        accounts: AccountRepository,
        transactions: FinancialTransactionRepository,
    ) -> None:
        self._accounts = accounts
        self._transactions = transactions

    def execute(self, account_id: int) -> Money:
        account = self._accounts.get_by_id(account_id)
        if account is None:
            raise AccountNotFoundError(
                f"Account {account_id} does not exist."
            )
        return self._transactions.get_balance(account)
