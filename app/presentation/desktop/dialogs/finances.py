"""Dialogs for expenses, capital movements and account transfers."""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.application.finances.capital import CapitalMovementRequest
from app.application.finances.exchange_currency import (
    ExchangeCurrencyRequest,
)
from app.application.finances.operations_service import (
    FinanceOperationsService,
)
from app.application.finances.register_expense import (
    RegisterExpenseRequest,
)
from app.application.finances.transfer_money import TransferMoneyRequest
from app.domain.entities.account import Account
from app.domain.entities.exchange_rate import ExchangeRate
from app.domain.enums.capital_movement_type import CapitalMovementType
from app.domain.enums.expense_type import ExpenseType
from app.presentation.desktop.form_utils import (
    date_to_datetime,
    parse_money,
)
from app.presentation.desktop.labels import (
    capital_movement_label,
    expense_type_label,
)


class ExpenseDialog(QDialog):
    """Register an operating expense from one account."""

    def __init__(
        self,
        finance: FinanceOperationsService,
        *,
        accounts: Sequence[Account],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        active = tuple(account for account in accounts if account.is_active)
        if not active:
            raise ValueError("At least one active account is required.")
        self._finance = finance
        self._accounts = active
        self.created_result = None
        self.setWindowTitle("New expense")
        self.setModal(True)
        self.resize(520, 460)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel("New expense", self)
        title.setObjectName("dialogTitle")
        layout.addWidget(title)

        form = QFormLayout()
        self._account = QComboBox(self)
        self._account.setObjectName("expenseAccount")
        for account in self._accounts:
            self._account.addItem(
                f"{account.name} — {account.currency.code}", account
            )
        form.addRow("Paid from *", self._account)

        self._type = QComboBox(self)
        self._type.setObjectName("expenseType")
        for value in ExpenseType:
            self._type.addItem(expense_type_label(value), value)
        form.addRow("Expense type *", self._type)

        self._amount = QLineEdit(self)
        self._amount.setObjectName("expenseAmount")
        self._amount.setPlaceholderText("0.00")
        form.addRow("Amount *", self._amount)

        self._date = QDateEdit(QDate.currentDate(), self)
        self._date.setObjectName("expenseDate")
        self._date.setCalendarPopup(True)
        self._date.setDisplayFormat("yyyy-MM-dd")
        form.addRow("Expense date *", self._date)

        self._description = QLineEdit(self)
        self._description.setObjectName("expenseDescription")
        self._description.setPlaceholderText("Example: Facebook ads")
        form.addRow("Description", self._description)

        self._notes = QPlainTextEdit(self)
        self._notes.setObjectName("expenseNotes")
        self._notes.setPlaceholderText("Optional notes")
        self._notes.setFixedHeight(60)
        form.addRow("Notes", self._notes)
        layout.addLayout(form)

        hint = QLabel(
            "The application records a negative EXPENSE ledger entry in the "
            "account's native currency.",
            self,
        )
        hint.setObjectName("fieldHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        layout.addStretch(1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel, self
        )
        save = QPushButton("Register expense", self)
        save.setObjectName("createExpenseButton")
        save.setProperty("variant", "primary")
        save.setDefault(True)
        buttons.addButton(save, QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.rejected.connect(self.reject)
        save.clicked.connect(self._submit)
        layout.addWidget(buttons)

    def _submit(self) -> None:
        account = self._account.currentData()
        if not isinstance(account, Account):
            return
        try:
            amount = parse_money(
                self._amount.text(), account.currency, "Amount"
            )
            self.created_result = self._finance.register_expense(
                RegisterExpenseRequest(
                    account_id=account.id,
                    expense_type=ExpenseType(self._type.currentData()),
                    amount=amount,
                    expense_date=date_to_datetime(self._date.date()),
                    description=(
                        self._description.text().strip() or None
                    ),
                    notes=self._notes.toPlainText().strip() or None,
                )
            )
        except Exception as exc:
            QMessageBox.critical(
                self, "Could not register expense", str(exc)
            )
            return
        self.accept()


class CapitalMovementDialog(QDialog):
    """Register a capital contribution or withdrawal."""

    def __init__(
        self,
        finance: FinanceOperationsService,
        *,
        accounts: Sequence[Account],
        movement_type: CapitalMovementType,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        active = tuple(account for account in accounts if account.is_active)
        if not active:
            raise ValueError("At least one active account is required.")
        self._finance = finance
        self._accounts = active
        self._movement_type = movement_type
        self.created_result = None
        title = capital_movement_label(movement_type)
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(500, 390)
        self._build_ui(title)

    def _build_ui(self, title_text: str) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel(title_text, self)
        title.setObjectName("dialogTitle")
        layout.addWidget(title)

        form = QFormLayout()
        self._account = QComboBox(self)
        self._account.setObjectName("capitalAccount")
        for account in self._accounts:
            self._account.addItem(
                f"{account.name} — {account.currency.code}", account
            )
        form.addRow("Account *", self._account)

        self._amount = QLineEdit(self)
        self._amount.setObjectName("capitalAmount")
        self._amount.setPlaceholderText("0.00")
        form.addRow("Amount *", self._amount)

        self._date = QDateEdit(QDate.currentDate(), self)
        self._date.setObjectName("capitalDate")
        self._date.setCalendarPopup(True)
        self._date.setDisplayFormat("yyyy-MM-dd")
        form.addRow("Movement date *", self._date)

        self._notes = QPlainTextEdit(self)
        self._notes.setObjectName("capitalNotes")
        self._notes.setPlaceholderText("Optional notes")
        self._notes.setFixedHeight(60)
        form.addRow("Notes", self._notes)
        layout.addLayout(form)
        layout.addStretch(1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel, self
        )
        save = QPushButton("Register movement", self)
        save.setObjectName("createCapitalButton")
        save.setProperty("variant", "primary")
        save.setDefault(True)
        buttons.addButton(save, QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.rejected.connect(self.reject)
        save.clicked.connect(self._submit)
        layout.addWidget(buttons)

    def _submit(self) -> None:
        account = self._account.currentData()
        if not isinstance(account, Account):
            return
        try:
            amount = parse_money(
                self._amount.text(), account.currency, "Amount"
            )
            request = CapitalMovementRequest(
                account_id=account.id,
                amount=amount,
                movement_date=date_to_datetime(self._date.date()),
                notes=self._notes.toPlainText().strip() or None,
            )
            if self._movement_type is CapitalMovementType.CONTRIBUTION:
                self.created_result = self._finance.add_capital(request)
            else:
                self.created_result = self._finance.withdraw_capital(request)
        except Exception as exc:
            QMessageBox.critical(
                self, "Could not register movement", str(exc)
            )
            return
        self.accept()


class TransferDialog(QDialog):
    """Move money between two accounts with the same currency."""

    def __init__(
        self,
        finance: FinanceOperationsService,
        *,
        accounts: Sequence[Account],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        active = tuple(account for account in accounts if account.is_active)
        if len(active) < 2:
            raise ValueError("At least two active accounts are required.")
        self._finance = finance
        self._accounts = active
        self.created_result = None
        self.setWindowTitle("Account transfer")
        self.setModal(True)
        self.resize(520, 430)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel("Account transfer", self)
        title.setObjectName("dialogTitle")
        layout.addWidget(title)

        form = QFormLayout()
        self._source = QComboBox(self)
        self._source.setObjectName("transferSource")
        self._destination = QComboBox(self)
        self._destination.setObjectName("transferDestination")
        for account in self._accounts:
            self._source.addItem(
                f"{account.name} — {account.currency.code}", account
            )
        self._source.currentIndexChanged.connect(
            self._refresh_destinations
        )
        form.addRow("From *", self._source)
        form.addRow("To *", self._destination)

        self._amount = QLineEdit(self)
        self._amount.setObjectName("transferAmount")
        self._amount.setPlaceholderText("0.00")
        form.addRow("Amount *", self._amount)

        self._date = QDateEdit(QDate.currentDate(), self)
        self._date.setObjectName("transferDate")
        self._date.setCalendarPopup(True)
        self._date.setDisplayFormat("yyyy-MM-dd")
        form.addRow("Transfer date *", self._date)

        self._notes = QPlainTextEdit(self)
        self._notes.setObjectName("transferNotes")
        self._notes.setPlaceholderText("Optional notes")
        self._notes.setFixedHeight(60)
        form.addRow("Notes", self._notes)
        layout.addLayout(form)
        layout.addStretch(1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel, self
        )
        save = QPushButton("Transfer", self)
        save.setObjectName("createTransferButton")
        save.setProperty("variant", "primary")
        save.setDefault(True)
        buttons.addButton(save, QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.rejected.connect(self.reject)
        save.clicked.connect(self._submit)
        layout.addWidget(buttons)
        self._refresh_destinations()

    def _refresh_destinations(self, *_args) -> None:
        source = self._source.currentData()
        self._destination.clear()
        if not isinstance(source, Account):
            return
        for account in self._accounts:
            if (
                account.id != source.id
                and account.currency.code == source.currency.code
            ):
                self._destination.addItem(
                    f"{account.name} — {account.currency.code}", account
                )

    def _submit(self) -> None:
        source = self._source.currentData()
        destination = self._destination.currentData()
        if not isinstance(source, Account):
            return
        if not isinstance(destination, Account):
            QMessageBox.warning(
                self,
                "Cannot transfer",
                "No destination account uses the source currency.",
            )
            return
        try:
            amount = parse_money(
                self._amount.text(), source.currency, "Amount"
            )
            self.created_result = self._finance.transfer_money(
                TransferMoneyRequest(
                    source_account_id=source.id,
                    destination_account_id=destination.id,
                    amount=amount,
                    transfer_date=date_to_datetime(self._date.date()),
                    notes=self._notes.toPlainText().strip() or None,
                )
            )
        except Exception as exc:
            QMessageBox.critical(
                self, "Could not transfer money", str(exc)
            )
            return
        self.accept()


class ExchangeDialog(QDialog):
    """Exchange money between accounts using a stored historical rate."""

    def __init__(
        self,
        finance: FinanceOperationsService,
        *,
        accounts: Sequence[Account],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        active = tuple(account for account in accounts if account.is_active)
        if len(active) < 2:
            raise ValueError("At least two active accounts are required.")
        self._finance = finance
        self._accounts = active
        self.created_result = None
        self.setWindowTitle("Currency exchange")
        self.setModal(True)
        self.resize(540, 470)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel("Currency exchange", self)
        title.setObjectName("dialogTitle")
        layout.addWidget(title)

        form = QFormLayout()
        self._source = QComboBox(self)
        self._source.setObjectName("exchangeSource")
        self._destination = QComboBox(self)
        self._destination.setObjectName("exchangeDestination")
        self._rate = QComboBox(self)
        self._rate.setObjectName("exchangeRate")
        for account in self._accounts:
            self._source.addItem(
                f"{account.name} — {account.currency.code}", account
            )
        self._source.currentIndexChanged.connect(
            self._refresh_destinations
        )
        self._destination.currentIndexChanged.connect(self._refresh_rates)
        form.addRow("From *", self._source)
        form.addRow("To *", self._destination)
        form.addRow("Rate *", self._rate)

        self._amount = QLineEdit(self)
        self._amount.setObjectName("exchangeAmount")
        self._amount.setPlaceholderText("0.00")
        form.addRow("Source amount *", self._amount)

        self._date = QDateEdit(QDate.currentDate(), self)
        self._date.setObjectName("exchangeDate")
        self._date.setCalendarPopup(True)
        self._date.setDisplayFormat("yyyy-MM-dd")
        form.addRow("Exchange date *", self._date)

        self._notes = QPlainTextEdit(self)
        self._notes.setObjectName("exchangeNotes")
        self._notes.setPlaceholderText("Optional notes")
        self._notes.setFixedHeight(60)
        form.addRow("Notes", self._notes)
        layout.addLayout(form)

        self._rate_hint = QLabel(self)
        self._rate_hint.setObjectName("fieldHint")
        self._rate_hint.setWordWrap(True)
        layout.addWidget(self._rate_hint)
        layout.addStretch(1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel, self
        )
        save = QPushButton("Exchange", self)
        save.setObjectName("createExchangeButton")
        save.setProperty("variant", "primary")
        save.setDefault(True)
        buttons.addButton(save, QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.rejected.connect(self.reject)
        save.clicked.connect(self._submit)
        layout.addWidget(buttons)
        self._refresh_destinations()

    def _refresh_destinations(self, *_args) -> None:
        source = self._source.currentData()
        self._destination.clear()
        if not isinstance(source, Account):
            return
        for account in self._accounts:
            if (
                account.id != source.id
                and account.currency.code != source.currency.code
            ):
                self._destination.addItem(
                    f"{account.name} — {account.currency.code}", account
                )
        self._refresh_rates()

    def _refresh_rates(self, *_args) -> None:
        source = self._source.currentData()
        destination = self._destination.currentData()
        self._rate.clear()
        self._rate_hint.clear()
        if not isinstance(source, Account) or not isinstance(
            destination, Account
        ):
            self._rate_hint.setText(
                "No cross-currency destination account is available."
            )
            return
        try:
            rates = self._finance.list_exchange_rates(
                source.currency.code, destination.currency.code
            )
        except Exception as exc:
            self._rate_hint.setText(f"Could not load rates: {exc}")
            return
        if not rates:
            self._rate_hint.setText(
                "No historical rate exists for this direction. Add one on "
                "the Currency Rates screen first."
            )
            return
        for rate in reversed(tuple(rates)):
            self._rate.addItem(
                f"1 {source.currency.code} = {rate.rate} "
                f"{destination.currency.code} · "
                f"{rate.rate_timestamp.date().isoformat()} · "
                f"{rate.source.value}",
                rate,
            )
        self._rate_hint.setText(
            "The exchange use case applies the selected immutable rate."
        )

    def _submit(self) -> None:
        source = self._source.currentData()
        destination = self._destination.currentData()
        rate = self._rate.currentData()
        if not isinstance(source, Account):
            return
        if not isinstance(destination, Account):
            QMessageBox.warning(
                self,
                "Cannot exchange",
                "Select a destination account with another currency.",
            )
            return
        if not isinstance(rate, ExchangeRate) or rate.id is None:
            QMessageBox.warning(
                self,
                "Cannot exchange",
                "Select a stored exchange rate.",
            )
            return
        try:
            amount = parse_money(
                self._amount.text(), source.currency, "Amount"
            )
            self.created_result = self._finance.exchange_currency(
                ExchangeCurrencyRequest(
                    source_account_id=source.id,
                    destination_account_id=destination.id,
                    source_amount=amount,
                    exchange_rate_id=rate.id,
                    transfer_date=date_to_datetime(self._date.date()),
                    notes=self._notes.toPlainText().strip() or None,
                )
            )
        except Exception as exc:
            QMessageBox.critical(
                self, "Could not exchange currency", str(exc)
            )
            return
        self.accept()
