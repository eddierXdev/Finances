"""Receiving screen."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTableView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.application.receiving.service import (
    ReceivingPurchase,
    ReceivingService,
)
from app.presentation.desktop.dialogs.receiving import ReceiptDialog
from app.presentation.desktop.labels import purchase_status_label
from app.presentation.desktop.table_model import ReadOnlyTableModel


class ReceivingPage(QWidget):
    """List purchases in transit and receive partial or complete stock."""

    def __init__(
        self,
        receiving: ReceivingService,
        *,
        base_currency: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._receiving = receiving
        self._base_currency = base_currency
        self._rows: tuple[ReceivingPurchase, ...] = ()

        self.setObjectName("receivingPage")
        self._build_ui()
        self.reload()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 24)
        layout.setSpacing(14)

        title = QLabel("Receiving", self)
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        description = QLabel(
            "Receive paid purchases into traceable inventory lots, partially "
            "or completely.",
            self,
        )
        description.setObjectName("pageDescription")
        description.setWordWrap(True)
        layout.addWidget(description)

        toolbar = QHBoxLayout()
        refresh = QPushButton("Refresh", self)
        refresh.setObjectName("refreshReceivingButton")
        refresh.clicked.connect(self.reload)
        toolbar.addWidget(refresh)
        toolbar.addStretch(1)

        self._receive_button = QPushButton("Receive stock", self)
        self._receive_button.setObjectName("receivePurchaseButton")
        self._receive_button.setProperty("variant", "primary")
        self._receive_button.clicked.connect(self._receive)
        toolbar.addWidget(self._receive_button)
        layout.addLayout(toolbar)

        self._error_banner = QLabel(self)
        self._error_banner.setObjectName("errorBanner")
        self._error_banner.setWordWrap(True)
        self._error_banner.hide()
        layout.addWidget(self._error_banner)

        self._model = ReadOnlyTableModel(
            ("Date", "Supplier", "Currency", "Status", "Items", "Pending"),
            self._values,
            right_columns=(4, 5),
            center_columns=(2, 3),
            parent=self,
        )
        self._table = QTableView(self)
        self._table.setObjectName("receivingTable")
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
            self._update_detail
        )
        self._table.doubleClicked.connect(self._receive)
        self._table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        for column in (0, 2, 3, 4, 5):
            self._table.horizontalHeader().setSectionResizeMode(
                column, QHeaderView.ResizeMode.ResizeToContents
            )

        self._empty_title = QLabel("Nothing waiting to be received", self)
        self._empty_title.setObjectName("emptyStateTitle")
        self._empty_hint = QLabel(
            "Paid purchases must reach In Transit before stock can be "
            "received.",
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
        self._content.setObjectName("receivingContent")
        self._content.addWidget(self._table)
        self._content.addWidget(self._empty)
        layout.addWidget(self._content, 1)

        detail_group = QWidget(self)
        detail_layout = QVBoxLayout(detail_group)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        detail_layout.setSpacing(6)
        detail_title = QLabel("Pending lines", detail_group)
        detail_title.setObjectName("sectionTitle")
        detail_layout.addWidget(detail_title)
        self._detail = QTableWidget(0, 5, detail_group)
        self._detail.setObjectName("receivingLinesTable")
        self._detail.setHorizontalHeaderLabels(
            ("Variant", "Ordered", "Received", "Remaining", "Unit cost")
        )
        self._detail.verticalHeader().setVisible(False)
        self._detail.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._detail.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        for column in (1, 2, 3, 4):
            self._detail.horizontalHeader().setSectionResizeMode(
                column, QHeaderView.ResizeMode.ResizeToContents
            )
        detail_layout.addWidget(self._detail)
        layout.addWidget(detail_group, 1)

        self._footer = QLabel(self)
        self._footer.setObjectName("receivingFooter")
        layout.addWidget(self._footer)
        self._update_detail()

    @staticmethod
    def _values(row: ReceivingPurchase) -> tuple[str, ...]:
        return (
            row.purchase_date.date().isoformat(),
            row.supplier_name or "—",
            row.currency_code,
            purchase_status_label(row.status),
            str(row.item_count),
            str(row.remaining_units),
        )

    def reload(self, *_args) -> None:
        try:
            rows = self._receiving.list_receivable_purchases()
        except Exception as exc:
            self._show_error(f"Could not load receipts: {exc}")
            return
        self._show_error(None)
        self._rows = tuple(rows)
        self._model.set_rows(self._rows)
        self._content.setCurrentWidget(
            self._table if self._rows else self._empty
        )
        self._footer.setText(
            f"{len(self._rows)} purchases waiting for stock"
            if self._rows
            else "No purchases waiting for stock"
        )
        self._update_detail()

    def _show_error(self, message: str | None) -> None:
        if message is None:
            self._error_banner.clear()
            self._error_banner.hide()
            return
        self._error_banner.setText(message)
        self._error_banner.show()

    def _selected(self) -> ReceivingPurchase | None:
        indexes = self._table.selectionModel().selectedRows()
        if not indexes:
            return None
        value = self._model.row_at(indexes[0].row())
        return value if isinstance(value, ReceivingPurchase) else None

    def _update_detail(self, *_args) -> None:
        selected = self._selected()
        self._receive_button.setEnabled(selected is not None)
        self._detail.setRowCount(0 if selected is None else len(selected.lines))
        if selected is None:
            return
        for row, line in enumerate(selected.lines):
            values = (
                line.variant_label,
                str(line.ordered_quantity),
                str(line.received_quantity),
                str(line.remaining_quantity),
                str(line.unit_cost),
            )
            for column, value in enumerate(values):
                self._detail.setItem(
                    row, column, QTableWidgetItem(value)
                )

    def _receive(self, *_args) -> None:
        selected = self._selected()
        if selected is None:
            return
        dialog = ReceiptDialog(self._receiving, selected, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.reload()
