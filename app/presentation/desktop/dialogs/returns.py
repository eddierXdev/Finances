"""Customer and supplier return dialogs."""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.application.returns.register_customer_return import (
    CustomerReturnItemRequest,
    RegisterCustomerReturnRequest,
)
from app.application.returns.register_supplier_return import (
    RegisterSupplierReturnRequest,
    SupplierReturnItemRequest,
)
from app.application.returns.service import (
    CustomerReturnContext,
    ReturnablePurchase,
    ReturnableSale,
    ReturnsService,
    SupplierReturnContext,
)
from app.domain.entities.account import Account
from app.domain.enums.return_condition import ReturnCondition
from app.presentation.desktop.form_utils import (
    date_to_datetime,
    parse_optional_money,
)
from app.presentation.desktop.labels import (
    return_condition_label,
    sale_status_label,
)


class CustomerReturnDialog(QDialog):
    """Register a return against a selected sale."""

    def __init__(
        self,
        returns: ReturnsService,
        *,
        sales: Sequence[ReturnableSale],
        accounts: Sequence[Account],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        if not sales:
            raise ValueError("No sale can currently receive a return.")
        self._returns = returns
        self._sales = tuple(sales)
        self._accounts = tuple(account for account in accounts if account.is_active)
        self._context: CustomerReturnContext | None = None
        self._quantities: list[QSpinBox] = []
        self._conditions: list[QComboBox] = []
        self.created_result = None

        self.setWindowTitle("Customer return")
        self.setModal(True)
        self.resize(760, 620)
        self._build_ui()
        self._load_sale()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel("Register customer return", self)
        title.setObjectName("dialogTitle")
        layout.addWidget(title)

        form = QFormLayout()
        self._sale = QComboBox(self)
        self._sale.setObjectName("customerReturnSale")
        for sale in self._sales:
            self._sale.addItem(sale.label, sale.sale_id)
        self._sale.currentIndexChanged.connect(self._load_sale)
        form.addRow("Original sale *", self._sale)

        self._date = QDateEdit(QDate.currentDate(), self)
        self._date.setObjectName("customerReturnDate")
        self._date.setCalendarPopup(True)
        self._date.setDisplayFormat("yyyy-MM-dd")
        form.addRow("Return date *", self._date)

        self._refund = QLineEdit(self)
        self._refund.setObjectName("customerReturnRefund")
        self._refund.setPlaceholderText("Optional refund amount")
        form.addRow("Refund", self._refund)

        self._account = QComboBox(self)
        self._account.setObjectName("customerReturnAccount")
        form.addRow("Refund account", self._account)

        self._notes = QPlainTextEdit(self)
        self._notes.setObjectName("customerReturnNotes")
        self._notes.setPlaceholderText("Optional notes")
        self._notes.setFixedHeight(56)
        form.addRow("Notes", self._notes)
        layout.addLayout(form)

        self._summary = QLabel(self)
        self._summary.setObjectName("dialogSummary")
        self._summary.setWordWrap(True)
        layout.addWidget(self._summary)

        self._lines = QTableWidget(0, 4, self)
        self._lines.setObjectName("customerReturnLinesTable")
        self._lines.setHorizontalHeaderLabels(
            ("Variant", "Returnable", "Quantity", "Condition")
        )
        self._lines.verticalHeader().setVisible(False)
        self._lines.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._lines.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        for column in (1, 2, 3):
            self._lines.horizontalHeader().setSectionResizeMode(
                column, QHeaderView.ResizeMode.ResizeToContents
            )
        layout.addWidget(self._lines, 1)

        hint = QLabel(
            "Sellable units return to stock; damaged units are recorded "
            "without restoring inventory. The return use case validates "
            "historical quantities and refunds.",
            self,
        )
        hint.setObjectName("fieldHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel, self
        )
        create = QPushButton("Register return", self)
        create.setObjectName("createCustomerReturnButton")
        create.setProperty("variant", "primary")
        create.setDefault(True)
        buttons.addButton(create, QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.rejected.connect(self.reject)
        create.clicked.connect(self._submit)
        layout.addWidget(buttons)

    def _load_sale(self, *_args) -> None:
        sale_id = self._sale.currentData()
        if sale_id is None:
            return
        try:
            context = self._returns.get_customer_return_context(sale_id)
        except Exception as exc:
            self._context = None
            self._lines.setRowCount(0)
            self._summary.setText(f"Could not load sale: {exc}")
            return
        self._context = context
        self._summary.setText(
            f"{context.account_name} · {context.currency.code} · "
            f"{sale_status_label(context.status)} · total {context.total}"
        )
        self._refresh_accounts()
        self._fill_lines(context)

    def _refresh_accounts(self) -> None:
        context = self._context
        current = self._account.currentData()
        self._account.clear()
        self._account.addItem("No refund", None)
        if context is not None:
            for account in self._accounts:
                if account.currency.code == context.currency.code:
                    self._account.addItem(
                        f"{account.name} — {account.currency.code}",
                        account.id,
                    )
        if current is not None:
            index = self._account.findData(current)
            if index >= 0:
                self._account.setCurrentIndex(index)

    def _fill_lines(self, context: CustomerReturnContext) -> None:
        self._quantities.clear()
        self._conditions.clear()
        self._lines.setRowCount(len(context.lines))
        for row, line in enumerate(context.lines):
            self._lines.setItem(
                row, 0, QTableWidgetItem(line.variant_label)
            )
            self._lines.setItem(
                row, 1, QTableWidgetItem(str(line.returnable_quantity))
            )
            quantity = QSpinBox(self._lines)
            quantity.setObjectName("customerReturnQuantity")
            quantity.setRange(0, line.returnable_quantity)
            quantity.setValue(0)
            self._lines.setCellWidget(row, 2, quantity)
            self._quantities.append(quantity)

            condition = QComboBox(self._lines)
            condition.setObjectName("customerReturnCondition")
            for value in ReturnCondition:
                condition.addItem(return_condition_label(value), value)
            self._lines.setCellWidget(row, 3, condition)
            self._conditions.append(condition)

    def _submit(self) -> None:
        context = self._context
        if context is None:
            QMessageBox.warning(
                self, "Invalid return", "Load a sale first."
            )
            return
        items = tuple(
            CustomerReturnItemRequest(
                sale_item_id=line.sale_item_id,
                quantity=quantity.value(),
                condition=ReturnCondition(condition.currentData()),
            )
            for line, quantity, condition in zip(
                context.lines,
                self._quantities,
                self._conditions,
                strict=True,
            )
            if quantity.value() > 0
        )
        if not items:
            QMessageBox.warning(
                self,
                "Nothing to return",
                "Enter at least one returned quantity.",
            )
            return

        try:
            refund = parse_optional_money(
                self._refund.text(), context.currency, "Refund"
            )
            if refund is not None and self._account.currentData() is None:
                raise ValueError(
                    "Select the account that pays the refund."
                )
            self.created_result = (
                self._returns.register_customer_return(
                    RegisterCustomerReturnRequest(
                        sale_id=context.sale_id,
                        return_date=date_to_datetime(self._date.date()),
                        items=items,
                        account_id=self._account.currentData(),
                        refund_amount=refund,
                        notes=(
                            self._notes.toPlainText().strip() or None
                        ),
                    )
                )
            )
        except Exception as exc:
            QMessageBox.critical(
                self, "Could not register return", str(exc)
            )
            return
        self.accept()


class SupplierReturnDialog(QDialog):
    """Register a return against exact purchase lots."""

    def __init__(
        self,
        returns: ReturnsService,
        *,
        purchases: Sequence[ReturnablePurchase],
        accounts: Sequence[Account],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        if not purchases:
            raise ValueError("No purchase has stock available to return.")
        self._returns = returns
        self._purchases = tuple(purchases)
        self._accounts = tuple(account for account in accounts if account.is_active)
        self._context: SupplierReturnContext | None = None
        self._quantities: list[QSpinBox] = []
        self.created_result = None

        self.setWindowTitle("Supplier return")
        self.setModal(True)
        self.resize(780, 620)
        self._build_ui()
        self._load_purchase()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel("Register supplier return", self)
        title.setObjectName("dialogTitle")
        layout.addWidget(title)

        form = QFormLayout()
        self._purchase = QComboBox(self)
        self._purchase.setObjectName("supplierReturnPurchase")
        for purchase in self._purchases:
            self._purchase.addItem(purchase.label, purchase.purchase_id)
        self._purchase.currentIndexChanged.connect(self._load_purchase)
        form.addRow("Original purchase *", self._purchase)

        self._date = QDateEdit(QDate.currentDate(), self)
        self._date.setObjectName("supplierReturnDate")
        self._date.setCalendarPopup(True)
        self._date.setDisplayFormat("yyyy-MM-dd")
        form.addRow("Return date *", self._date)

        self._refund = QLineEdit(self)
        self._refund.setObjectName("supplierReturnRefund")
        self._refund.setPlaceholderText("Optional supplier refund")
        form.addRow("Refund", self._refund)

        self._account = QComboBox(self)
        self._account.setObjectName("supplierReturnAccount")
        form.addRow("Refund account", self._account)

        self._notes = QPlainTextEdit(self)
        self._notes.setObjectName("supplierReturnNotes")
        self._notes.setPlaceholderText("Optional notes")
        self._notes.setFixedHeight(56)
        form.addRow("Notes", self._notes)
        layout.addLayout(form)

        self._summary = QLabel(self)
        self._summary.setObjectName("dialogSummary")
        self._summary.setWordWrap(True)
        layout.addWidget(self._summary)

        self._lots = QTableWidget(0, 5, self)
        self._lots.setObjectName("supplierReturnLotsTable")
        self._lots.setHorizontalHeaderLabels(
            ("Variant", "Lot", "Remaining", "Unit cost", "Return qty")
        )
        self._lots.verticalHeader().setVisible(False)
        self._lots.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._lots.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        for column in (1, 2, 3, 4):
            self._lots.horizontalHeader().setSectionResizeMode(
                column, QHeaderView.ResizeMode.ResizeToContents
            )
        layout.addWidget(self._lots, 1)

        hint = QLabel(
            "Returns reference the exact acquisition lot and preserve its "
            "historical unit cost. The use case rejects quantities above the "
            "remaining stock.",
            self,
        )
        hint.setObjectName("fieldHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel, self
        )
        create = QPushButton("Register return", self)
        create.setObjectName("createSupplierReturnButton")
        create.setProperty("variant", "primary")
        create.setDefault(True)
        buttons.addButton(create, QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.rejected.connect(self.reject)
        create.clicked.connect(self._submit)
        layout.addWidget(buttons)

    def _load_purchase(self, *_args) -> None:
        purchase_id = self._purchase.currentData()
        if purchase_id is None:
            return
        try:
            context = self._returns.get_supplier_return_context(purchase_id)
        except Exception as exc:
            self._context = None
            self._lots.setRowCount(0)
            self._summary.setText(f"Could not load purchase: {exc}")
            return
        self._context = context
        self._summary.setText(
            f"{context.supplier_name or 'No supplier'} · "
            f"{context.currency.code} · {len(context.lots)} lots available"
        )
        self._refresh_accounts()
        self._fill_lots(context)

    def _refresh_accounts(self) -> None:
        context = self._context
        current = self._account.currentData()
        self._account.clear()
        self._account.addItem("No refund", None)
        if context is not None:
            for account in self._accounts:
                if account.currency.code == context.currency.code:
                    self._account.addItem(
                        f"{account.name} — {account.currency.code}",
                        account.id,
                    )
        if current is not None:
            index = self._account.findData(current)
            if index >= 0:
                self._account.setCurrentIndex(index)

    def _fill_lots(self, context: SupplierReturnContext) -> None:
        self._quantities.clear()
        self._lots.setRowCount(len(context.lots))
        for row, lot in enumerate(context.lots):
            values = (
                lot.variant_label,
                str(lot.lot_id),
                str(lot.remaining_quantity),
                str(lot.unit_cost),
            )
            for column, value in enumerate(values):
                self._lots.setItem(
                    row, column, QTableWidgetItem(value)
                )
            quantity = QSpinBox(self._lots)
            quantity.setObjectName("supplierReturnQuantity")
            quantity.setRange(0, lot.remaining_quantity)
            quantity.setValue(0)
            self._lots.setCellWidget(row, 4, quantity)
            self._quantities.append(quantity)

    def _submit(self) -> None:
        context = self._context
        if context is None:
            QMessageBox.warning(
                self, "Invalid return", "Load a purchase first."
            )
            return
        items = tuple(
            SupplierReturnItemRequest(
                purchase_item_id=lot.purchase_item_id,
                inventory_lot_id=lot.lot_id,
                quantity=quantity.value(),
            )
            for lot, quantity in zip(
                context.lots, self._quantities, strict=True
            )
            if quantity.value() > 0
        )
        if not items:
            QMessageBox.warning(
                self,
                "Nothing to return",
                "Enter at least one returned quantity.",
            )
            return

        try:
            refund = parse_optional_money(
                self._refund.text(), context.currency, "Refund"
            )
            if refund is not None and self._account.currentData() is None:
                raise ValueError(
                    "Select the account that receives the refund."
                )
            self.created_result = (
                self._returns.register_supplier_return(
                    RegisterSupplierReturnRequest(
                        purchase_id=context.purchase_id,
                        return_date=date_to_datetime(self._date.date()),
                        items=items,
                        account_id=self._account.currentData(),
                        refund_amount=refund,
                        notes=(
                            self._notes.toPlainText().strip() or None
                        ),
                    )
                )
            )
        except Exception as exc:
            QMessageBox.critical(
                self, "Could not register return", str(exc)
            )
            return
        self.accept()
