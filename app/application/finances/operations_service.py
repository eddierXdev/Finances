"""Application service for expenses, capital and account movements."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.application.finances.capital import (
    AddCapital,
    CapitalMovementRequest,
    WithdrawCapital,
)
from app.application.finances.exchange_currency import (
    ExchangeCurrency,
    ExchangeCurrencyRequest,
)
from app.application.finances.register_expense import (
    RegisterExpense,
    RegisterExpenseRequest,
)
from app.application.finances.transfer_money import (
    TransferMoney,
    TransferMoneyRequest,
)
from app.application.unit_of_work import UnitOfWorkFactory
from app.domain.entities.account import Account
from app.domain.entities.account_transfer import AccountTransfer
from app.domain.entities.capital_movement import CapitalMovement
from app.domain.entities.currency import Currency
from app.domain.entities.exchange_rate import ExchangeRate
from app.domain.entities.expense import Expense
from app.domain.enums.capital_movement_type import CapitalMovementType
from app.domain.enums.expense_type import ExpenseType
from app.domain.value_objects.money import Money


@dataclass(frozen=True, slots=True)
class ExpenseRow:
    """An operating expense ready for display."""

    expense_id: int
    expense_date: datetime
    expense_type: ExpenseType
    amount: Money
    account_name: str
    description: str | None
    notes: str | None


@dataclass(frozen=True, slots=True)
class CapitalRow:
    """A capital contribution or withdrawal ready for display."""

    movement_id: int
    movement_date: datetime
    movement_type: CapitalMovementType
    amount: Money
    account_name: str
    notes: str | None


@dataclass(frozen=True, slots=True)
class TransferRow:
    """An account transfer or currency exchange."""

    transfer_id: int
    transfer_date: datetime
    source_account: str
    destination_account: str
    source_amount: Money
    destination_amount: Money
    is_cross_currency: bool
    notes: str | None


class FinanceOperationsService:
    """Read finance history and run expense/capital/transfer use cases."""

    def __init__(self, unit_of_work: UnitOfWorkFactory) -> None:
        self._unit_of_work = unit_of_work

    def list_expenses(self) -> tuple[ExpenseRow, ...]:
        with self._unit_of_work.unit_of_work() as uow:
            return tuple(
                _expense_row(expense) for expense in uow.expenses.list_all()
            )

    def list_capital_movements(self) -> tuple[CapitalRow, ...]:
        with self._unit_of_work.unit_of_work() as uow:
            rows: list[CapitalRow] = []
            for account in uow.accounts.list_all(include_inactive=True):
                if account.id is None:
                    continue
                for movement in uow.capital_movements.list_for_account(
                    account.id
                ):
                    rows.append(_capital_row(movement, account))
            rows.sort(
                key=lambda row: (
                    row.movement_date,
                    row.movement_id,
                ),
                reverse=True,
            )
            return tuple(rows)

    def list_transfers(self) -> tuple[TransferRow, ...]:
        with self._unit_of_work.unit_of_work() as uow:
            seen: set[int] = set()
            rows: list[TransferRow] = []
            for account in uow.accounts.list_all(include_inactive=True):
                if account.id is None:
                    continue
                for transfer in uow.transfers.list_for_account(account.id):
                    if transfer.id is None or transfer.id in seen:
                        continue
                    seen.add(transfer.id)
                    rows.append(_transfer_row(transfer))
            rows.sort(
                key=lambda row: (row.transfer_date, row.transfer_id),
                reverse=True,
            )
            return tuple(rows)

    def list_accounts(
        self, *, include_inactive: bool = False
    ) -> tuple[Account, ...]:
        with self._unit_of_work.unit_of_work() as uow:
            return tuple(
                uow.accounts.list_all(include_inactive=include_inactive)
            )

    def list_enabled_currencies(self) -> tuple[Currency, ...]:
        with self._unit_of_work.unit_of_work() as uow:
            return tuple(uow.currencies.list_all(enabled_only=True))

    def list_exchange_rates(
        self, base_code: str, quote_code: str
    ) -> tuple[ExchangeRate, ...]:
        with self._unit_of_work.unit_of_work() as uow:
            return tuple(
                uow.exchange_rates.list_for_pair(base_code, quote_code)
            )

    def register_expense(self, request: RegisterExpenseRequest) -> Expense:
        with self._unit_of_work.unit_of_work() as uow:
            expense = RegisterExpense(
                accounts=uow.accounts,
                expenses=uow.expenses,
                transactions=uow.transactions,
            ).execute(request)
            uow.commit()
            return expense

    def add_capital(
        self, request: CapitalMovementRequest
    ) -> CapitalMovement:
        with self._unit_of_work.unit_of_work() as uow:
            movement = AddCapital(
                accounts=uow.accounts,
                movements=uow.capital_movements,
                transactions=uow.transactions,
            ).execute(request)
            uow.commit()
            return movement

    def withdraw_capital(
        self, request: CapitalMovementRequest
    ) -> CapitalMovement:
        with self._unit_of_work.unit_of_work() as uow:
            movement = WithdrawCapital(
                accounts=uow.accounts,
                movements=uow.capital_movements,
                transactions=uow.transactions,
            ).execute(request)
            uow.commit()
            return movement

    def transfer_money(
        self, request: TransferMoneyRequest
    ) -> AccountTransfer:
        with self._unit_of_work.unit_of_work() as uow:
            transfer = TransferMoney(
                accounts=uow.accounts,
                transfers=uow.transfers,
                transactions=uow.transactions,
            ).execute(request)
            uow.commit()
            return transfer

    def exchange_currency(
        self, request: ExchangeCurrencyRequest
    ) -> AccountTransfer:
        with self._unit_of_work.unit_of_work() as uow:
            transfer = ExchangeCurrency(
                accounts=uow.accounts,
                exchange_rates=uow.exchange_rates,
                transfers=uow.transfers,
                transactions=uow.transactions,
            ).execute(request)
            uow.commit()
            return transfer


def _expense_row(expense: Expense) -> ExpenseRow:
    if expense.id is None:
        raise RuntimeError("Persisted expense has no identifier.")
    return ExpenseRow(
        expense_id=expense.id,
        expense_date=expense.expense_date,
        expense_type=expense.expense_type,
        amount=expense.amount,
        account_name=expense.account.name,
        description=expense.description,
        notes=expense.notes,
    )


def _capital_row(
    movement: CapitalMovement, account: Account
) -> CapitalRow:
    if movement.id is None:
        raise RuntimeError("Persisted capital movement has no identifier.")
    return CapitalRow(
        movement_id=movement.id,
        movement_date=movement.movement_date,
        movement_type=movement.movement_type,
        amount=movement.amount,
        account_name=account.name,
        notes=movement.notes,
    )


def _transfer_row(transfer: AccountTransfer) -> TransferRow:
    if transfer.id is None:
        raise RuntimeError("Persisted transfer has no identifier.")
    return TransferRow(
        transfer_id=transfer.id,
        transfer_date=transfer.transfer_date,
        source_account=transfer.source_account.name,
        destination_account=transfer.destination_account.name,
        source_amount=transfer.source_amount,
        destination_amount=transfer.destination_amount,
        is_cross_currency=transfer.is_cross_currency,
        notes=transfer.notes,
    )
