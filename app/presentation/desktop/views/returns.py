"""Returns screen for customer and supplier returns."""

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

from app.application.returns.service import (
    CustomerReturnRow,
    ReturnsService,
    SupplierReturnRow,
)
from app.presentation.desktop.dialogs.returns import (
    CustomerReturnDialog,
    SupplierReturnDialog,
)
from app.presentation.desktop.form_utils import display_datetime
from app.presentation.desktop.table_model import ReadOnlyTableModel


class ReturnsPage(QWidget):
    """Browse return history and register returns against exact documents."""

    def __init__(
        self,
        returns: ReturnsService,
        *,
        base_currency: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._returns = returns
        self._base_currency = base_currency
        self._customer_rows: tuple[CustomerReturnRow, ...] = ()
        self._supplier_rows: tuple[SupplierReturnRow, ...] = ()
        self.setObjectName("returnsPage")
        self._build_ui()
        self.reload()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 24)
        layout.setSpacing(14)

        title = QLabel("Returns", self)
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        description = QLabel(
            "Customer returns reverse historical sale allocations. "
            "Supplier returns remove stock from exact purchase lots while "
            "preserving their acquisition cost.",
            self,
        )
        description.setObjectName("pageDescription")
        description.setWordWrap(True)
        layout.addWidget(description)

        toolbar = QHBoxLayout()
        refresh = QPushButton("Refresh", self)
        refresh.setObjectName("refreshReturnsButton")
        refresh.clicked.connect(self.reload)
        toolbar.addWidget(refresh)
        toolbar.addStretch(1)

        self._new_customer_button = QPushButton(
            "New customer return", self
        )
        self._new_customer_button.setObjectName(
            "newCustomerReturnButton"
        )
        self._new_customer_button.setProperty("variant", "primary")
        self._new_customer_button.clicked.connect(
            self._create_customer_return
        )
        toolbar.addWidget(self._new_customer_button)

        self._new_supplier_button = QPushButton(
            "New supplier return", self
        )
        self._new_supplier_button.setObjectName(
            "newSupplierReturnButton"
        )
        self._new_supplier_button.clicked.connect(
            self._create_supplier_return
        )
        toolbar.addWidget(self._new_supplier_button)
        layout.addLayout(toolbar)

        self._error_banner = QLabel(self)
        self._error_banner.setObjectName("errorBanner")
        self._error_banner.setWordWrap(True)
        self._error_banner.hide()
        layout.addWidget(self._error_banner)

        self._customer_model = ReadOnlyTableModel(
            ("Date", "Sale", "Items", "Refund", "Account", "Notes"),
            self._customer_values,
            right_columns=(1, 2, 3),
            parent=self,
        )
        self._supplier_model = ReadOnlyTableModel(
            (
                "Date",
                "Purchase",
                "Supplier",
                "Items",
                "Refund",
                "Account",
                "Notes",
            ),
            self._supplier_values,
            right_columns=(1, 3, 4),
            parent=self,
        )
        self._customer_table = _table(
            self, "customerReturnsTable", self._customer_model, 5
        )
        self._supplier_table = _table(
            self, "supplierReturnsTable", self._supplier_model, 6
        )

        self._tabs = QTabWidget(self)
        self._tabs.setObjectName("returnsTabs")
        self._tabs.addTab(self._customer_table, "Customer returns")
        self._tabs.addTab(self._supplier_table, "Supplier returns")
        layout.addWidget(self._tabs, 1)

        self._footer = QLabel(self)
        self._footer.setObjectName("returnsFooter")
        layout.addWidget(self._footer)

    @staticmethod
    def _customer_values(row: CustomerReturnRow) -> tuple[str, ...]:
        return (
            display_datetime(row.return_date),
            str(row.sale_id),
            str(row.item_count),
            str(row.refund_amount) if row.refund_amount else "—",
            row.account_name or "—",
            row.notes or "—",
        )

    @staticmethod
    def _supplier_values(row: SupplierReturnRow) -> tuple[str, ...]:
        return (
            display_datetime(row.return_date),
            str(row.purchase_id),
            row.supplier_name or "—",
            str(row.item_count),
            str(row.refund_amount) if row.refund_amount else "—",
            row.account_name or "—",
            row.notes or "—",
        )

    def reload(self, *_args) -> None:
        try:
            customer_rows = self._returns.list_customer_returns()
            supplier_rows = self._returns.list_supplier_returns()
        except Exception as exc:
            self._show_error(f"Could not load returns: {exc}")
            return
        self._show_error(None)
        self._customer_rows = tuple(customer_rows)
        self._supplier_rows = tuple(supplier_rows)
        self._customer_model.set_rows(self._customer_rows)
        self._supplier_model.set_rows(self._supplier_rows)
        self._footer.setText(
            f"{len(self._customer_rows)} customer returns · "
            f"{len(self._supplier_rows)} supplier returns"
        )

    def _show_error(self, message: str | None) -> None:
        if message is None:
            self._error_banner.clear()
            self._error_banner.hide()
            return
        self._error_banner.setText(message)
        self._error_banner.show()

    def _create_customer_return(self) -> None:
        try:
            sales = self._returns.list_returnable_sales()
            accounts = self._returns.list_accounts()
        except Exception as exc:
            QMessageBox.critical(
                self, "Could not open return form", str(exc)
            )
            return
        if not sales:
            QMessageBox.information(
                self,
                "Nothing to return",
                "No sale has units available for a customer return.",
            )
            return
        dialog = CustomerReturnDialog(
            self._returns,
            sales=sales,
            accounts=accounts,
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.reload()

    def _create_supplier_return(self) -> None:
        try:
            purchases = self._returns.list_returnable_purchases()
            accounts = self._returns.list_accounts()
        except Exception as exc:
            QMessageBox.critical(
                self, "Could not open return form", str(exc)
            )
            return
        if not purchases:
            QMessageBox.information(
                self,
                "Nothing to return",
                "No purchase lot has remaining stock for a supplier "
                "return.",
            )
            return
        dialog = SupplierReturnDialog(
            self._returns,
            purchases=purchases,
            accounts=accounts,
            parent=self,
        )
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
    table.setSelectionMode(
        QAbstractItemView.SelectionMode.SingleSelection
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
