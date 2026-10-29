"""Expenses and capital screen, including transfers and exchanges."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from app.application.finances.operations_service import (
    CapitalRow,
    ExpenseRow,
    FinanceOperationsService,
    TransferRow,
)
from app.domain.enums.capital_movement_type import CapitalMovementType
from app.presentation.desktop.dialogs.finances import (
    CapitalMovementDialog,
    ExchangeDialog,
    ExpenseDialog,
    TransferDialog,
)
from app.presentation.desktop.form_utils import display_datetime
from app.presentation.desktop.labels import (
    capital_movement_label,
    expense_type_label,
)
from app.presentation.desktop.table_model import ReadOnlyTableModel


class FinancesPage(QWidget):
    """Track operating expenses, capital and movements between accounts."""

    def __init__(
        self,
        finance: FinanceOperationsService,
        *,
        base_currency: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._finance = finance
        self._base_currency = base_currency
        self._expenses: tuple[ExpenseRow, ...] = ()
        self._capital: tuple[CapitalRow, ...] = ()
        self._transfers: tuple[TransferRow, ...] = ()
        self.setObjectName("financesPage")
        self._build_ui()
        self.reload()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 24)
        layout.setSpacing(14)

        title = QLabel("Expenses & Capital", self)
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        description = QLabel(
            "Register operating expenses, owner contributions and "
            "withdrawals, and move money between accounts without editing "
            "the ledger directly.",
            self,
        )
        description.setObjectName("pageDescription")
        description.setWordWrap(True)
        layout.addWidget(description)

        toolbar = QHBoxLayout()
        refresh = QPushButton("Refresh", self)
        refresh.setObjectName("refreshFinancesButton")
        refresh.clicked.connect(self.reload)
        toolbar.addWidget(refresh)
        toolbar.addStretch(1)

        expense = QPushButton("Add expense", self)
        expense.setObjectName("addExpenseButton")
        expense.setProperty("variant", "primary")
        expense.clicked.connect(self._add_expense)
        toolbar.addWidget(expense)

        contribution = QPushButton("Contribute capital", self)
        contribution.setObjectName("addCapitalButton")
        contribution.clicked.connect(self._add_capital)
        toolbar.addWidget(contribution)

        withdrawal = QPushButton("Withdraw capital", self)
        withdrawal.setObjectName("withdrawCapitalButton")
        withdrawal.clicked.connect(self._withdraw_capital)
        toolbar.addWidget(withdrawal)

        transfer = QPushButton("Transfer", self)
        transfer.setObjectName("transferMoneyButton")
        transfer.clicked.connect(self._transfer)
        toolbar.addWidget(transfer)

        exchange = QPushButton("Exchange", self)
        exchange.setObjectName("exchangeCurrencyButton")
        exchange.clicked.connect(self._exchange)
        toolbar.addWidget(exchange)
        layout.addLayout(toolbar)

        self._error_banner = QLabel(self)
        self._error_banner.setObjectName("errorBanner")
        self._error_banner.setWordWrap(True)
        self._error_banner.hide()
        layout.addWidget(self._error_banner)

        self._expenses_model = ReadOnlyTableModel(
            ("Date", "Type", "Account", "Amount", "Description", "Notes"),
            self._expense_values,
            right_columns=(3,),
            parent=self,
        )
        self._capital_model = ReadOnlyTableModel(
            ("Date", "Type", "Account", "Amount", "Notes"),
            self._capital_values,
            right_columns=(3,),
            center_columns=(1,),
            parent=self,
        )
        self._transfers_model = ReadOnlyTableModel(
            (
                "Date",
                "From",
                "To",
                "Source amount",
                "Destination amount",
                "Notes",
            ),
            self._transfer_values,
            right_columns=(3, 4),
            parent=self,
        )

        self._expenses_table = _table(
            self, "expensesTable", self._expenses_model, 4
        )
        self._capital_table = _table(
            self, "capitalTable", self._capital_model, 4
        )
        self._transfers_table = _table(
            self, "transfersTable", self._transfers_model, 5
        )

        self._tabs = QTabWidget(self)
        self._tabs.setObjectName("financesTabs")
        self._tabs.addTab(self._expenses_table, "Expenses")
        self._tabs.addTab(self._capital_table, "Capital")
        self._tabs.addTab(self._transfers_table, "Transfers")
        layout.addWidget(self._tabs, 1)

        self._footer = QLabel(self)
        self._footer.setObjectName("financesFooter")
        layout.addWidget(self._footer)

    @staticmethod
    def _expense_values(row: ExpenseRow) -> tuple[str, ...]:
        return (
            display_datetime(row.expense_date),
            expense_type_label(row.expense_type),
            row.account_name,
            str(row.amount),
            row.description or "—",
            row.notes or "—",
        )

    @staticmethod
    def _capital_values(row: CapitalRow) -> tuple[str, ...]:
        return (
            display_datetime(row.movement_date),
            capital_movement_label(row.movement_type),
            row.account_name,
            str(row.amount),
            row.notes or "—",
        )

    @staticmethod
    def _transfer_values(row: TransferRow) -> tuple[str, ...]:
        return (
            display_datetime(row.transfer_date),
            row.source_account,
            row.destination_account,
            str(row.source_amount),
            str(row.destination_amount),
            row.notes or "—",
        )

    def reload(self, *_args) -> None:
        try:
            expenses = self._finance.list_expenses()
            capital = self._finance.list_capital_movements()
            transfers = self._finance.list_transfers()
        except Exception as exc:
            self._show_error(f"Could not load finances: {exc}")
            return
        self._show_error(None)
        self._expenses = tuple(expenses)
        self._capital = tuple(capital)
        self._transfers = tuple(transfers)
        self._expenses_model.set_rows(self._expenses)
        self._capital_model.set_rows(self._capital)
        self._transfers_model.set_rows(self._transfers)
        self._footer.setText(
            f"{len(self._expenses)} expenses · "
            f"{len(self._capital)} capital movements · "
            f"{len(self._transfers)} transfers"
        )

    def _show_error(self, message: str | None) -> None:
        if message is None:
            self._error_banner.clear()
            self._error_banner.hide()
            return
        self._error_banner.setText(message)
        self._error_banner.show()

    def _accounts(self):
        try:
            accounts = self._finance.list_accounts()
        except Exception as exc:
            QMessageBox.critical(
                self, "Could not load accounts", str(exc)
            )
            return ()
        if not accounts:
            QMessageBox.information(
                self,
                "No active accounts",
                "Create an active account first.",
            )
        return accounts

    def _add_expense(self) -> None:
        accounts = self._accounts()
        if not accounts:
            return
        dialog = ExpenseDialog(self._finance, accounts=accounts, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.reload()

    def _add_capital(self) -> None:
        self._open_capital(CapitalMovementType.CONTRIBUTION)

    def _withdraw_capital(self) -> None:
        self._open_capital(CapitalMovementType.WITHDRAWAL)

    def _open_capital(self, movement_type: CapitalMovementType) -> None:
        accounts = self._accounts()
        if not accounts:
            return
        try:
            dialog = CapitalMovementDialog(
                self._finance,
                accounts=accounts,
                movement_type=movement_type,
                parent=self,
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Cannot register movement", str(exc))
            return
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.reload()

    def _transfer(self) -> None:
        accounts = self._accounts()
        if not accounts:
            return
        try:
            dialog = TransferDialog(
                self._finance, accounts=accounts, parent=self
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Cannot transfer", str(exc))
            return
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.reload()

    def _exchange(self) -> None:
        accounts = self._accounts()
        if not accounts:
            return
        try:
            dialog = ExchangeDialog(
                self._finance, accounts=accounts, parent=self
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Cannot exchange", str(exc))
            return
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.reload()


def _table(
    parent: QWidget,
    object_name: str,
    model: ReadOnlyTableModel,
    stretch_column: int,
) -> QTableView:
    table = QTableView(parent)
    table.setObjectName(object_name)
    table.setModel(model)
    table.setAlternatingRowColors(True)
    table.setSelectionBehavior(
        QAbstractItemView.SelectionBehavior.SelectRows
    )
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.verticalHeader().setVisible(False)
    table.horizontalHeader().setSectionResizeMode(
        stretch_column, QHeaderView.ResizeMode.Stretch
    )
    for column in range(model.columnCount()):
        if column != stretch_column:
            table.horizontalHeader().setSectionResizeMode(
                column, QHeaderView.ResizeMode.ResizeToContents
            )
    return table
