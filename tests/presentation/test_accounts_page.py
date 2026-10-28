"""Accounts screen and dialog tests (headless)."""

from __future__ import annotations

from types import SimpleNamespace

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QStackedWidget,
    QTableView,
)

from app.application.finances.list_accounts import AccountListItem
from app.domain.entities.currency import Currency
from app.domain.value_objects.money import Money
from app.infrastructure.config.settings import Settings
from app.presentation.desktop.app import build_main_window
from app.presentation.desktop.dialogs.account import AccountDialog
from app.presentation.desktop.navigation import NAVIGATION_ITEMS
from app.presentation.desktop.views.accounts import AccountsPage

USD = Currency(code="USD", name="US Dollar", decimal_places=2)
EUR = Currency(code="EUR", name="Euro", decimal_places=2)


class FakeAccounts:
    def __init__(self, rows=(), currencies=()) -> None:
        self.rows = tuple(rows)
        self.currencies = tuple(currencies)
        self.list_calls: list[bool] = []
        self.created_accounts: list = []
        self.active_changes: list[tuple[int, bool]] = []

    def list_accounts(self, *, include_inactive: bool = False):
        self.list_calls.append(include_inactive)
        if include_inactive:
            return self.rows
        return tuple(row for row in self.rows if row.is_active)

    def create_account(self, request):
        self.created_accounts.append(request)
        return SimpleNamespace(id=len(self.created_accounts))

    def set_account_active(self, account_id: int, *, is_active: bool):
        self.active_changes.append((account_id, is_active))
        return SimpleNamespace(id=account_id, is_active=is_active)

    def list_enabled_currencies(self):
        return self.currencies


def _item(
    name: str,
    *,
    balance: str = "0.00",
    active: bool = True,
    account_type: str | None = "Cash",
    currency: Currency = USD,
    account_id: int = 1,
) -> AccountListItem:
    return AccountListItem(
        account_id=account_id,
        name=name,
        account_type=account_type,
        currency_code=currency.code,
        balance=Money(balance, currency),
        is_active=active,
        notes=None,
    )


def test_accounts_page_shows_native_balances(qapp) -> None:
    service = FakeAccounts(
        rows=(
            _item("Main Cash", balance="125.50"),
            _item(
                "Euro Wallet",
                balance="80.00",
                currency=EUR,
                account_type="Wallet",
                account_id=2,
            ),
        )
    )
    page = AccountsPage(service, base_currency="USD")
    try:
        table = page.findChild(QTableView, "accountsTable")
        assert table is not None
        model = table.model()
        assert model.rowCount() == 2
        assert model.data(model.index(0, 0)) == "Main Cash"
        assert model.data(model.index(0, 3)) == "125.50 USD"
        assert model.data(model.index(1, 2)) == "EUR"
        assert model.data(model.index(1, 3)) == "80.00 EUR"

        footer = page.findChild(QLabel, "accountsFooter")
        assert footer is not None
        assert footer.text() == "2 accounts"
    finally:
        page.close()


def test_account_search_filters_by_name_type_or_currency(qapp) -> None:
    service = FakeAccounts(
        rows=(
            _item("Main Cash", account_id=1),
            _item("Euro Wallet", currency=EUR, account_id=2),
        )
    )
    page = AccountsPage(service, base_currency="USD")
    try:
        search = page.findChild(QLineEdit, "accountSearch")
        table = page.findChild(QTableView, "accountsTable")
        footer = page.findChild(QLabel, "accountsFooter")
        assert search is not None
        assert table is not None
        assert footer is not None

        search.setText("eur")
        assert table.model().rowCount() == 1
        assert table.model().data(table.model().index(0, 0)) == "Euro Wallet"
        assert footer.text() == "1 of 2 accounts"

        search.clear()
        assert table.model().rowCount() == 2
    finally:
        page.close()


def test_show_inactive_accounts_reloads_with_the_flag(qapp) -> None:
    service = FakeAccounts(
        rows=(
            _item("Current", account_id=1),
            _item("Retired", active=False, account_id=2),
        )
    )
    page = AccountsPage(service, base_currency="USD")
    try:
        table = page.findChild(QTableView, "accountsTable")
        checkbox = page.findChild(QCheckBox, "showInactiveAccounts")
        assert table is not None
        assert checkbox is not None
        assert table.model().rowCount() == 1

        checkbox.setChecked(True)

        assert service.list_calls[-1] is True
        assert table.model().rowCount() == 2
    finally:
        page.close()


def test_empty_accounts_page_shows_empty_state(qapp) -> None:
    page = AccountsPage(FakeAccounts(), base_currency="USD")
    try:
        table = page.findChild(QTableView, "accountsTable")
        stack = page.findChild(QStackedWidget, "accountsContent")
        footer = page.findChild(QLabel, "accountsFooter")
        assert table is not None
        assert stack is not None
        assert footer is not None

        assert stack.currentWidget() is not table
        assert footer.text() == "No accounts"
    finally:
        page.close()


def test_accounts_page_toggles_the_selected_account(
    qapp, monkeypatch
) -> None:
    service = FakeAccounts(rows=(_item("Main Cash"),))
    page = AccountsPage(service, base_currency="USD")
    try:
        table = page.findChild(QTableView, "accountsTable")
        button = page.findChild(QPushButton, "toggleAccountActiveButton")
        assert table is not None
        assert button is not None
        assert not button.isEnabled()

        table.selectRow(0)
        assert button.isEnabled()
        assert button.text() == "Deactivate"

        monkeypatch.setattr(
            QMessageBox,
            "question",
            lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
        )
        button.click()

        assert service.active_changes == [(1, False)]
    finally:
        page.close()


def test_account_dialog_sends_a_complete_request(qapp) -> None:
    service = FakeAccounts(currencies=(EUR, USD))
    dialog = AccountDialog(
        service,
        service.currencies,
        base_currency="USD",
    )
    try:
        dialog.findChild(QLineEdit, "accountName").setText("Main Cash")
        dialog.findChild(QComboBox, "accountType").setCurrentText("Bank")
        dialog.findChild(QPlainTextEdit, "accountNotes").setPlainText(
            "Daily use"
        )

        currency = dialog.findChild(QComboBox, "accountCurrency")
        assert currency is not None
        assert currency.currentData().code == "USD"

        dialog.findChild(QPushButton, "createAccountButton").click()

        assert dialog.result() == QDialog.DialogCode.Accepted
        assert len(service.created_accounts) == 1
        request = service.created_accounts[0]
        assert request.name == "Main Cash"
        assert request.currency == USD
        assert request.account_type == "Bank"
        assert request.notes == "Daily use"
    finally:
        dialog.close()


def test_main_window_uses_the_real_accounts_screen(qapp) -> None:
    service = FakeAccounts(currencies=(USD,))
    window = build_main_window(
        Settings(base_currency="USD"), accounts=service
    )
    try:
        stack = window.findChild(QStackedWidget, "pageStack")
        assert stack is not None
        account_index = [
            item.key for item in NAVIGATION_ITEMS
        ].index("accounts")
        assert isinstance(stack.widget(account_index), AccountsPage)
    finally:
        window.close()
