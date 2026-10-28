"""Same-currency transfer use case."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.application.accounts import require_active_account
from app.domain.entities.account_transfer import AccountTransfer
from app.domain.entities.financial_transaction import FinancialTransaction
from app.domain.enums.financial_transaction_type import (
    FinancialTransactionType,
)
from app.domain.exceptions import InvalidTransferError
from app.domain.repositories.account_repository import AccountRepository
from app.domain.repositories.account_transfer_repository import (
    AccountTransferRepository,
)
from app.domain.repositories.financial_transaction_repository import (
    FinancialTransactionRepository,
)
from app.domain.value_objects.money import Money


@dataclass(frozen=True, slots=True)
class TransferMoneyRequest:
    """Input for a same-currency transfer."""

    source_account_id: int
    destination_account_id: int
    amount: Money
    transfer_date: datetime | None = None
    notes: str | None = None


class TransferMoney:
    """Move money between accounts with the same native currency.

    The transfer and both ledger entries must be persisted inside one
    caller-managed transaction.
    """

    def __init__(
        self,
        accounts: AccountRepository,
        transfers: AccountTransferRepository,
        transactions: FinancialTransactionRepository,
    ) -> None:
        self._accounts = accounts
        self._transfers = transfers
        self._transactions = transactions

    def execute(self, request: TransferMoneyRequest) -> AccountTransfer:
        source = require_active_account(
            self._accounts, request.source_account_id, label="Source account"
        )
        destination = require_active_account(
            self._accounts,
            request.destination_account_id,
            label="Destination account",
        )

        if source.currency.code != destination.currency.code:
            raise InvalidTransferError(
                "Cross-currency movements must use ExchangeCurrency."
            )

        transfer_date = request.transfer_date or datetime.now(UTC)
        stored = self._transfers.add(
            AccountTransfer(
                source_account=source,
                destination_account=destination,
                source_amount=request.amount,
                destination_amount=request.amount,
                transfer_date=transfer_date,
                notes=request.notes,
            )
        )
        if stored.id is None:
            raise RuntimeError("Persisted transfer has no identifier.")

        self._transactions.add(
            FinancialTransaction(
                account=source,
                amount=-stored.source_amount,
                transaction_type=FinancialTransactionType.TRANSFER,
                transaction_date=stored.transfer_date,
                description=f"Transfer to {destination.name}",
                account_transfer_id=stored.id,
            )
        )
        self._transactions.add(
            FinancialTransaction(
                account=destination,
                amount=stored.destination_amount,
                transaction_type=FinancialTransactionType.TRANSFER,
                transaction_date=stored.transfer_date,
                description=f"Transfer from {source.name}",
                account_transfer_id=stored.id,
            )
        )
        return stored
