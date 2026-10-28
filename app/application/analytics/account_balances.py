"""Native account balances use case."""

from __future__ import annotations

from datetime import UTC, datetime

from app.application.analytics.calculations import (
    add_money,
    totals_tuple,
)
from app.application.analytics.models import (
    AccountBalance,
    AccountBalancesReport,
    AnalyticsFilters,
)
from app.domain.repositories.account_repository import AccountRepository
from app.domain.repositories.financial_transaction_repository import (
    FinancialTransactionRepository,
)
from app.domain.value_objects.money import Money


class GetAccountBalances:
    """Return every account's native ledger balance at a cutoff."""

    def __init__(
        self,
        accounts: AccountRepository,
        transactions: FinancialTransactionRepository,
        *,
        clock=None,
    ) -> None:
        self._accounts = accounts
        self._transactions = transactions
        self._clock = clock or (lambda: datetime.now(UTC))

    def execute(
        self,
        as_of: datetime | None = None,
        filters: AnalyticsFilters | None = None,
    ) -> AccountBalancesReport:
        filters = filters or AnalyticsFilters()
        cutoff = as_of or self._clock()
        if cutoff.tzinfo is None or cutoff.utcoffset() is None:
            raise ValueError("Account-balance as_of must be timezone-aware.")
        cutoff = cutoff.astimezone(UTC)

        balances: list[AccountBalance] = []
        totals: dict[str, Money] = {}

        for account in self._accounts.list_all(include_inactive=True):
            if account.id is None:
                continue
            if (
                filters.account_id is not None
                and account.id != filters.account_id
            ):
                continue
            if (
                filters.currency_code is not None
                and account.currency.code != filters.currency_code
            ):
                continue

            balance = Money.zero(account.currency)
            for entry in self._transactions.list_for_account(
                account.id, end=cutoff
            ):
                balance = balance + entry.amount

            balances.append(
                AccountBalance(
                    account_id=account.id,
                    account_name=account.name,
                    currency=account.currency,
                    balance=balance,
                    is_active=account.is_active,
                )
            )
            add_money(totals, balance)

        return AccountBalancesReport(
            as_of=cutoff,
            accounts=tuple(balances),
            totals=totals_tuple(totals),
        )
