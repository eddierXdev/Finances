"""Sales screen."""

from __future__ import annotations

from PySide6.QtCore import Qt
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

from app.application.sales.service import SaleRow, SalesService
from app.domain.enums.sale_status import SaleStatus
from app.presentation.desktop.dialogs.sales import (
    SaleDetailDialog,
    SaleDialog,
)
from app.presentation.desktop.labels import sale_status_label
from app.presentation.desktop.table_model import ReadOnlyTableModel


class SalesPage(QWidget):
    """List sales and register new FIFO sales."""

    def __init__(
        self,
        sales: SalesService,
        *,
        base_currency: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._sales = sales
        self._base_currency = base_currency
        self._rows: tuple[SaleRow, ...] = ()

        self.setObjectName("salesPage")
        self._build_ui()
        self.reload()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 24)
        layout.setSpacing(14)

        title = QLabel("Sales", self)
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        description = QLabel(
            "Fully collected sales with immutable FIFO allocations, COGS and "
            "gross profit.",
            self,
        )
        description.setObjectName("pageDescription")
        description.setWordWrap(True)
        layout.addWidget(description)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        self._search = QLineEdit(self)
        self._search.setObjectName("saleSearch")
        self._search.setPlaceholderText(
            "Search by account, currency or status"
        )
        self._search.setClearButtonEnabled(True)
        self._search.setMaximumWidth(300)
        self._search.textChanged.connect(self._apply_filter)
        toolbar.addWidget(self._search)

        self._status_filter = QComboBox(self)
        self._status_filter.setObjectName("saleStatusFilter")
        self._status_filter.addItem("All statuses", None)
        for status in SaleStatus:
            self._status_filter.addItem(sale_status_label(status), status)
        self._status_filter.currentIndexChanged.connect(self._apply_filter)
        toolbar.addWidget(self._status_filter)

        refresh = QPushButton("Refresh", self)
        refresh.setObjectName("refreshSalesButton")
        refresh.clicked.connect(self.reload)
        toolbar.addWidget(refresh)
        toolbar.addStretch(1)

        self._new_button = QPushButton("New sale", self)
        self._new_button.setObjectName("newSaleButton")
        self._new_button.setProperty("variant", "primary")
        self._new_button.clicked.connect(self._create_sale)
        toolbar.addWidget(self._new_button)
        layout.addLayout(toolbar)

        actions = QHBoxLayout()
        actions.addStretch(1)
        self._detail_button = QPushButton("Details", self)
        self._detail_button.setObjectName("saleDetailButton")
        self._detail_button.clicked.connect(self._show_detail)
        actions.addWidget(self._detail_button)
        layout.addLayout(actions)

        self._error_banner = QLabel(self)
        self._error_banner.setObjectName("errorBanner")
        self._error_banner.setWordWrap(True)
        self._error_banner.hide()
        layout.addWidget(self._error_banner)

        self._model = ReadOnlyTableModel(
            (
                "Date",
                "Account",
                "Currency",
                "Items",
                "Total",
                "Status",
                "COGS",
            ),
            self._values,
            right_columns=(3, 4, 6),
            center_columns=(2, 5),
            muted=lambda row: row.status is SaleStatus.CANCELLED,
            parent=self,
        )
        self._table = QTableView(self)
        self._table.setObjectName("salesTable")
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
        self._table.selectionModel().selectionChanged.connect(
            self._update_actions
        )
        self._table.doubleClicked.connect(self._show_detail)
        self._table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        for column in (0, 2, 3, 4, 5, 6):
            self._table.horizontalHeader().setSectionResizeMode(
                column, QHeaderView.ResizeMode.ResizeToContents
            )

        self._empty_title = QLabel("No sales yet", self)
        self._empty_title.setObjectName("emptyStateTitle")
        self._empty_hint = QLabel(
            "Receive stock first, then register a sale collected into an "
            "account.",
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
        self._content.setObjectName("salesContent")
        self._content.addWidget(self._table)
        self._content.addWidget(self._empty)
        layout.addWidget(self._content, 1)

        self._footer = QLabel(self)
        self._footer.setObjectName("salesFooter")
        layout.addWidget(self._footer)
        self._update_actions()

    @staticmethod
    def _values(row: SaleRow) -> tuple[str, ...]:
        return (
            row.sale_date.date().isoformat(),
            row.account_name,
            row.currency_code,
            str(row.item_count),
            str(row.total),
            sale_status_label(row.status),
            " + ".join(str(value) for value in row.cogs) or "—",
        )

    def reload(self, *_args) -> None:
        try:
            rows = self._sales.list_sales()
        except Exception as exc:
            self._show_error(f"Could not load sales: {exc}")
            return
        self._show_error(None)
        self._rows = tuple(rows)
        self._apply_filter()

    def _apply_filter(self, *_args) -> None:
        query = self._search.text().strip().casefold()
        status = self._status_filter.currentData()
        rows = self._rows
        if status is not None:
            target = SaleStatus(status)
            rows = tuple(row for row in rows if row.status is target)
        if query:
            rows = tuple(
                row
                for row in rows
                if query
                in " ".join(
                    (
                        row.account_name,
                        row.currency_code,
                        sale_status_label(row.status),
                        str(row.sale_id),
                    )
                ).casefold()
            )
        self._model.set_rows(rows)
        self._content.setCurrentWidget(
            self._table if rows else self._empty
        )
        self._update_actions()
        if not self._rows:
            self._empty_title.setText("No sales yet")
            self._empty_hint.setText(
                "Receive stock first, then register a sale collected into an "
                "account."
            )
            self._footer.setText("No sales")
        elif not rows:
            self._empty_title.setText("No matching sales")
            self._empty_hint.setText(
                "Change the search text or select another status."
            )
            self._footer.setText(f"0 of {len(self._rows)} sales")
        elif len(rows) == len(self._rows):
            self._footer.setText(
                f"{len(rows)} sale" if len(rows) == 1 else f"{len(rows)} sales"
            )
        else:
            self._footer.setText(
                f"{len(rows)} of {len(self._rows)} sales"
            )

    def _show_error(self, message: str | None) -> None:
        if message is None:
            self._error_banner.clear()
            self._error_banner.hide()
            return
        self._error_banner.setText(message)
        self._error_banner.show()

    def _selected(self) -> SaleRow | None:
        indexes = self._table.selectionModel().selectedRows()
        if not indexes:
            return None
        value = self._model.row_at(indexes[0].row())
        return value if isinstance(value, SaleRow) else None

    def _update_actions(self, *_args) -> None:
        self._detail_button.setEnabled(self._selected() is not None)

    def _create_sale(self) -> None:
        try:
            currencies = tuple(self._sales.list_enabled_currencies())
            accounts = tuple(self._sales.list_accounts())
            variants = tuple(self._sales.list_variant_options())
        except Exception as exc:
            QMessageBox.critical(
                self, "Could not open sale form", str(exc)
            )
            return
        if not currencies or not accounts:
            QMessageBox.warning(
                self,
                "Cannot register a sale",
                "Create an active account and enable a currency first.",
            )
            return
        if not variants:
            QMessageBox.warning(
                self,
                "No variants available",
                "Create a product with an active variant first.",
            )
            return
        dialog = SaleDialog(
            self._sales,
            currencies=currencies,
            accounts=accounts,
            variants=variants,
            base_currency=self._base_currency,
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.reload()

    def _show_detail(self, *_args) -> None:
        selected = self._selected()
        if selected is None:
            return
        try:
            detail = self._sales.get_sale_detail(selected.sale_id)
        except Exception as exc:
            QMessageBox.critical(
                self, "Could not load sale", str(exc)
            )
            return
        SaleDetailDialog(detail, parent=self).exec()
