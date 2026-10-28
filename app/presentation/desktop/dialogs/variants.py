"""Variant and attribute management dialogs."""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableView,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.application.attributes.manage_attributes import (
    AttributeSummary,
    CreateAttributeRequest,
    CreateAttributeValueRequest,
)
from app.application.products.catalog import ProductCatalogService
from app.application.products.list_products import ProductListItem
from app.application.products.variants import (
    CreateVariantRequest,
    UpdateVariantRequest,
    VariantListItem,
)


class VariantTableModel(QAbstractTableModel):
    """Read-only variant rows."""

    HEADERS = ("SKU", "Variant", "Barcode", "Attributes", "Status")

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._rows: tuple[VariantListItem, ...] = ()

    def set_variants(self, variants: Sequence[VariantListItem]) -> None:
        self.beginResetModel()
        self._rows = tuple(variants)
        self.endResetModel()

    def variants(self) -> tuple[VariantListItem, ...]:
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
                row.sku or "—",
                row.variant_name or "—",
                row.barcode or "—",
                ", ".join(row.attribute_labels) or "—",
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


class VariantDialog(QDialog):
    """Create or edit one variant and its attribute values."""

    def __init__(
        self,
        catalog: ProductCatalogService,
        product_id: int,
        attributes: Sequence[AttributeSummary],
        *,
        existing: VariantListItem | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._catalog = catalog
        self._product_id = product_id
        self._attributes = tuple(attributes)
        self._existing = existing
        self._attribute_combos: dict[int, QComboBox] = {}

        self.setWindowTitle(
            "Edit variant" if existing is not None else "New variant"
        )
        self.setModal(True)
        self.resize(520, 560)
        self._build_ui()
        if existing is not None:
            self._apply_existing(existing)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel(
            "Edit variant" if self._existing is not None else "New variant",
            self,
        )
        title.setObjectName("dialogTitle")
        layout.addWidget(title)

        form = QFormLayout()
        self._sku = QLineEdit(self)
        self._sku.setObjectName("variantSku")
        self._sku.setPlaceholderText("Optional unique SKU")
        form.addRow("SKU", self._sku)

        self._variant_name = QLineEdit(self)
        self._variant_name.setObjectName("variantName")
        self._variant_name.setPlaceholderText("For example: Red, Large")
        form.addRow("Variant name", self._variant_name)

        self._barcode = QLineEdit(self)
        self._barcode.setObjectName("variantBarcode")
        self._barcode.setPlaceholderText("Optional barcode")
        form.addRow("Barcode", self._barcode)
        layout.addLayout(form)

        group = QGroupBox("Attributes", self)
        group_layout = QFormLayout(group)
        if not self._attributes:
            hint = QLabel(
                "No attributes defined. Use Manage attributes to add some.",
                group,
            )
            hint.setObjectName("fieldHint")
            hint.setWordWrap(True)
            group_layout.addRow(hint)
        else:
            for attribute in self._attributes:
                combo = QComboBox(group)
                combo.setObjectName("variantAttribute")
                combo.setProperty("attributeId", attribute.attribute_id)
                combo.addItem("—", None)
                for value in attribute.values:
                    combo.addItem(value.value, value.id)
                group_layout.addRow(attribute.name, combo)
                self._attribute_combos[attribute.attribute_id] = combo
        layout.addWidget(group)

        layout.addStretch(1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel, self)
        self._save_button = QPushButton(
            "Save variant" if self._existing is not None else "Create variant",
            self,
        )
        self._save_button.setObjectName("saveVariantButton")
        self._save_button.setProperty("variant", "primary")
        self._save_button.setDefault(True)
        buttons.addButton(
            self._save_button, QDialogButtonBox.ButtonRole.AcceptRole
        )
        buttons.rejected.connect(self.reject)
        self._save_button.clicked.connect(self._submit)
        layout.addWidget(buttons)

    def _apply_existing(self, existing: VariantListItem) -> None:
        self._sku.setText(existing.sku or "")
        self._variant_name.setText(existing.variant_name or "")
        self._barcode.setText(existing.barcode or "")

        for value_id in existing.attribute_value_ids:
            for combo in self._attribute_combos.values():
                index = combo.findData(value_id)
                if index >= 0:
                    combo.setCurrentIndex(index)
                    break

    def _submit(self) -> None:
        sku = self._sku.text().strip() or None
        variant_name = self._variant_name.text().strip() or None
        barcode = self._barcode.text().strip() or None
        attribute_value_ids = tuple(
            combo.currentData()
            for combo in self._attribute_combos.values()
            if combo.currentData() is not None
        )

        try:
            if self._existing is None:
                self._catalog.create_variant(
                    CreateVariantRequest(
                        product_id=self._product_id,
                        sku=sku,
                        variant_name=variant_name,
                        barcode=barcode,
                        attribute_value_ids=attribute_value_ids,
                    )
                )
            else:
                self._catalog.update_variant(
                    UpdateVariantRequest(
                        variant_id=self._existing.variant_id,
                        sku=sku,
                        variant_name=variant_name,
                        barcode=barcode,
                        attribute_value_ids=attribute_value_ids,
                    )
                )
        except Exception as exc:
            QMessageBox.critical(
                self,
                (
                    "Could not update variant"
                    if self._existing is not None
                    else "Could not create variant"
                ),
                str(exc),
            )
            return

        self.accept()


class VariantsDialog(QDialog):
    """Manage all variants of one product."""

    def __init__(
        self,
        catalog: ProductCatalogService,
        product: ProductListItem,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._catalog = catalog
        self._product = product
        self._attributes: tuple[AttributeSummary, ...] = ()

        self.setWindowTitle(f"Variants — {product.name}")
        self.setModal(True)
        self.resize(760, 520)
        self._build_ui()
        self.reload()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel(self._product.name, self)
        title.setObjectName("dialogTitle")
        layout.addWidget(title)

        subtitle = QLabel(
            "Each variant is a sellable identity. Attribute values describe it.",
            self,
        )
        subtitle.setObjectName("pageDescription")
        layout.addWidget(subtitle)

        self._error_banner = QLabel(self)
        self._error_banner.setObjectName("errorBanner")
        self._error_banner.setWordWrap(True)
        self._error_banner.hide()
        layout.addWidget(self._error_banner)

        self._model = VariantTableModel(self)
        self._table = QTableView(self)
        self._table.setObjectName("variantsTable")
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
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.Stretch
        )
        self._table.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.selectionModel().selectionChanged.connect(
            self._update_actions
        )
        self._table.doubleClicked.connect(self._edit_variant)
        layout.addWidget(self._table, 1)

        self._footer = QLabel(self)
        self._footer.setObjectName("productsFooter")
        layout.addWidget(self._footer)

        actions = QHBoxLayout()
        self._add_button = QPushButton("New variant", self)
        self._add_button.setObjectName("addVariantButton")
        self._add_button.setProperty("variant", "primary")
        self._add_button.clicked.connect(self._add_variant)
        actions.addWidget(self._add_button)

        self._edit_button = QPushButton("Edit", self)
        self._edit_button.setObjectName("editVariantButton")
        self._edit_button.clicked.connect(self._edit_variant)
        actions.addWidget(self._edit_button)

        self._toggle_button = QPushButton("Deactivate", self)
        self._toggle_button.setObjectName("toggleVariantButton")
        self._toggle_button.clicked.connect(self._toggle_variant)
        actions.addWidget(self._toggle_button)

        self._attributes_button = QPushButton("Manage attributes", self)
        self._attributes_button.setObjectName("manageAttributesButton")
        self._attributes_button.clicked.connect(self._manage_attributes)
        actions.addWidget(self._attributes_button)

        actions.addStretch(1)

        close_button = QPushButton("Close", self)
        close_button.setObjectName("closeVariantsButton")
        close_button.clicked.connect(self.accept)
        actions.addWidget(close_button)
        layout.addLayout(actions)

        self._update_actions()

    def reload(self) -> None:
        try:
            variants = self._catalog.list_variants(
                self._product.product_id, include_inactive=True
            )
            self._attributes = tuple(self._catalog.list_attributes())
        except Exception as exc:
            self._show_error(f"Could not load variants: {exc}")
            return

        self._show_error(None)
        self._model.set_variants(variants)
        suffix = "variant" if len(variants) == 1 else "variants"
        self._footer.setText(f"{len(variants)} {suffix}")
        self._update_actions()

    def _show_error(self, message: str | None) -> None:
        if message is None:
            self._error_banner.clear()
            self._error_banner.hide()
            return
        self._error_banner.setText(message)
        self._error_banner.show()

    def _selected_variant(self) -> VariantListItem | None:
        indexes = self._table.selectionModel().selectedRows()
        if not indexes:
            return None
        row = indexes[0].row()
        rows = self._model.variants()
        if 0 <= row < len(rows):
            return rows[row]
        return None

    def _update_actions(self, *_args) -> None:
        selected = self._selected_variant()
        self._edit_button.setEnabled(selected is not None)
        self._toggle_button.setEnabled(selected is not None)
        if selected is None:
            self._toggle_button.setText("Deactivate")
        else:
            self._toggle_button.setText(
                "Deactivate" if selected.is_active else "Activate"
            )

    def _add_variant(self) -> None:
        dialog = VariantDialog(
            self._catalog,
            self._product.product_id,
            self._attributes,
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.reload()

    def _edit_variant(self, *_args) -> None:
        selected = self._selected_variant()
        if selected is None:
            return
        dialog = VariantDialog(
            self._catalog,
            self._product.product_id,
            self._attributes,
            existing=selected,
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.reload()

    def _toggle_variant(self) -> None:
        selected = self._selected_variant()
        if selected is None:
            return

        target = not selected.is_active
        action = "Activate" if target else "Deactivate"
        answer = QMessageBox.question(
            self,
            f"{action} variant",
            f"{action} variant {selected.sku or selected.variant_name or ''}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            self._catalog.set_variant_active(
                selected.variant_id, is_active=target
            )
        except Exception as exc:
            QMessageBox.critical(
                self, f"Could not {action.lower()} variant", str(exc)
            )
            return
        self.reload()

    def _manage_attributes(self) -> None:
        dialog = AttributesDialog(self._catalog, parent=self)
        dialog.exec()
        self.reload()


class AttributesDialog(QDialog):
    """Create attributes and values used by product variants."""

    def __init__(
        self,
        catalog: ProductCatalogService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._catalog = catalog
        self.setWindowTitle("Attributes")
        self.setModal(True)
        self.resize(560, 560)
        self._build_ui()
        self.reload()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel("Attributes", self)
        title.setObjectName("dialogTitle")
        layout.addWidget(title)

        subtitle = QLabel(
            "Attributes such as color or size group the values used by variants.",
            self,
        )
        subtitle.setObjectName("pageDescription")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        self._error_banner = QLabel(self)
        self._error_banner.setObjectName("errorBanner")
        self._error_banner.setWordWrap(True)
        self._error_banner.hide()
        layout.addWidget(self._error_banner)

        self._tree = QTreeWidget(self)
        self._tree.setObjectName("attributesTree")
        self._tree.setHeaderLabels(["Attribute / value"])
        self._tree.setRootIsDecorated(True)
        self._tree.itemSelectionChanged.connect(self._update_actions)
        layout.addWidget(self._tree, 1)

        attribute_row = QHBoxLayout()
        self._new_attribute = QLineEdit(self)
        self._new_attribute.setObjectName("newAttributeName")
        self._new_attribute.setPlaceholderText("New attribute, e.g. Color")
        attribute_row.addWidget(self._new_attribute, 1)
        self._add_attribute_button = QPushButton("Add attribute", self)
        self._add_attribute_button.setObjectName("addAttributeButton")
        self._add_attribute_button.clicked.connect(self._add_attribute)
        attribute_row.addWidget(self._add_attribute_button)
        layout.addLayout(attribute_row)

        value_row = QHBoxLayout()
        self._new_value = QLineEdit(self)
        self._new_value.setObjectName("newAttributeValue")
        self._new_value.setPlaceholderText("New value for the selected attribute")
        value_row.addWidget(self._new_value, 1)
        self._add_value_button = QPushButton("Add value", self)
        self._add_value_button.setObjectName("addAttributeValueButton")
        self._add_value_button.clicked.connect(self._add_value)
        value_row.addWidget(self._add_value_button)
        layout.addLayout(value_row)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._update_actions()

    def reload(self, *, select_attribute_id: int | None = None) -> None:
        try:
            attributes = self._catalog.list_attributes()
        except Exception as exc:
            self._show_error(f"Could not load attributes: {exc}")
            return

        self._show_error(None)
        self._tree.clear()
        selected_item: QTreeWidgetItem | None = None
        for attribute in attributes:
            item = QTreeWidgetItem([attribute.name])
            item.setData(0, Qt.ItemDataRole.UserRole, attribute.attribute_id)
            self._tree.addTopLevelItem(item)
            for value in attribute.values:
                child = QTreeWidgetItem([value.value])
                child.setData(
                    0, Qt.ItemDataRole.UserRole, value.id
                )
                child.setData(
                    0, Qt.ItemDataRole.UserRole + 1, attribute.attribute_id
                )
                item.addChild(child)
            item.setExpanded(True)
            if attribute.attribute_id == select_attribute_id:
                selected_item = item

        if selected_item is not None:
            self._tree.setCurrentItem(selected_item)
        self._update_actions()

    def _show_error(self, message: str | None) -> None:
        if message is None:
            self._error_banner.clear()
            self._error_banner.hide()
            return
        self._error_banner.setText(message)
        self._error_banner.show()

    def _selected_attribute_id(self) -> int | None:
        item = self._tree.currentItem()
        if item is None:
            return None
        attribute_id = item.data(0, Qt.ItemDataRole.UserRole + 1)
        if attribute_id is None:
            attribute_id = item.data(0, Qt.ItemDataRole.UserRole)
        return attribute_id if isinstance(attribute_id, int) else None

    def _update_actions(self, *_args) -> None:
        self._add_value_button.setEnabled(
            self._selected_attribute_id() is not None
        )

    def _add_attribute(self) -> None:
        name = self._new_attribute.text().strip()
        if not name:
            QMessageBox.warning(
                self, "Invalid attribute", "Attribute name is required."
            )
            return

        try:
            created = self._catalog.create_attribute(
                CreateAttributeRequest(name=name)
            )
        except Exception as exc:
            QMessageBox.critical(
                self, "Could not create attribute", str(exc)
            )
            return

        self._new_attribute.clear()
        self.reload(select_attribute_id=created.id)

    def _add_value(self) -> None:
        attribute_id = self._selected_attribute_id()
        if attribute_id is None:
            QMessageBox.warning(
                self,
                "No attribute selected",
                "Select an attribute before adding a value.",
            )
            return

        value = self._new_value.text().strip()
        if not value:
            QMessageBox.warning(
                self, "Invalid value", "Attribute value is required."
            )
            return

        try:
            self._catalog.create_attribute_value(
                CreateAttributeValueRequest(
                    attribute_id=attribute_id,
                    value=value,
                )
            )
        except Exception as exc:
            QMessageBox.critical(
                self, "Could not create attribute value", str(exc)
            )
            return

        self._new_value.clear()
        self.reload(select_attribute_id=attribute_id)
