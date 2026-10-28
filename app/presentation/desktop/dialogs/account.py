"""Account creation dialog."""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtWidgets import (
    QComboBox,
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

from app.application.finances.account_service import AccountService
from app.application.finances.create_account import CreateAccountRequest
from app.domain.entities.currency import Currency


class AccountDialog(QDialog):
    """Collect and persist a new account."""

    def __init__(
        self,
        accounts: AccountService,
        currencies: Sequence[Currency],
        *,
        base_currency: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        if not currencies:
            raise ValueError("At least one enabled currency is required.")

        self._accounts = accounts
        self._currencies = tuple(currencies)
        self._base_currency = base_currency

        self.setWindowTitle("New account")
        self.setModal(True)
        self.resize(460, 360)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel("New account", self)
        title.setObjectName("dialogTitle")
        layout.addWidget(title)

        form = QFormLayout()
        self._name = QLineEdit(self)
        self._name.setObjectName("accountName")
        self._name.setPlaceholderText("For example: Main cash")
        form.addRow("Name *", self._name)

        self._currency = QComboBox(self)
        self._currency.setObjectName("accountCurrency")
        default_index = 0
        for index, currency in enumerate(self._currencies):
            self._currency.addItem(
                f"{currency.code} — {currency.name}", currency
            )
            if currency.code == self._base_currency:
                default_index = index
        self._currency.setCurrentIndex(default_index)
        form.addRow("Native currency", self._currency)

        self._type = QComboBox(self)
        self._type.setObjectName("accountType")
        self._type.setEditable(True)
        self._type.addItems(
            ["Cash", "Bank", "Wallet", "Card", "Savings", "Other"]
        )
        self._type.setCurrentIndex(-1)
        if self._type.lineEdit() is not None:
            self._type.lineEdit().setPlaceholderText(
                "Optional, for example: Bank"
            )
        form.addRow("Type", self._type)

        self._notes = QPlainTextEdit(self)
        self._notes.setObjectName("accountNotes")
        self._notes.setPlaceholderText("Optional notes")
        self._notes.setFixedHeight(70)
        form.addRow("Notes", self._notes)

        layout.addLayout(form)
        layout.addStretch(1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel, self)
        self._create_button = QPushButton("Create account", self)
        self._create_button.setObjectName("createAccountButton")
        self._create_button.setProperty("variant", "primary")
        self._create_button.setDefault(True)
        buttons.addButton(
            self._create_button, QDialogButtonBox.ButtonRole.AcceptRole
        )
        buttons.rejected.connect(self.reject)
        self._create_button.clicked.connect(self._submit)
        layout.addWidget(buttons)

    def _submit(self) -> None:
        name = self._name.text().strip()
        if not name:
            QMessageBox.warning(self, "Invalid account", "Name is required.")
            return

        currency = self._currency.currentData()
        if not isinstance(currency, Currency):
            QMessageBox.warning(
                self, "Invalid account", "Select a native currency."
            )
            return

        try:
            self._accounts.create_account(
                CreateAccountRequest(
                    name=name,
                    currency=currency,
                    account_type=(
                        self._type.currentText().strip() or None
                    ),
                    notes=self._notes.toPlainText().strip() or None,
                )
            )
        except Exception as exc:
            QMessageBox.critical(
                self, "Could not create account", str(exc)
            )
            return

        self.accept()
