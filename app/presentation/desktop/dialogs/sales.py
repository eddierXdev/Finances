"""Sale creation and detail dialogs."""

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

from app.application.sales.register_sale import (
    RegisterSaleRequest,
    SaleItemRequest,
)
from app.application.sales.service import (
    SaleDetail,
    SalesService,
    SaleVariantOption,
)
from app.domain.entities.account import Account
from app.domain.entities.currency import Currency
from app.domain.value_objects.money import Money
from app.presentation.desktop.form_utils import (
    date_to_datetime,
    parse_money,
    parse_optional_money,
)
from app.presentation.desktop.labels import sale_status_label


class SaleDialog(QDialog):
    """Collect a fully collected FIFO sale."""

    def __init__(
        self,
        sales: SalesService,
        *,
        currencies: Sequence[Currency],
        accounts: Sequence[Account],
        variants: Sequence[SaleVariantOption],
        base_currency: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        if not currencies:
            raise ValueError("At least one enabled currency is required.")
        if not accounts:
            raise ValueError("At least one active account is required.")
        if not variants:
            raise ValueError("At least one active variant is required.")

        self._sales = sales
        self._currencies = tuple(currencies)
        self._accounts = tuple(account for account in accounts if account.is_active)
        self._variants = tuple(variants)
        self._base_currency = base_currency
        self.created_result = None

        self.setWindowTitle("New sale")
        self.setModal(True)
        self.resize(800, 700)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel("New sale", self)
        title.setObjectName("dialogTitle")
        layout.addWidget(title)

        header = QFormLayout()
        header.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow
        )

        self._date = QDateEdit(QDate.currentDate(), self)
        self._date.setObjectName("saleDate")
        self._date.setCalendarPopup(True)
        self._date.setDisplayFormat("yyyy-MM-dd")
        header.addRow("Sale date *", self._date)

        self._currency = QComboBox(self)
        self._currency.setObjectName("saleCurrency")
        default_index = 0
        for index, currency in enumerate(self._currencies):
            self._currency.addItem(
                f"{currency.code} — {currency.name}", currency
            )
            if currency.code == self._base_currency:
                default_index = index
        self._currency.setCurrentIndex(default_index)
        self._currency.currentIndexChanged.connect(
            self._on_currency_changed
        )
        header.addRow("Currency *", self._currency)

        self._account = QComboBox(self)
        self._account.setObjectName("saleAccount")
        header.addRow("Collected into *", self._account)

        self._discount = QLineEdit(self)
        self._discount.setObjectName("saleDiscount")
        self._discount.setPlaceholderText("Optional order discount")
        header.addRow("Order discount", self._discount)

        self._notes = QPlainTextEdit(self)
        self._notes.setObjectName("saleNotes")
        self._notes.setPlaceholderText("Optional notes")
        self._notes.setFixedHeight(58)
        header.addRow("Notes", self._notes)
        layout.addLayout(header)

        items_group = QGroupBox("Items", self)
        items_layout = QVBoxLayout(items_group)
        self._items = QTableWidget(0, 4, items_group)
        self._items.setObjectName("saleItemsTable")
        self._items.setHorizontalHeaderLabels(
            ("Variant *", "Quantity *", "Unit price *", "Line discount")
        )
        self._items.verticalHeader().setVisible(False)
        self._items.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._items.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        for column in (1, 2, 3):
            self._items.horizontalHeader().setSectionResizeMode(
                column, QHeaderView.ResizeMode.ResizeToContents
            )
        items_layout.addWidget(self._items)

        buttons = QHBoxLayout()
        add_item = QPushButton("Add item", items_group)
        add_item.setObjectName("addSaleItemButton")
        add_item.clicked.connect(self._add_item_row)
        buttons.addWidget(add_item)
        remove = QPushButton("Remove item", items_group)
        remove.setObjectName("removeSaleItemButton")
        remove.clicked.connect(self._remove_selected)
        buttons.addWidget(remove)
        buttons.addStretch(1)
        items_layout.addLayout(buttons)
        layout.addWidget(items_group, 1)

        hint = QLabel(
            "Stock is consumed oldest first. The application calculates "
            "revenue, COGS and profit; the dialog forwards the request.",
            self,
        )
        hint.setObjectName("fieldHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        dialog_buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel, self
        )
        create = QPushButton("Register sale", self)
        create.setObjectName("createSaleButton")
        create.setProperty("variant", "primary")
        create.setDefault(True)
        dialog_buttons.addButton(
            create, QDialogButtonBox.ButtonRole.AcceptRole
        )
        dialog_buttons.rejected.connect(self.reject)
        create.clicked.connect(self._submit)
        layout.addWidget(dialog_buttons)

        self._refresh_accounts()
        self._add_item_row()

    def _refresh_accounts(self, *_args) -> None:
        currency = self._currency.currentData()
        self._account.clear()
        if isinstance(currency, Currency):
            for account in self._accounts:
                if account.currency.code == currency.code:
                    self._account.addItem(
                        f"{account.name} — {account.currency.code}",
                        account.id,
                    )

    def _on_currency_changed(self, *_args) -> None:
        self._refresh_accounts()
        self._discount.clear()
        for row in range(self._items.rowCount()):
            variant = self._items.cellWidget(row, 0)
            price = self._items.cellWidget(row, 2)
            discount = self._items.cellWidget(row, 3)
            if isinstance(price, QLineEdit):
                price.clear()
            if isinstance(discount, QLineEdit):
                discount.clear()
            if isinstance(variant, QComboBox) and isinstance(
                price, QLineEdit
            ):
                self._apply_default_price(variant, price)

    def _add_item_row(self) -> None:
        row = self._items.rowCount()
        self._items.insertRow(row)

        variant = QComboBox(self._items)
        variant.setObjectName("saleItemVariant")
        for option in self._variants:
            variant.addItem(
                f"{option.label} · {option.on_hand} in stock",
                option.variant_id,
            )
        self._items.setCellWidget(row, 0, variant)

        quantity = QSpinBox(self._items)
        quantity.setObjectName("saleItemQuantity")
        quantity.setRange(1, 1_000_000)
        quantity.setValue(1)
        self._items.setCellWidget(row, 1, quantity)

        price = QLineEdit(self._items)
        price.setObjectName("saleItemPrice")
        price.setPlaceholderText("0.00")
        self._items.setCellWidget(row, 2, price)

        discount = QLineEdit(self._items)
        discount.setObjectName("saleItemDiscount")
        discount.setPlaceholderText("Optional")
        self._items.setCellWidget(row, 3, discount)

        variant.currentIndexChanged.connect(
            lambda _index, combo=variant, price_field=price: (
                self._apply_default_price(combo, price_field)
            )
        )
        self._apply_default_price(variant, price)

    def _apply_default_price(
        self, variant: QComboBox, price: QLineEdit
    ) -> None:
        currency = self._currency.currentData()
        variant_id = variant.currentData()
        if not isinstance(currency, Currency):
            return
        option = next(
            (
                item
                for item in self._variants
                if item.variant_id == variant_id
            ),
            None,
        )
        if (
            option is not None
            and option.default_selling_price is not None
            and option.default_selling_price.currency.code
            == currency.code
        ):
            price.setText(str(option.default_selling_price.amount))

    def _remove_selected(self) -> None:
        rows = sorted(
            {index.row() for index in self._items.selectedIndexes()},
            reverse=True,
        )
        for row in rows:
            self._items.removeRow(row)

    def _submit(self) -> None:
        currency = self._currency.currentData()
        account_id = self._account.currentData()
        if not isinstance(currency, Currency):
            QMessageBox.warning(
                self, "Invalid sale", "Select a sale currency."
            )
            return
        if account_id is None:
            QMessageBox.warning(
                self,
                "Invalid sale",
                "No active account uses the selected currency.",
            )
            return
        if self._items.rowCount() == 0:
            QMessageBox.warning(
                self, "Invalid sale", "Add at least one item."
            )
            return

        try:
            items = self._collect_items(currency)
            discount = parse_optional_money(
                self._discount.text(), currency, "Order discount"
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid sale", str(exc))
            return

        try:
            self.created_result = self._sales.register_sale(
                RegisterSaleRequest(
                    account_id=account_id,
                    currency=currency,
                    sale_date=date_to_datetime(self._date.date()),
                    items=items,
                    discount_amount=discount,
                    notes=self._notes.toPlainText().strip() or None,
                )
            )
        except Exception as exc:
            QMessageBox.critical(
                self, "Could not register sale", str(exc)
            )
            return
        self.accept()

    def _collect_items(
        self, currency: Currency
    ) -> tuple[SaleItemRequest, ...]:
        items: list[SaleItemRequest] = []
        for row in range(self._items.rowCount()):
            variant = self._items.cellWidget(row, 0)
            quantity = self._items.cellWidget(row, 1)
            price = self._items.cellWidget(row, 2)
            discount = self._items.cellWidget(row, 3)
            if (
                not isinstance(variant, QComboBox)
                or not isinstance(quantity, QSpinBox)
                or not isinstance(price, QLineEdit)
                or not isinstance(discount, QLineEdit)
            ):
                raise ValueError(f"Item {row + 1} is incomplete.")
            variant_id = variant.currentData()
            if variant_id is None:
                raise ValueError(f"Item {row + 1}: select a variant.")
            items.append(
                SaleItemRequest(
                    variant_id=variant_id,
                    quantity=quantity.value(),
                    unit_price=parse_money(
                        price.text(),
                        currency,
                        f"Item {row + 1} unit price",
                    ),
                    discount_amount=parse_optional_money(
                        discount.text(),
                        currency,
                        f"Item {row + 1} discount",
                    ),
                )
            )
        return tuple(items)


class SaleDetailDialog(QDialog):
    """Read-only sale, line and FIFO allocation detail."""

    def __init__(
        self,
        detail: SaleDetail,
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._detail = detail
        self.setWindowTitle("Sale detail")
        self.setModal(True)
        self.resize(760, 600)
        self._build_ui()

    def _build_ui(self) -> None:
        sale = self._detail.sale
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(10)

        title = QLabel(f"Sale #{sale.sale_id}", self)
        title.setObjectName("dialogTitle")
        layout.addWidget(title)

        summary = QFormLayout()
        summary.addRow(
            "Date", QLabel(sale.sale_date.date().isoformat(), self)
        )
        summary.addRow("Account", QLabel(sale.account_name, self))
        summary.addRow("Status", QLabel(sale_status_label(sale.status), self))
        summary.addRow("Total", QLabel(str(sale.total), self))
        summary.addRow(
            "COGS",
            QLabel(
                " + ".join(str(value) for value in sale.cogs) or "—",
                self,
            ),
        )
        summary.addRow(
            "Gross profit",
            QLabel(
                " + ".join(
                    str(value) for value in sale.gross_profit
                )
                or "Mixed currencies",
                self,
            ),
        )
        if sale.notes:
            summary.addRow("Notes", QLabel(sale.notes, self))
        layout.addLayout(summary)

        lines_group = QGroupBox("Items", self)
        lines_layout = QVBoxLayout(lines_group)
        lines = QTableWidget(len(self._detail.lines), 5, lines_group)
        lines.setObjectName("saleDetailLinesTable")
        lines.setHorizontalHeaderLabels(
            ("Variant", "Quantity", "Unit price", "Discount", "Line total")
        )
        lines.verticalHeader().setVisible(False)
        lines.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        lines.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        for row, line in enumerate(self._detail.lines):
            values = (
                line.variant_label,
                str(line.quantity),
                str(line.unit_price),
                str(line.discount_amount) if line.discount_amount else "—",
                str(line.line_total),
            )
            for column, value in enumerate(values):
                lines.setItem(row, column, QTableWidgetItem(value))
        lines_layout.addWidget(lines)
        layout.addWidget(lines_group, 1)

        allocations_group = QGroupBox("FIFO allocations", self)
        allocations_layout = QVBoxLayout(allocations_group)
        allocations = QTableWidget(
            len(self._detail.allocations), 5, allocations_group
        )
        allocations.setObjectName("saleDetailAllocationsTable")
        allocations.setHorizontalHeaderLabels(
            ("Variant", "Lot", "Quantity", "Unit cost", "COGS")
        )
        allocations.verticalHeader().setVisible(False)
        allocations.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        allocations.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        for row, allocation in enumerate(self._detail.allocations):
            values = (
                allocation.variant_label,
                str(allocation.lot_id),
                str(allocation.quantity),
                str(allocation.unit_cost),
                str(allocation.cost),
            )
            for column, value in enumerate(values):
                allocations.setItem(
                    row, column, QTableWidgetItem(value)
                )
        allocations_layout.addWidget(allocations)
        layout.addWidget(allocations_group)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close, self
        )
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
