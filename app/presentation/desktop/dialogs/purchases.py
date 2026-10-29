"""Dialogs for suppliers, purchases, payments, status and detail."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
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

from app.application.purchases.list_purchases import (
    PurchaseDetail,
    PurchaseListItem,
    VariantOption,
)
from app.application.purchases.register_purchase import (
    PurchaseCostRequest,
    PurchaseItemRequest,
    RegisterPurchaseRequest,
)
from app.application.purchases.register_purchase_payment import (
    RegisterPurchasePaymentRequest,
)
from app.application.purchases.service import PurchaseService
from app.application.purchases.update_purchase_status import (
    UpdatePurchaseStatusRequest,
)
from app.application.suppliers.create_supplier import CreateSupplierRequest
from app.domain.entities.account import Account
from app.domain.entities.currency import Currency
from app.domain.entities.supplier import Supplier
from app.domain.enums.allocation_method import AllocationMethod
from app.domain.enums.purchase_cost_type import PurchaseCostType
from app.domain.enums.purchase_status import PurchaseStatus
from app.domain.value_objects.money import Money
from app.presentation.desktop.labels import (
    allocation_method_label,
    purchase_cost_type_label,
    purchase_status_label,
)

_AUTOMATIC_ALLOCATIONS = (
    AllocationMethod.BY_QUANTITY,
    AllocationMethod.BY_VALUE,
    AllocationMethod.BY_WEIGHT,
)


class SupplierDialog(QDialog):
    """Collect and persist a new supplier."""

    def __init__(
        self,
        purchases: PurchaseService,
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._purchases = purchases
        self.created_supplier: Supplier | None = None
        self.setWindowTitle("New supplier")
        self.setModal(True)
        self.resize(460, 390)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel("New supplier", self)
        title.setObjectName("dialogTitle")
        layout.addWidget(title)

        form = QFormLayout()
        self._name = QLineEdit(self)
        self._name.setObjectName("supplierName")
        self._name.setPlaceholderText("For example: Acme Trading")
        form.addRow("Name *", self._name)

        self._type = QLineEdit(self)
        self._type.setObjectName("supplierType")
        self._type.setPlaceholderText("Optional, for example: Wholesaler")
        form.addRow("Type", self._type)

        self._contact = QLineEdit(self)
        self._contact.setObjectName("supplierContact")
        self._contact.setPlaceholderText("Optional contact details")
        form.addRow("Contact", self._contact)

        self._website = QLineEdit(self)
        self._website.setObjectName("supplierWebsite")
        self._website.setPlaceholderText("Optional website")
        form.addRow("Website", self._website)

        self._notes = QPlainTextEdit(self)
        self._notes.setObjectName("supplierNotes")
        self._notes.setPlaceholderText("Optional notes")
        self._notes.setFixedHeight(70)
        form.addRow("Notes", self._notes)

        layout.addLayout(form)
        layout.addStretch(1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel, self
        )
        create = QPushButton("Create supplier", self)
        create.setObjectName("createSupplierButton")
        create.setProperty("variant", "primary")
        create.setDefault(True)
        buttons.addButton(create, QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.rejected.connect(self.reject)
        create.clicked.connect(self._submit)
        layout.addWidget(buttons)

    def _submit(self) -> None:
        name = self._name.text().strip()
        if not name:
            QMessageBox.warning(
                self, "Invalid supplier", "Name is required."
            )
            return

        try:
            self.created_supplier = self._purchases.create_supplier(
                CreateSupplierRequest(
                    name=name,
                    supplier_type=self._type.text().strip() or None,
                    contact=self._contact.text().strip() or None,
                    website=self._website.text().strip() or None,
                    notes=self._notes.toPlainText().strip() or None,
                )
            )
        except Exception as exc:
            QMessageBox.critical(
                self, "Could not create supplier", str(exc)
            )
            return

        self.accept()


class PurchaseDialog(QDialog):
    """Collect and persist a purchase with items and automatic costs."""

    def __init__(
        self,
        purchases: PurchaseService,
        *,
        currencies: Sequence[Currency],
        suppliers: Sequence[Supplier],
        accounts: Sequence[Account],
        variants: Sequence[VariantOption],
        base_currency: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        if not currencies:
            raise ValueError("At least one enabled currency is required.")
        if not variants:
            raise ValueError("At least one active variant is required.")

        self._purchases = purchases
        self._currencies = tuple(currencies)
        self._suppliers = tuple(suppliers)
        self._accounts = tuple(accounts)
        self._variants = tuple(variants)
        self._base_currency = base_currency

        self.setWindowTitle("New purchase")
        self.setModal(True)
        self.resize(780, 740)
        self._build_ui()
        self._refresh_accounts()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel("New purchase", self)
        title.setObjectName("dialogTitle")
        layout.addWidget(title)

        header = QFormLayout()
        header.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow
        )

        self._date = QDateEdit(QDate.currentDate(), self)
        self._date.setObjectName("purchaseDate")
        self._date.setCalendarPopup(True)
        self._date.setDisplayFormat("yyyy-MM-dd")
        header.addRow("Purchase date *", self._date)

        self._currency = QComboBox(self)
        self._currency.setObjectName("purchaseCurrency")
        default_index = 0
        for index, currency in enumerate(self._currencies):
            self._currency.addItem(
                f"{currency.code} — {currency.name}", currency
            )
            if currency.code == self._base_currency:
                default_index = index
        self._currency.setCurrentIndex(default_index)
        self._currency.currentIndexChanged.connect(self._refresh_accounts)
        header.addRow("Purchase currency *", self._currency)

        supplier_row = QHBoxLayout()
        self._supplier = QComboBox(self)
        self._supplier.setObjectName("purchaseSupplier")
        supplier_row.addWidget(self._supplier, 1)
        new_supplier = QPushButton("New supplier", self)
        new_supplier.setObjectName("newSupplierFromPurchaseButton")
        new_supplier.clicked.connect(self._create_supplier)
        supplier_row.addWidget(new_supplier)
        header.addRow("Supplier", supplier_row)
        self._reload_suppliers()

        self._account = QComboBox(self)
        self._account.setObjectName("purchasePaymentAccount")
        header.addRow("Payment account", self._account)

        payment_hint = QLabel(
            "Choose an account to record the full payment immediately. "
            "Leave it empty to register the purchase as pending.",
            self,
        )
        payment_hint.setObjectName("fieldHint")
        payment_hint.setWordWrap(True)
        header.addRow(payment_hint)

        self._order_number = QLineEdit(self)
        self._order_number.setObjectName("purchaseOrderNumber")
        self._order_number.setPlaceholderText("Optional order number")
        header.addRow("Order number", self._order_number)

        self._tracking_number = QLineEdit(self)
        self._tracking_number.setObjectName("purchaseTrackingNumber")
        self._tracking_number.setPlaceholderText(
            "Optional tracking number"
        )
        header.addRow("Tracking number", self._tracking_number)

        self._notes = QPlainTextEdit(self)
        self._notes.setObjectName("purchaseNotes")
        self._notes.setPlaceholderText("Optional notes")
        self._notes.setFixedHeight(60)
        header.addRow("Notes", self._notes)

        layout.addLayout(header)

        items_group = QGroupBox("Items", self)
        items_group.setObjectName("purchaseItemsGroup")
        items_layout = QVBoxLayout(items_group)
        self._items_table = QTableWidget(0, 4, items_group)
        self._items_table.setObjectName("purchaseItemsTable")
        self._items_table.setHorizontalHeaderLabels(
            ("Variant *", "Quantity *", "Unit price *", "Weight")
        )
        self._items_table.verticalHeader().setVisible(False)
        self._items_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._items_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        for column in (1, 2, 3):
            self._items_table.horizontalHeader().setSectionResizeMode(
                column, QHeaderView.ResizeMode.ResizeToContents
            )
        items_layout.addWidget(self._items_table)

        item_buttons = QHBoxLayout()
        add_item = QPushButton("Add item", items_group)
        add_item.setObjectName("addPurchaseItemButton")
        add_item.clicked.connect(self._add_item_row)
        item_buttons.addWidget(add_item)
        remove_item = QPushButton("Remove item", items_group)
        remove_item.setObjectName("removePurchaseItemButton")
        remove_item.clicked.connect(
            lambda: self._remove_selected(self._items_table)
        )
        item_buttons.addWidget(remove_item)
        item_buttons.addStretch(1)
        items_layout.addLayout(item_buttons)
        layout.addWidget(items_group)

        costs_group = QGroupBox("Additional costs (optional)", self)
        costs_group.setObjectName("purchaseCostsGroup")
        costs_layout = QVBoxLayout(costs_group)
        self._costs_table = QTableWidget(0, 4, costs_group)
        self._costs_table.setObjectName("purchaseCostsTable")
        self._costs_table.setHorizontalHeaderLabels(
            ("Type", "Amount *", "Allocation", "Description")
        )
        self._costs_table.verticalHeader().setVisible(False)
        self._costs_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._costs_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self._costs_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self._costs_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self._costs_table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.Stretch
        )
        costs_layout.addWidget(self._costs_table)

        cost_note = QLabel(
            "Costs use the purchase currency and are allocated by quantity, "
            "value or weight. Weight allocation requires a weight on every "
            "item.",
            costs_group,
        )
        cost_note.setObjectName("fieldHint")
        cost_note.setWordWrap(True)
        costs_layout.addWidget(cost_note)

        cost_buttons = QHBoxLayout()
        add_cost = QPushButton("Add cost", costs_group)
        add_cost.setObjectName("addPurchaseCostButton")
        add_cost.clicked.connect(self._add_cost_row)
        cost_buttons.addWidget(add_cost)
        remove_cost = QPushButton("Remove cost", costs_group)
        remove_cost.setObjectName("removePurchaseCostButton")
        remove_cost.clicked.connect(
            lambda: self._remove_selected(self._costs_table)
        )
        cost_buttons.addWidget(remove_cost)
        cost_buttons.addStretch(1)
        costs_layout.addLayout(cost_buttons)
        layout.addWidget(costs_group)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel, self
        )
        create = QPushButton("Create purchase", self)
        create.setObjectName("createPurchaseButton")
        create.setProperty("variant", "primary")
        create.setDefault(True)
        buttons.addButton(create, QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.rejected.connect(self.reject)
        create.clicked.connect(self._submit)
        layout.addWidget(buttons)

        self._add_item_row()

    def _reload_suppliers(self, select_id: int | None = None) -> None:
        current = (
            select_id
            if select_id is not None
            else self._supplier.currentData()
        )
        self._supplier.blockSignals(True)
        self._supplier.clear()
        self._supplier.addItem("No supplier", None)
        for supplier in self._suppliers:
            self._supplier.addItem(supplier.name, supplier.id)
        if current is not None:
            index = self._supplier.findData(current)
            if index >= 0:
                self._supplier.setCurrentIndex(index)
        self._supplier.blockSignals(False)

    def _create_supplier(self) -> None:
        dialog = SupplierDialog(self._purchases, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self._refresh_suppliers(select_id=dialog.created_supplier.id)

    def _refresh_suppliers(self, *, select_id: int | None) -> None:
        try:
            suppliers = self._purchases.list_suppliers()
        except Exception as exc:
            QMessageBox.critical(
                self, "Could not load suppliers", str(exc)
            )
            return
        self._suppliers = tuple(suppliers)
        self._reload_suppliers(select_id)

    def _refresh_accounts(self, *_args) -> None:
        currency = self._currency.currentData()
        self._account.blockSignals(True)
        self._account.clear()
        self._account.addItem("Pay later (pending)", None)
        if isinstance(currency, Currency):
            for account in self._accounts:
                if (
                    account.is_active
                    and account.currency.code == currency.code
                ):
                    self._account.addItem(
                        f"{account.name} — {account.currency.code}",
                        account.id,
                    )
        self._account.blockSignals(False)

    def _add_item_row(self) -> None:
        row = self._items_table.rowCount()
        self._items_table.insertRow(row)

        variant = QComboBox(self._items_table)
        variant.setObjectName("purchaseItemVariant")
        for option in self._variants:
            variant.addItem(option.label, option.variant_id)
        self._items_table.setCellWidget(row, 0, variant)

        quantity = QSpinBox(self._items_table)
        quantity.setObjectName("purchaseItemQuantity")
        quantity.setRange(1, 1_000_000)
        quantity.setValue(1)
        self._items_table.setCellWidget(row, 1, quantity)

        price = QLineEdit(self._items_table)
        price.setObjectName("purchaseItemPrice")
        price.setPlaceholderText("0.00")
        self._items_table.setCellWidget(row, 2, price)

        weight = QLineEdit(self._items_table)
        weight.setObjectName("purchaseItemWeight")
        weight.setPlaceholderText("Optional")
        self._items_table.setCellWidget(row, 3, weight)

    def _add_cost_row(self) -> None:
        row = self._costs_table.rowCount()
        self._costs_table.insertRow(row)

        cost_type = QComboBox(self._costs_table)
        cost_type.setObjectName("purchaseCostType")
        for value in PurchaseCostType:
            cost_type.addItem(purchase_cost_type_label(value), value)
        self._costs_table.setCellWidget(row, 0, cost_type)

        amount = QLineEdit(self._costs_table)
        amount.setObjectName("purchaseCostAmount")
        amount.setPlaceholderText("0.00")
        self._costs_table.setCellWidget(row, 1, amount)

        allocation = QComboBox(self._costs_table)
        allocation.setObjectName("purchaseCostAllocation")
        for value in _AUTOMATIC_ALLOCATIONS:
            allocation.addItem(allocation_method_label(value), value)
        self._costs_table.setCellWidget(row, 2, allocation)

        description = QLineEdit(self._costs_table)
        description.setObjectName("purchaseCostDescription")
        description.setPlaceholderText("Optional")
        self._costs_table.setCellWidget(row, 3, description)

    @staticmethod
    def _remove_selected(table: QTableWidget) -> None:
        rows = sorted(
            {index.row() for index in table.selectedIndexes()},
            reverse=True,
        )
        for row in rows:
            table.removeRow(row)

    def _submit(self) -> None:
        currency = self._currency.currentData()
        if not isinstance(currency, Currency):
            QMessageBox.warning(
                self, "Invalid purchase", "Select a currency."
            )
            return
        if self._items_table.rowCount() == 0:
            QMessageBox.warning(
                self, "Invalid purchase", "Add at least one item."
            )
            return

        try:
            items = self._collect_items(currency)
            costs = self._collect_costs(currency)
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid purchase", str(exc))
            return

        request = RegisterPurchaseRequest(
            currency=currency,
            purchase_date=_date_to_datetime(self._date.date()),
            items=items,
            costs=costs,
            supplier_id=self._supplier.currentData(),
            account_id=self._account.currentData(),
            order_number=self._order_number.text().strip() or None,
            tracking_number=(
                self._tracking_number.text().strip() or None
            ),
            notes=self._notes.toPlainText().strip() or None,
        )

        try:
            self._purchases.create_purchase(request)
        except Exception as exc:
            QMessageBox.critical(
                self, "Could not create purchase", str(exc)
            )
            return
        self.accept()

    def _collect_items(
        self, currency: Currency
    ) -> tuple[PurchaseItemRequest, ...]:
        items: list[PurchaseItemRequest] = []
        for row in range(self._items_table.rowCount()):
            variant = self._items_table.cellWidget(row, 0)
            quantity = self._items_table.cellWidget(row, 1)
            price = self._items_table.cellWidget(row, 2)
            weight = self._items_table.cellWidget(row, 3)

            if (
                not isinstance(variant, QComboBox)
                or not isinstance(quantity, QSpinBox)
                or not isinstance(price, QLineEdit)
                or not isinstance(weight, QLineEdit)
            ):
                raise ValueError(f"Item {row + 1} is incomplete.")
            variant_id = variant.currentData()
            if variant_id is None:
                raise ValueError(f"Item {row + 1}: select a variant.")

            items.append(
                PurchaseItemRequest(
                    variant_id=variant_id,
                    quantity=quantity.value(),
                    unit_price=_parse_money(
                        price.text(),
                        currency,
                        f"Item {row + 1} unit price",
                    ),
                    weight=_parse_optional_decimal(
                        weight.text(),
                        f"Item {row + 1} weight",
                    ),
                )
            )
        return tuple(items)

    def _collect_costs(
        self, currency: Currency
    ) -> tuple[PurchaseCostRequest, ...]:
        costs: list[PurchaseCostRequest] = []
        for row in range(self._costs_table.rowCount()):
            cost_type = self._costs_table.cellWidget(row, 0)
            amount = self._costs_table.cellWidget(row, 1)
            allocation = self._costs_table.cellWidget(row, 2)
            description = self._costs_table.cellWidget(row, 3)

            if (
                not isinstance(cost_type, QComboBox)
                or not isinstance(amount, QLineEdit)
                or not isinstance(allocation, QComboBox)
                or not isinstance(description, QLineEdit)
            ):
                raise ValueError(f"Cost {row + 1} is incomplete.")

            try:
                type_value = PurchaseCostType(cost_type.currentData())
                allocation_value = AllocationMethod(
                    allocation.currentData()
                )
            except ValueError as exc:
                raise ValueError(
                    f"Cost {row + 1}: select a valid type and allocation."
                ) from exc

            costs.append(
                PurchaseCostRequest(
                    cost_type=type_value,
                    amount=_parse_money(
                        amount.text(),
                        currency,
                        f"Cost {row + 1} amount",
                    ),
                    allocation_method=allocation_value,
                    description=description.text().strip() or None,
                )
            )
        return tuple(costs)


class PurchasePaymentDialog(QDialog):
    """Record the single full payment allowed by V1."""

    def __init__(
        self,
        purchases: PurchaseService,
        purchase: PurchaseListItem,
        accounts: Sequence[Account],
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._purchases = purchases
        self._purchase = purchase
        self._accounts = tuple(
            account
            for account in accounts
            if account.is_active
            and account.currency.code == purchase.currency_code
        )

        self.setWindowTitle("Register purchase payment")
        self.setModal(True)
        self.resize(470, 300)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel("Register full payment", self)
        title.setObjectName("dialogTitle")
        layout.addWidget(title)

        summary = QLabel(
            f"Purchase #{self._purchase.purchase_id} · "
            f"{self._purchase.total}",
            self,
        )
        summary.setObjectName("dialogSummary")
        layout.addWidget(summary)

        form = QFormLayout()
        self._account = QComboBox(self)
        self._account.setObjectName("purchasePaymentDialogAccount")
        for account in self._accounts:
            self._account.addItem(
                f"{account.name} — {account.currency.code}", account.id
            )
        form.addRow("Pay from *", self._account)

        self._date = QDateEdit(QDate.currentDate(), self)
        self._date.setObjectName("purchasePaymentDate")
        self._date.setCalendarPopup(True)
        self._date.setDisplayFormat("yyyy-MM-dd")
        form.addRow("Payment date *", self._date)
        layout.addLayout(form)

        if not self._accounts:
            warning = QLabel(
                "No active account uses this purchase currency. Create or "
                "activate a matching account first.",
                self,
            )
            warning.setObjectName("errorBanner")
            warning.setWordWrap(True)
            layout.addWidget(warning)

        layout.addStretch(1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel, self
        )
        pay = QPushButton("Register payment", self)
        pay.setObjectName("registerPurchasePaymentButton")
        pay.setProperty("variant", "primary")
        pay.setDefault(True)
        pay.setEnabled(bool(self._accounts))
        buttons.addButton(pay, QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.rejected.connect(self.reject)
        pay.clicked.connect(self._submit)
        layout.addWidget(buttons)

    def _submit(self) -> None:
        account_id = self._account.currentData()
        if account_id is None:
            QMessageBox.warning(
                self, "Invalid payment", "Select a payment account."
            )
            return
        try:
            self._purchases.register_payment(
                RegisterPurchasePaymentRequest(
                    purchase_id=self._purchase.purchase_id,
                    account_id=account_id,
                    payment_date=_date_to_datetime(self._date.date()),
                )
            )
        except Exception as exc:
            QMessageBox.critical(
                self, "Could not register payment", str(exc)
            )
            return
        self.accept()


class PurchaseStatusDialog(QDialog):
    """Apply one allowed logistics transition."""

    def __init__(
        self,
        purchases: PurchaseService,
        purchase: PurchaseListItem,
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        if not purchase.allowed_statuses:
            raise ValueError("This purchase has no logistics transition.")

        self._purchases = purchases
        self._purchase = purchase
        self.setWindowTitle("Update purchase status")
        self.setModal(True)
        self.resize(430, 220)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel("Update purchase status", self)
        title.setObjectName("dialogTitle")
        layout.addWidget(title)

        current = QLabel(
            f"Current status: "
            f"{purchase_status_label(self._purchase.status)}",
            self,
        )
        current.setObjectName("dialogSummary")
        layout.addWidget(current)

        form = QFormLayout()
        self._status = QComboBox(self)
        self._status.setObjectName("purchaseTargetStatus")
        for status in self._purchase.allowed_statuses:
            self._status.addItem(purchase_status_label(status), status)
        form.addRow("New status *", self._status)
        layout.addLayout(form)
        layout.addStretch(1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel, self
        )
        update = QPushButton("Update status", self)
        update.setObjectName("updatePurchaseStatusButton")
        update.setProperty("variant", "primary")
        update.setDefault(True)
        buttons.addButton(update, QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.rejected.connect(self.reject)
        update.clicked.connect(self._submit)
        layout.addWidget(buttons)

    def _submit(self) -> None:
        raw_status = self._status.currentData()
        if raw_status is None:
            QMessageBox.warning(
                self, "Invalid status", "Select a new status."
            )
            return
        try:
            status = PurchaseStatus(raw_status)
        except ValueError:
            QMessageBox.warning(
                self, "Invalid status", "Select a valid status."
            )
            return

        try:
            self._purchases.update_status(
                UpdatePurchaseStatusRequest(
                    purchase_id=self._purchase.purchase_id,
                    status=status,
                )
            )
        except Exception as exc:
            QMessageBox.critical(
                self, "Could not update purchase", str(exc)
            )
            return
        self.accept()


class PurchaseDetailDialog(QDialog):
    """Read-only view of a purchase's items and costs."""

    def __init__(
        self,
        detail: PurchaseDetail,
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._detail = detail
        self.setWindowTitle("Purchase detail")
        self.setModal(True)
        self.resize(720, 560)
        self._build_ui()

    def _build_ui(self) -> None:
        purchase = self._detail.purchase
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(10)

        title = QLabel(f"Purchase #{purchase.purchase_id}", self)
        title.setObjectName("dialogTitle")
        layout.addWidget(title)

        summary = QFormLayout()
        summary.addRow(
            "Date",
            QLabel(purchase.purchase_date.date().isoformat(), self),
        )
        summary.addRow(
            "Supplier", QLabel(_value(purchase.supplier_name), self)
        )
        summary.addRow(
            "Status", QLabel(purchase_status_label(purchase.status), self)
        )
        summary.addRow("Total", QLabel(str(purchase.total), self))
        summary.addRow("Payment", QLabel(_value(purchase.account_name), self))
        summary.addRow("Order", QLabel(_value(purchase.order_number), self))
        summary.addRow(
            "Tracking", QLabel(_value(purchase.tracking_number), self)
        )
        if purchase.notes:
            summary.addRow("Notes", QLabel(purchase.notes, self))
        layout.addLayout(summary)

        items_group = QGroupBox("Items", self)
        items_layout = QVBoxLayout(items_group)
        items_table = QTableWidget(len(self._detail.items), 5, items_group)
        items_table.setObjectName("purchaseDetailItemsTable")
        items_table.setHorizontalHeaderLabels(
            ("Variant", "Quantity", "Unit price", "Line total", "Weight")
        )
        items_table.verticalHeader().setVisible(False)
        items_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        items_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        for row, item in enumerate(self._detail.items):
            values = (
                item.variant_label,
                str(item.quantity),
                str(item.unit_price),
                str(item.line_total),
                item.weight or "—",
            )
            for column, value in enumerate(values):
                items_table.setItem(
                    row, column, QTableWidgetItem(value)
                )
        items_layout.addWidget(items_table)
        layout.addWidget(items_group, 1)

        costs_group = QGroupBox("Additional costs", self)
        costs_layout = QVBoxLayout(costs_group)
        if self._detail.costs:
            costs_table = QTableWidget(
                len(self._detail.costs), 5, costs_group
            )
            costs_table.setObjectName("purchaseDetailCostsTable")
            costs_table.setHorizontalHeaderLabels(
                ("Type", "Amount", "Normalized", "Allocation", "Description")
            )
            costs_table.verticalHeader().setVisible(False)
            costs_table.setEditTriggers(
                QAbstractItemView.EditTrigger.NoEditTriggers
            )
            costs_table.horizontalHeader().setSectionResizeMode(
                4, QHeaderView.ResizeMode.Stretch
            )
            for row, cost in enumerate(self._detail.costs):
                values = (
                    purchase_cost_type_label(cost.cost_type),
                    str(cost.amount),
                    str(cost.normalized_amount),
                    allocation_method_label(cost.allocation_method),
                    cost.description or "—",
                )
                for column, value in enumerate(values):
                    costs_table.setItem(
                        row, column, QTableWidgetItem(value)
                    )
            costs_layout.addWidget(costs_table)
        else:
            empty = QLabel("No additional costs.", costs_group)
            empty.setObjectName("emptyStateHint")
            costs_layout.addWidget(empty)
        layout.addWidget(costs_group)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close, self
        )
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


def _date_to_datetime(value: QDate) -> datetime:
    return datetime(
        value.year(),
        value.month(),
        value.day(),
        tzinfo=UTC,
    )


def _parse_money(text: str, currency: Currency, field: str) -> Money:
    normalized = text.strip().replace(",", ".")
    if not normalized:
        raise ValueError(f"{field} is required.")
    try:
        amount = Decimal(normalized)
    except InvalidOperation as exc:
        raise ValueError(f"{field} must be a number.") from exc
    return Money(amount, currency)


def _parse_optional_decimal(text: str, field: str) -> Decimal | None:
    normalized = text.strip().replace(",", ".")
    if not normalized:
        return None
    try:
        value = Decimal(normalized)
    except InvalidOperation as exc:
        raise ValueError(f"{field} must be a number.") from exc
    if value <= 0:
        raise ValueError(f"{field} must be greater than zero.")
    return value


def _value(value: object | None) -> str:
    return "—" if value is None else str(value)
