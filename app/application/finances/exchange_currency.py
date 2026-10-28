"""Explicit cross-currency exchange use case."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.application.accounts import require_active_account
from app.domain.entities.account_transfer import AccountTransfer
from app.domain.entities.financial_transaction import FinancialTransaction
from app.domain.enums.financial_transaction_type import (
    FinancialTransactionType,
)
from app.domain.exceptions import (
    ExchangeRateNotFoundError,
    InvalidTransferError,
)
from app.domain.repositories.account_repository import AccountRepository
from app.domain.repositories.account_transfer_repository import (
    AccountTransferRepository,
)
from app.domain.repositories.exchange_rate_repository import (
    ExchangeRateRepository,
)
from app.domain.repositories.financial_transaction_repository import (
    FinancialTransactionRepository,
)
from app.domain.value_objects.money import Money


@dataclass(frozen=True, slots=True)
class ExchangeCurrencyRequest:
    """Input for an explicit cross-currency exchange."""

    source_account_id: int
    destination_account_id: int
    source_amount: Money
    exchange_rate_id: int
    transfer_date: datetime | None = None
    notes: str | None = None


class ExchangeCurrency:
    """Convert money between accounts using a historical exchange rate.

    The transfer and both signed ledger entries must be persisted inside one
    caller-managed transaction.
    """

    def __init__(
        self,
        accounts: AccountRepository,
        exchange_rates: ExchangeRateRepository,
        transfers: AccountTransferRepository,
        transactions: FinancialTransactionRepository,
    ) -> None:
        self._accounts = accounts
        self._exchange_rates = exchange_rates
        self._transfers = transfers
        self._transactions = transactions

    def execute(self, request: ExchangeCurrencyRequest) -> AccountTransfer:
        source = require_active_account(
            self._accounts, request.source_account_id, label="Source account"
        )
        destination = require_active_account(
            self._accounts,
            request.destination_account_id,
            label="Destination account",
        )

        if source.currency.code == destination.currency.code:
            raise InvalidTransferError(
                "Same-currency movements must use TransferMoney."
            )

        exchange_rate = self._exchange_rates.get_by_id(
            request.exchange_rate_id
        )
        if exchange_rate is None:
            raise ExchangeRateNotFoundError(
                f"Exchange rate {request.exchange_rate_id} does not exist."
            )
        if exchange_rate.id is None:
            raise RuntimeError("Persisted exchange rate has no identifier.")

        destination_amount = exchange_rate.convert(request.source_amount)
        transfer_date = request.transfer_date or datetime.now(UTC)

        stored = self._transfers.add(
            AccountTransfer(
                source_account=source,
                destination_account=destination,
                source_amount=request.source_amount,
                destination_amount=destination_amount,
                transfer_date=transfer_date,
                exchange_rate=exchange_rate,
                notes=request.notes,
            )
        )
        if stored.id is None:
            raise RuntimeError("Persisted transfer has no identifier.")

        self._transactions.add(
            FinancialTransaction(
                account=source,
                amount=-stored.source_amount,
                transaction_type=FinancialTransactionType.CURRENCY_EXCHANGE,
                transaction_date=stored.transfer_date,
                description=(
                    f"Exchange to {destination.name} at "
                    f"{exchange_rate.base_currency.code}/"
                    f"{exchange_rate.quote_currency.code}"
                ),
                account_transfer_id=stored.id,
                exchange_rate_id=exchange_rate.id,
            )
        )
        self._transactions.add(
            FinancialTransaction(
                account=destination,
                amount=stored.destination_amount,
                transaction_type=FinancialTransactionType.CURRENCY_EXCHANGE,
                transaction_date=stored.transfer_date,
                description=(
                    f"Exchange from {source.name} at "
                    f"{exchange_rate.base_currency.code}/"
                    f"{exchange_rate.quote_currency.code}"
                ),
                account_transfer_id=stored.id,
                exchange_rate_id=exchange_rate.id,
            )
        )
        return stored
