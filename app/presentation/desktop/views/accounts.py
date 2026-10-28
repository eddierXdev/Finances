"""Accounts screen."""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from app.application.finances.account_service import AccountService
from app.application.finances.list_accounts import AccountListItem
from app.domain.entities.currency import Currency
from app.presentation.desktop.dialogs.account import AccountDialog


class AccountTableModel(QAbstractTableModel):
    """Read-only account rows with native-currency balances."""

    HEADERS = ("Name", "Type", "Currency", "Balance", "Status")

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._rows: tuple[AccountListItem, ...] = ()

    def set_accounts(self, accounts: Sequence[AccountListItem]) -> None:
        self.beginResetModel()
        self._rows = tuple(accounts)
        self.endResetModel()

    def accounts(self) -> tuple[AccountListItem, ...]:
        return self._rows

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.HEADERS)

    def data(
        self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole
    ):
        if not index.isValid() or not 0 <= index.row() < len(self._rows):
            return None

        row = self._rows[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            values = (
                row.name,
                row.account_type or "—",
                row.currency_code,
                str(row.balance),
                "Active" if row.is_active else "Inactive",
            )
            return values[index.column()]

        if role == Qt.ItemDataRole.TextAlignmentRole:
            if index.column() == 4:
                return int(
                    Qt.AlignmentFlag.AlignCenter
                    | Qt.AlignmentFlag.AlignVCenter
                )
            return int(
                Qt.AlignmentFlag.AlignLeft
                | Qt.AlignmentFlag.AlignVCenter
            )

        if role == Qt.ItemDataRole.ForegroundRole and not row.is_active:
            return QColor("#9ca3af")

        return None

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ):
        if (
            orientation == Qt.Orientation.Horizontal
            and role == Qt.ItemDataRole.DisplayRole
            and 0 <= section < len(self.HEADERS)
        ):
            return self.HEADERS[section]
        return None


