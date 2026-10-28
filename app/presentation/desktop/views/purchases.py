"""Purchases screen."""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
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

from app.application.purchases.list_purchases import PurchaseListItem
from app.application.purchases.service import PurchaseService
from app.domain.entities.account import Account
from app.domain.entities.currency import Currency
from app.domain.entities.supplier import Supplier
from app.domain.enums.purchase_status import PurchaseStatus
from app.presentation.desktop.dialogs.purchases import (
    PurchaseDetailDialog,
    PurchaseDialog,
    PurchasePaymentDialog,
    PurchaseStatusDialog,
    SupplierDialog,
)
from app.presentation.desktop.labels import purchase_status_label


class PurchaseTableModel(QAbstractTableModel):
    """Read-only purchase rows with totals from the application layer."""

    HEADERS = (
        "Date",
        "Supplier",
        "Order",
        "Items",
        "Total",
        "Payment",
        "Status",
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._rows: tuple[PurchaseListItem, ...] = ()

    def set_purchases(self, purchases: Sequence[PurchaseListItem]) -> None:
        self.beginResetModel()
        self._rows = tuple(purchases)
        self.endResetModel()

    def purchases(self) -> tuple[PurchaseListItem, ...]:
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
                row.purchase_date.date().isoformat(),
                row.supplier_name or "—",
                row.order_number or "—",
                str(row.item_count),
                str(row.total),
                (
                    f"Paid · {row.account_name}"
                    if row.account_name
                    else "Unpaid"
                ),
                purchase_status_label(row.status),
            )
            return values[index.column()]

        if role == Qt.ItemDataRole.TextAlignmentRole:
            if index.column() == 3:
                return int(
                    Qt.AlignmentFlag.AlignRight
                    | Qt.AlignmentFlag.AlignVCenter
                )
            if index.column() == 6:
                return int(
                    Qt.AlignmentFlag.AlignCenter
                    | Qt.AlignmentFlag.AlignVCenter
                )
            return int(
                Qt.AlignmentFlag.AlignLeft
                | Qt.AlignmentFlag.AlignVCenter
            )

        if (
            role == Qt.ItemDataRole.ForegroundRole
            and row.status is PurchaseStatus.CANCELLED
        ):
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


