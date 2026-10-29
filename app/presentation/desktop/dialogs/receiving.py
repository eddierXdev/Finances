"""Receipt dialog for the Receiving screen."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.application.inventory import (
    ReceivePurchaseRequest,
    ReceiptItemRequest,
)
from app.application.receiving.service import (
    ReceivingPurchase,
    ReceivingService,
)
from app.presentation.desktop.form_utils import date_to_datetime


class ReceiptDialog(QDialog):
    """Collect quantities for one purchase receipt."""

    def __init__(
        self,
        receiving: ReceivingService,
        purchase: ReceivingPurchase,
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        if not purchase.lines:
            raise ValueError("This purchase has no pending stock.")
        self._receiving = receiving
        self._purchase = purchase
        self._quantities: list[QSpinBox] = []
        self.received_result = None

        self.setWindowTitle("Receive purchase")
        self.setModal(True)
        self.resize(720, 540)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel(f"Receive purchase #{self._purchase.purchase_id}", self)
        title.setObjectName("dialogTitle")
        layout.addWidget(title)

        summary = QLabel(
            f"{self._purchase.supplier_name or 'No supplier'} · "
            f"{self._purchase.currency_code} · "
            f"{self._purchase.remaining_units} units pending",
            self,
        )
        summary.setObjectName("dialogSummary")
        layout.addWidget(summary)

        form = QFormLayout()
        self._date = QDateEdit(QDate.currentDate(), self)
        self._date.setObjectName("receiptDate")
        self._date.setCalendarPopup(True)
        self._date.setDisplayFormat("yyyy-MM-dd")
        form.addRow("Received on *", self._date)

        self._notes = QPlainTextEdit(self)
        self._notes.setObjectName("receiptNotes")
        self._notes.setPlaceholderText("Optional receipt notes")
        self._notes.setFixedHeight(58)
        form.addRow("Notes", self._notes)
        layout.addLayout(form)

        table = QTableWidget(len(self._purchase.lines), 5, self)
        table.setObjectName("receiptItemsTable")
        table.setHorizontalHeaderLabels(
            ("Variant", "Ordered", "Received", "Remaining", "Receive now")
        )
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        for column in (1, 2, 3, 4):
            table.horizontalHeader().setSectionResizeMode(
                column, QHeaderView.ResizeMode.ResizeToContents
            )

        for row, line in enumerate(self._purchase.lines):
            values = (
                line.variant_label,
                str(line.ordered_quantity),
                str(line.received_quantity),
                str(line.remaining_quantity),
            )
            for column, value in enumerate(values):
                table.setItem(
                    row, column, QTableWidgetItem(value)
                )
            quantity = QSpinBox(table)
            quantity.setObjectName("receiptQuantity")
            quantity.setRange(0, line.remaining_quantity)
            quantity.setValue(line.remaining_quantity)
            table.setCellWidget(row, 4, quantity)
            self._quantities.append(quantity)

        layout.addWidget(table, 1)

        hint = QLabel(
            "Set a quantity to zero to leave that line pending for a later "
            "receipt. The purchase status is calculated by the receiving "
            "use case.",
            self,
        )
        hint.setObjectName("fieldHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        layout.addStretch(0)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel, self
        )
        receive = QPushButton("Receive stock", self)
        receive.setObjectName("receiveStockButton")
        receive.setProperty("variant", "primary")
        receive.setDefault(True)
        buttons.addButton(receive, QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.rejected.connect(self.reject)
        receive.clicked.connect(self._submit)
        layout.addWidget(buttons)

    def _submit(self) -> None:
        items = tuple(
            ReceiptItemRequest(
                purchase_item_id=line.purchase_item_id,
                quantity=quantity.value(),
            )
            for line, quantity in zip(
                self._purchase.lines, self._quantities, strict=True
            )
            if quantity.value() > 0
        )
        if not items:
            QMessageBox.warning(
                self,
                "Nothing to receive",
                "Enter at least one received quantity.",
            )
            return

        try:
            self.received_result = self._receiving.receive_purchase(
                ReceivePurchaseRequest(
                    purchase_id=self._purchase.purchase_id,
                    items=items,
                    received_at=date_to_datetime(self._date.date()),
                    notes=self._notes.toPlainText().strip() or None,
                )
            )
        except Exception as exc:
            QMessageBox.critical(
                self, "Could not receive purchase", str(exc)
            )
            return
        self.accept()