class AccountsPage(QWidget):
    """Account list, creation and activation screen.

    Balances arrive from the application layer. The page only formats them.
    """

    def __init__(
        self,
        accounts: AccountService,
        *,
        base_currency: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._accounts = accounts
        self._base_currency = base_currency
        self._rows: tuple[AccountListItem, ...] = ()

        self.setObjectName("accountsPage")
        self._build_ui()
        self.reload()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 24)
        layout.setSpacing(14)

        title = QLabel("Accounts", self)
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        description = QLabel(
            "Cash, bank, wallet and card accounts. Balances stay in each "
            "account's native currency.",
            self,
        )
        description.setObjectName("pageDescription")
        description.setWordWrap(True)
        layout.addWidget(description)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self._search = QLineEdit(self)
        self._search.setObjectName("accountSearch")
        self._search.setPlaceholderText("Search by name, type or currency")
        self._search.setClearButtonEnabled(True)
        self._search.setMaximumWidth(320)
        self._search.textChanged.connect(self._apply_filter)
        toolbar.addWidget(self._search)

        self._show_inactive = QCheckBox("Show inactive", self)
        self._show_inactive.setObjectName("showInactiveAccounts")
        self._show_inactive.toggled.connect(self.reload)
        toolbar.addWidget(self._show_inactive)

        refresh = QPushButton("Refresh", self)
        refresh.setObjectName("refreshAccountsButton")
        refresh.clicked.connect(self.reload)
        toolbar.addWidget(refresh)

        toolbar.addStretch(1)

        self._new_button = QPushButton("New account", self)
        self._new_button.setObjectName("newAccountButton")
        self._new_button.setProperty("variant", "primary")
        self._new_button.clicked.connect(self._create_account)
        toolbar.addWidget(self._new_button)

        self._toggle_button = QPushButton("Deactivate", self)
        self._toggle_button.setObjectName("toggleAccountActiveButton")
        self._toggle_button.clicked.connect(self._toggle_account_active)
        toolbar.addWidget(self._toggle_button)

        layout.addLayout(toolbar)

        self._error_banner = QLabel(self)
        self._error_banner.setObjectName("errorBanner")
        self._error_banner.setWordWrap(True)
        self._error_banner.hide()
        layout.addWidget(self._error_banner)

        self._model = AccountTableModel(self)
        self._table = QTableView(self)
        self._table.setObjectName("accountsTable")
        self._table.setModel(self._model)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self._table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self._table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.selectionModel().selectionChanged.connect(
            self._update_actions
        )

        self._empty_title = QLabel("No accounts yet", self)
        self._empty_title.setObjectName("emptyStateTitle")
        self._empty_hint = QLabel(
            "Create a cash, bank or wallet account to start tracking money.",
            self,
        )
        self._empty_hint.setObjectName("emptyStateHint")
        self._empty_hint.setWordWrap(True)
        self._empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._empty = QWidget(self)
        empty_layout = QVBoxLayout(self._empty)
        empty_layout.setContentsMargins(24, 24, 24, 24)
        empty_layout.setSpacing(6)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self._empty_title)
        empty_layout.addWidget(self._empty_hint)

        self._content = QStackedWidget(self)
        self._content.setObjectName("accountsContent")
        self._content.addWidget(self._table)
        self._content.addWidget(self._empty)
        layout.addWidget(self._content, 1)

        self._footer = QLabel(self)
        self._footer.setObjectName("accountsFooter")
        layout.addWidget(self._footer)

        self._update_actions()

    def reload(self, *_args) -> None:
        try:
            rows = self._accounts.list_accounts(
                include_inactive=self._show_inactive.isChecked()
            )
        except Exception as exc:
            self._show_error(f"Could not load accounts: {exc}")
            return

        self._show_error(None)
        self._rows = tuple(rows)
        self._apply_filter()

    def _apply_filter(self, *_args) -> None:
        query = self._search.text().strip().casefold()
        rows = self._rows
        if query:
            rows = tuple(
                account
                for account in rows
                if query
                in " ".join(
                    part
                    for part in (
                        account.name,
                        account.account_type or "",
                        account.currency_code,
                    )
                    if part
                ).casefold()
            )

        self._model.set_accounts(rows)
        self._update_actions()
        visible = bool(rows)
        self._content.setCurrentWidget(
            self._table if visible else self._empty
        )

        if not self._rows:
            self._empty_title.setText("No accounts yet")
            self._empty_hint.setText(
                "Create a cash, bank or wallet account to start tracking "
                "money."
            )
            self._footer.setText("No accounts")
        elif not rows:
            self._empty_title.setText("No matching accounts")
            self._empty_hint.setText(
                "Change the search text or include inactive accounts."
            )
            self._footer.setText(f"0 of {len(self._rows)} accounts")
        else:
            suffix = "account" if len(rows) == 1 else "accounts"
            if len(rows) == len(self._rows):
                self._footer.setText(f"{len(rows)} {suffix}")
            else:
                self._footer.setText(
                    f"{len(rows)} of {len(self._rows)} accounts"
                )

    def _show_error(self, message: str | None) -> None:
        if message is None:
            self._error_banner.clear()
            self._error_banner.hide()
            return
        self._error_banner.setText(message)
        self._error_banner.show()

    def _selected_account(self) -> AccountListItem | None:
        indexes = self._table.selectionModel().selectedRows()
        if not indexes:
            return None
        row = indexes[0].row()
        rows = self._model.accounts()
        if 0 <= row < len(rows):
            return rows[row]
        return None

    def _update_actions(self, *_args) -> None:
        selected = self._selected_account()
        self._toggle_button.setEnabled(selected is not None)
        if selected is None:
            self._toggle_button.setText("Deactivate")
        else:
            self._toggle_button.setText(
                "Deactivate" if selected.is_active else "Activate"
            )

    def _create_account(self) -> None:
        try:
            currencies = tuple(self._accounts.list_enabled_currencies())
        except Exception as exc:
            QMessageBox.critical(
                self, "Could not open account form", str(exc)
            )
            return

        if not currencies:
            QMessageBox.warning(
                self,
                "No currencies available",
                "Enable at least one currency before creating accounts.",
            )
            return

        dialog = AccountDialog(
            self._accounts,
            currencies,
            base_currency=self._base_currency,
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.reload()

    def _toggle_account_active(self) -> None:
        selected = self._selected_account()
        if selected is None:
            return

        target = not selected.is_active
        action = "Activate" if target else "Deactivate"
        answer = QMessageBox.question(
            self,
            f"{action} account",
            f"{action} account {selected.name!r}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            self._accounts.set_account_active(
                selected.account_id, is_active=target
            )
        except Exception as exc:
            QMessageBox.critical(
                self, f"Could not {action.lower()} account", str(exc)
            )
            return
        self.reload()