class PurchasesPage(QWidget):
    """Purchase list, creation, payment and logistics screen.

    All totals, statuses and allowed transitions arrive from the application
    layer. The page only presents them and forwards user actions.
    """

    def __init__(
        self,
        purchases: PurchaseService,
        *,
        base_currency: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._purchases = purchases
        self._base_currency = base_currency
        self._rows: tuple[PurchaseListItem, ...] = ()

        self.setObjectName("purchasesPage")
        self._build_ui()
        self.reload()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 24)
        layout.setSpacing(14)

        title = QLabel("Purchases", self)
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        description = QLabel(
            "Supplier purchases, acquisition costs, full payments and "
            "logistics status.",
            self,
        )
        description.setObjectName("pageDescription")
        description.setWordWrap(True)
        layout.addWidget(description)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self._search = QLineEdit(self)
        self._search.setObjectName("purchaseSearch")
        self._search.setPlaceholderText(
            "Search by supplier, order, tracking or account"
        )
        self._search.setClearButtonEnabled(True)
        self._search.setMaximumWidth(290)
        self._search.textChanged.connect(self._apply_filter)
        toolbar.addWidget(self._search)

        self._status_filter = QComboBox(self)
        self._status_filter.setObjectName("purchaseStatusFilter")
        self._status_filter.addItem("All statuses", None)
        for status in PurchaseStatus:
            self._status_filter.addItem(
                purchase_status_label(status), status
            )
        self._status_filter.currentIndexChanged.connect(self._apply_filter)
        toolbar.addWidget(self._status_filter)

        refresh = QPushButton("Refresh", self)
        refresh.setObjectName("refreshPurchasesButton")
        refresh.clicked.connect(self.reload)
        toolbar.addWidget(refresh)

        toolbar.addStretch(1)

        self._new_supplier_button = QPushButton("New supplier", self)
        self._new_supplier_button.setObjectName("newSupplierButton")
        self._new_supplier_button.clicked.connect(self._create_supplier)
        toolbar.addWidget(self._new_supplier_button)

        self._new_button = QPushButton("New purchase", self)
        self._new_button.setObjectName("newPurchaseButton")
        self._new_button.setProperty("variant", "primary")
        self._new_button.clicked.connect(self._create_purchase)
        toolbar.addWidget(self._new_button)

        layout.addLayout(toolbar)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        actions.addStretch(1)

        self._detail_button = QPushButton("Details", self)
        self._detail_button.setObjectName("purchaseDetailButton")
        self._detail_button.clicked.connect(self._show_detail)
        actions.addWidget(self._detail_button)

        self._pay_button = QPushButton("Register payment", self)
        self._pay_button.setObjectName("purchasePayButton")
        self._pay_button.clicked.connect(self._register_payment)
        actions.addWidget(self._pay_button)

        self._status_button = QPushButton("Update status", self)
        self._status_button.setObjectName("purchaseStatusButton")
        self._status_button.clicked.connect(self._update_status)
        actions.addWidget(self._status_button)

        layout.addLayout(actions)

        self._error_banner = QLabel(self)
        self._error_banner.setObjectName("errorBanner")
        self._error_banner.setWordWrap(True)
        self._error_banner.hide()
        layout.addWidget(self._error_banner)

        self._model = PurchaseTableModel(self)
        self._table = QTableView(self)
        self._table.setObjectName("purchasesTable")
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
        self._table.horizontalHeader().setStretchLastSection(False)
        self._table.selectionModel().selectionChanged.connect(
            self._update_actions
        )
        self._table.doubleClicked.connect(self._show_detail)
        self._table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        for column in range(2, len(PurchaseTableModel.HEADERS)):
            self._table.horizontalHeader().setSectionResizeMode(
                column, QHeaderView.ResizeMode.ResizeToContents
            )

        self._empty_title = QLabel("No purchases yet", self)
        self._empty_title.setObjectName("emptyStateTitle")
        self._empty_hint = QLabel(
            "Register a supplier purchase to start tracking acquisition "
            "costs and payments.",
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
        self._content.setObjectName("purchasesContent")
        self._content.addWidget(self._table)
        self._content.addWidget(self._empty)
        layout.addWidget(self._content, 1)

        self._footer = QLabel(self)
        self._footer.setObjectName("purchasesFooter")
        layout.addWidget(self._footer)

        self._update_actions()

    def reload(self, *_args) -> None:
        try:
            rows = self._purchases.list_purchases()
        except Exception as exc:
            self._show_error(f"Could not load purchases: {exc}")
            return

        self._show_error(None)
        self._rows = tuple(rows)
        self._apply_filter()

    def _apply_filter(self, *_args) -> None:
        query = self._search.text().strip().casefold()
        status = self._status_filter.currentData()
        rows = self._rows
        if status is not None:
            target = PurchaseStatus(status)
            rows = tuple(row for row in rows if row.status is target)
        if query:
            rows = tuple(
                row
                for row in rows
                if query
                in " ".join(
                    part
                    for part in (
                        row.supplier_name or "",
                        row.order_number or "",
                        row.tracking_number or "",
                        row.currency_code,
                        row.account_name or "",
                        purchase_status_label(row.status),
                    )
                    if part
                ).casefold()
            )

        self._model.set_purchases(rows)
        self._update_actions()
        self._content.setCurrentWidget(
            self._table if rows else self._empty
        )

        if not self._rows:
            self._empty_title.setText("No purchases yet")
            self._empty_hint.setText(
                "Register a supplier purchase to start tracking acquisition "
                "costs and payments."
            )
            self._footer.setText("No purchases")
        elif not rows:
            self._empty_title.setText("No matching purchases")
            self._empty_hint.setText(
                "Change the search text or select another status."
            )
            self._footer.setText(f"0 of {len(self._rows)} purchases")
        else:
            suffix = "purchase" if len(rows) == 1 else "purchases"
            if len(rows) == len(self._rows):
                self._footer.setText(f"{len(rows)} {suffix}")
            else:
                self._footer.setText(
                    f"{len(rows)} of {len(self._rows)} purchases"
                )

    def _show_error(self, message: str | None) -> None:
        if message is None:
            self._error_banner.clear()
            self._error_banner.hide()
            return
        self._error_banner.setText(message)
        self._error_banner.show()

    def _selected_purchase(self) -> PurchaseListItem | None:
        indexes = self._table.selectionModel().selectedRows()
        if not indexes:
            return None
        row = indexes[0].row()
        rows = self._model.purchases()
        if 0 <= row < len(rows):
            return rows[row]
        return None

    def _update_actions(self, *_args) -> None:
        selected = self._selected_purchase()
        self._detail_button.setEnabled(selected is not None)
        self._pay_button.setEnabled(
            selected is not None
            and selected.status is PurchaseStatus.PENDING
            and selected.total.is_positive
        )
        self._status_button.setEnabled(
            selected is not None and bool(selected.allowed_statuses)
        )

    def _create_supplier(self) -> None:
        SupplierDialog(self._purchases, parent=self).exec()

    def _load_reference_data(
        self,
    ) -> (
        tuple[
            tuple[Currency, ...],
            tuple[Supplier, ...],
            tuple[Account, ...],
        ]
        | None
    ):
        try:
            currencies = tuple(self._purchases.list_enabled_currencies())
            suppliers = tuple(self._purchases.list_suppliers())
            accounts = tuple(self._purchases.list_accounts())
        except Exception as exc:
            QMessageBox.critical(
                self, "Could not open purchase form", str(exc)
            )
            return None
        return currencies, suppliers, accounts

    def _create_purchase(self) -> None:
        reference_data = self._load_reference_data()
        if reference_data is None:
            return
        currencies, suppliers, accounts = reference_data

        if not currencies:
            QMessageBox.warning(
                self,
                "No currencies available",
                "Enable at least one currency before creating purchases.",
            )
            return

        try:
            variants = tuple(self._purchases.list_variant_options())
        except Exception as exc:
            QMessageBox.critical(
                self, "Could not load variants", str(exc)
            )
            return
        if not variants:
            QMessageBox.warning(
                self,
                "No variants available",
                "Create a product with an active variant before registering "
                "a purchase.",
            )
            return

        dialog = PurchaseDialog(
            self._purchases,
            currencies=currencies,
            suppliers=suppliers,
            accounts=accounts,
            variants=variants,
            base_currency=self._base_currency,
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.reload()

    def _show_detail(self, *_args) -> None:
        selected = self._selected_purchase()
        if selected is None:
            return
        try:
            detail = self._purchases.get_purchase_detail(
                selected.purchase_id
            )
        except Exception as exc:
            QMessageBox.critical(
                self, "Could not load purchase", str(exc)
            )
            return
        PurchaseDetailDialog(detail, parent=self).exec()

    def _register_payment(self) -> None:
        selected = self._selected_purchase()
        if selected is None:
            return
        try:
            accounts = tuple(self._purchases.list_accounts())
        except Exception as exc:
            QMessageBox.critical(
                self, "Could not load accounts", str(exc)
            )
            return

        dialog = PurchasePaymentDialog(
            self._purchases,
            selected,
            accounts,
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.reload()

    def _update_status(self) -> None:
        selected = self._selected_purchase()
        if selected is None:
            return
        dialog = PurchaseStatusDialog(
            self._purchases,
            selected,
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.reload()
