"""Inventory screen with stock, lots and movement history."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTabWidget,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from app.application.inventory.service import (
    InventoryLotRow,
    InventoryMovementRow,
    InventoryService,
    InventoryStockRow,
)
from app.presentation.desktop.form_utils import display_datetime
from app.presentation.desktop.labels import inventory_movement_label
from app.presentation.desktop.table_model import ReadOnlyTableModel


class InventoryPage(QWidget):
    """Read-only view of current stock, acquisition lots and movements."""

    def __init__(
        self,
        inventory: InventoryService,
        *,
        base_currency: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._inventory = inventory
        self._base_currency = base_currency
        self.setObjectName("inventoryPage")
        self._build_ui()
        self.reload()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 24)
        layout.setSpacing(14)

        title = QLabel("Inventory", self)
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        description = QLabel(
            "Sellable stock by variant, the lots that created it and every "
            "signed movement.",
            self,
        )
        description.setObjectName("pageDescription")
        description.setWordWrap(True)
        layout.addWidget(description)

        toolbar = QHBoxLayout()
        refresh = QPushButton("Refresh", self)
        refresh.setObjectName("refreshInventoryButton")
        refresh.clicked.connect(self.reload)
        toolbar.addWidget(refresh)
        toolbar.addStretch(1)
        layout.addLayout(toolbar)

        self._error_banner = QLabel(self)
        self._error_banner.setObjectName("errorBanner")
        self._error_banner.setWordWrap(True)
        self._error_banner.hide()
        layout.addWidget(self._error_banner)

        self._stock_model = ReadOnlyTableModel(
            (
                "Product",
                "Variant",
                "SKU",
                "On hand",
                "Lots",
                "Acquisition value",
            ),
            self._stock_values,
            right_columns=(3, 4),
            muted=lambda row: not row.is_active,
            parent=self,
        )
        self._lots_model = ReadOnlyTableModel(
            (
                "Received",
                "Product",
                "Variant",
                "SKU",
                "Supplier",
                "Acquired",
                "Remaining",
                "Unit cost",
                "Lot",
            ),
            self._lot_values,
            right_columns=(5, 6, 7),
            parent=self,
        )
        self._movements_model = ReadOnlyTableModel(
            (
                "Date",
                "Type",
                "Product",
                "Variant",
                "Quantity",
                "Lot",
                "Reference",
                "Unit cost",
            ),
            self._movement_values,
            right_columns=(4, 5, 7),
            parent=self,
        )

        self._stock_table = _table(
            self, "inventoryStockTable", self._stock_model, 0
        )
        self._lots_table = _table(
            self, "inventoryLotsTable", self._lots_model, 1
        )
        self._movements_table = _table(
            self, "inventoryMovementsTable", self._movements_model, 2
        )

        tabs = QTabWidget(self)
        tabs.setObjectName("inventoryTabs")
        tabs.addTab(self._stock_table, "Stock")
        tabs.addTab(self._lots_table, "Lots")
        tabs.addTab(self._movements_table, "Movements")
        layout.addWidget(tabs, 1)

        self._footer = QLabel(self)
        self._footer.setObjectName("inventoryFooter")
        layout.addWidget(self._footer)

    @staticmethod
    def _stock_values(row: InventoryStockRow) -> tuple[str, ...]:
        return (
            row.product_name,
            row.variant_name or "Default",
            row.sku or "—",
            str(row.on_hand),
            str(row.lot_count),
            row.value_label,
        )

    @staticmethod
    def _lot_values(row: InventoryLotRow) -> tuple[str, ...]:
        return (
            display_datetime(row.received_at),
            row.product_name,
            row.variant_name or "Default",
            row.sku or "—",
            row.supplier_name or "—",
            str(row.acquired_quantity),
            str(row.remaining_quantity),
            str(row.unit_cost),
            str(row.lot_id),
        )

    @staticmethod
    def _movement_values(row: InventoryMovementRow) -> tuple[str, ...]:
        quantity = f"{row.quantity:+d}"
        reference = "—"
        if row.reference_type:
            reference = row.reference_type
            if row.reference_id is not None:
                reference = f"{reference} #{row.reference_id}"
        return (
            display_datetime(row.movement_date),
            inventory_movement_label(row.movement_type),
            row.product_name,
            row.variant_name or "Default",
            quantity,
            str(row.lot_id) if row.lot_id is not None else "—",
            reference,
            str(row.unit_cost) if row.unit_cost is not None else "—",
        )

    def reload(self, *_args) -> None:
        try:
            stock = self._inventory.list_stock()
            lots = self._inventory.list_lots()
            movements = self._inventory.list_movements()
        except Exception as exc:
            self._show_error(f"Could not load inventory: {exc}")
            return
        self._show_error(None)
        self._stock_model.set_rows(stock)
        self._lots_model.set_rows(lots)
        self._movements_model.set_rows(movements)
        total_units = sum(row.on_hand for row in stock)
        self._footer.setText(
            f"{len(stock)} variants · {total_units} units · "
            f"{len(lots)} lots · {len(movements)} movements"
        )

    def _show_error(self, message: str | None) -> None:
        if message is None:
            self._error_banner.clear()
            self._error_banner.hide()
            return
        self._error_banner.setText(message)
        self._error_banner.show()


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
