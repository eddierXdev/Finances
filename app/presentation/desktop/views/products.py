"""Products screen."""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
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

from app.application.products.catalog import ProductCatalogService
from app.application.products.list_products import ProductListItem
from app.domain.entities.category import Category
from app.domain.entities.currency import Currency
from app.presentation.desktop.dialogs.catalog import (
    CategoryDialog,
    ProductDialog,
)
from app.presentation.desktop.dialogs.variants import VariantsDialog


class ProductTableModel(QAbstractTableModel):
    """Read-only product rows.

    The model formats values for display only. Prices arrive already calculated
    by the application layer as ``Money``.
    """

    HEADERS = (
        "Name",
        "Brand",
        "Category",
        "Variants",
        "Default price",
        "Status",
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._rows: tuple[ProductListItem, ...] = ()

    def set_products(self, products: Sequence[ProductListItem]) -> None:
        self.beginResetModel()
        self._rows = tuple(products)
        self.endResetModel()

    def products(self) -> tuple[ProductListItem, ...]:
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
                row.name,
                row.brand or "—",
                row.category_name or "—",
                str(row.variant_count),
                (
                    str(row.default_selling_price)
                    if row.default_selling_price is not None
                    else "—"
                ),
                "Active" if row.is_active else "Inactive",
            )
            return values[index.column()]

        if role == Qt.ItemDataRole.TextAlignmentRole:
            if index.column() == 3:
                return int(
                    Qt.AlignmentFlag.AlignRight
                    | Qt.AlignmentFlag.AlignVCenter
                )
            if index.column() == 5:
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


class ProductsPage(QWidget):
    """Product catalog screen.

    The page asks ``ProductCatalogService`` for data and sends it user actions.
    It never opens a database session or calculates business values.
    """

    def __init__(
        self,
        catalog: ProductCatalogService,
        *,
        base_currency: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._catalog = catalog
        self._base_currency = base_currency
        self._products: tuple[ProductListItem, ...] = ()

        self.setObjectName("productsPage")
        self._build_ui()
        self.reload()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 24)
        layout.setSpacing(14)

        title = QLabel("Products", self)
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        description = QLabel(
            "Categories, products, variants and default selling prices.",
            self,
        )
        description.setObjectName("pageDescription")
        layout.addWidget(description)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self._search = QLineEdit(self)
        self._search.setObjectName("productSearch")
        self._search.setPlaceholderText("Search by name, brand or category")
        self._search.setClearButtonEnabled(True)
        self._search.setMaximumWidth(320)
        self._search.textChanged.connect(self._apply_filter)
        toolbar.addWidget(self._search)

        self._show_inactive = QCheckBox("Show inactive", self)
        self._show_inactive.setObjectName("showInactiveProducts")
        self._show_inactive.toggled.connect(self.reload)
        toolbar.addWidget(self._show_inactive)

        refresh = QPushButton("Refresh", self)
        refresh.setObjectName("refreshProductsButton")
        refresh.clicked.connect(self.reload)
        toolbar.addWidget(refresh)

        toolbar.addStretch(1)

        self._new_category_button = QPushButton("New category", self)
        self._new_category_button.setObjectName("newCategoryButton")
        self._new_category_button.clicked.connect(self._create_category)
        toolbar.addWidget(self._new_category_button)

        self._new_product_button = QPushButton("New product", self)
        self._new_product_button.setObjectName("newProductButton")
        self._new_product_button.setProperty("variant", "primary")
        self._new_product_button.clicked.connect(self._create_product)
        toolbar.addWidget(self._new_product_button)

        self._edit_button = QPushButton("Edit", self)
        self._edit_button.setObjectName("editProductButton")
        self._edit_button.clicked.connect(self._edit_product)
        toolbar.addWidget(self._edit_button)

        self._variants_button = QPushButton("Variants", self)
        self._variants_button.setObjectName("manageVariantsButton")
        self._variants_button.clicked.connect(self._manage_variants)
        toolbar.addWidget(self._variants_button)

        self._toggle_button = QPushButton("Deactivate", self)
        self._toggle_button.setObjectName("toggleProductActiveButton")
        self._toggle_button.clicked.connect(self._toggle_product_active)
        toolbar.addWidget(self._toggle_button)

        layout.addLayout(toolbar)

        self._error_banner = QLabel(self)
        self._error_banner.setObjectName("errorBanner")
        self._error_banner.setWordWrap(True)
        self._error_banner.hide()
        layout.addWidget(self._error_banner)

        self._model = ProductTableModel(self)

        self._table = QTableView(self)
        self._table.setObjectName("productsTable")
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
        self._table.doubleClicked.connect(self._edit_product)
        self._table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self._table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(
            5, QHeaderView.ResizeMode.ResizeToContents
        )

        self._empty_title = QLabel("No products yet", self)
        self._empty_title.setObjectName("emptyStateTitle")
        self._empty_hint = QLabel(
            "Create your first product to start building the catalog.",
            self,
        )
        self._empty_hint.setObjectName("emptyStateHint")
        self._empty_hint.setWordWrap(True)
        self._empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)

        empty = QWidget(self)
        empty_layout = QVBoxLayout(empty)
        empty_layout.setContentsMargins(24, 24, 24, 24)
        empty_layout.setSpacing(6)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self._empty_title)
        empty_layout.addWidget(self._empty_hint)
        self._empty = empty

        self._content = QStackedWidget(self)
        self._content.setObjectName("productsContent")
        self._content.addWidget(self._table)
        self._content.addWidget(empty)
        layout.addWidget(self._content, 1)

        self._footer = QLabel(self)
        self._footer.setObjectName("productsFooter")
        layout.addWidget(self._footer)

        self._update_actions()

    def reload(self, *_args) -> None:
        """Reload products from the application service."""
        try:
            products = self._catalog.list_products(
                include_inactive=self._show_inactive.isChecked()
            )
        except Exception as exc:
            self._show_error(f"Could not load products: {exc}")
            return

        self._show_error(None)
        self._products = tuple(products)
        self._apply_filter()

    def _apply_filter(self, *_args) -> None:
        query = self._search.text().strip().casefold()
        rows = self._products
        if query:
            rows = tuple(
                product
                for product in rows
                if query
                in " ".join(
                    part
                    for part in (
                        product.name,
                        product.brand or "",
                        product.category_name or "",
                    )
                    if part
                ).casefold()
            )

        self._model.set_products(rows)
        self._update_actions()
        visible = bool(rows)
        self._content.setCurrentWidget(
            self._table if visible else self._empty
        )

        if not self._products:
            self._empty_title.setText("No products yet")
            self._empty_hint.setText(
                "Create your first product to start building the catalog."
            )
            self._footer.setText("No products")
        elif not rows:
            self._empty_title.setText("No matching products")
            self._empty_hint.setText(
                "Change the search text or include inactive products."
            )
            self._footer.setText(f"0 of {len(self._products)} products")
        else:
            suffix = "product" if len(rows) == 1 else "products"
            if len(rows) == len(self._products):
                self._footer.setText(f"{len(rows)} {suffix}")
            else:
                self._footer.setText(
                    f"{len(rows)} of {len(self._products)} products"
                )

    def _show_error(self, message: str | None) -> None:
        if message is None:
            self._error_banner.clear()
            self._error_banner.hide()
            return
        self._error_banner.setText(message)
        self._error_banner.show()

    def _load_reference_data(
        self,
    ) -> tuple[tuple[Category, ...], tuple[Currency, ...]] | None:
        try:
            categories = tuple(self._catalog.list_categories())
            currencies = tuple(self._catalog.list_enabled_currencies())
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Could not open product form",
                str(exc),
            )
            return None
        return categories, currencies

    def _create_product(self) -> None:
        reference_data = self._load_reference_data()
        if reference_data is None:
            return
        categories, currencies = reference_data
        if not currencies:
            QMessageBox.warning(
                self,
                "No currencies available",
                "Enable at least one currency before creating products.",
            )
            return

        dialog = ProductDialog(
            self._catalog,
            categories,
            currencies,
            base_currency=self._base_currency,
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.reload()

    def _create_category(self) -> None:
        dialog = CategoryDialog(self._catalog, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.reload()

    def _selected_product(self) -> ProductListItem | None:
        indexes = self._table.selectionModel().selectedRows()
        if not indexes:
            return None
        row = indexes[0].row()
        rows = self._model.products()
        if 0 <= row < len(rows):
            return rows[row]
        return None

    def _update_actions(self, *_args) -> None:
        selected = self._selected_product()
        enabled = selected is not None
        self._edit_button.setEnabled(enabled)
        self._variants_button.setEnabled(enabled)
        self._toggle_button.setEnabled(enabled)
        if selected is None:
            self._toggle_button.setText("Deactivate")
        else:
            self._toggle_button.setText(
                "Deactivate" if selected.is_active else "Activate"
            )

    def _edit_product(self, *_args) -> None:
        selected = self._selected_product()
        if selected is None:
            return

        reference_data = self._load_reference_data()
        if reference_data is None:
            return
        categories, currencies = reference_data
        if not currencies:
            QMessageBox.warning(
                self,
                "No currencies available",
                "Enable at least one currency before editing products.",
            )
            return

        dialog = ProductDialog(
            self._catalog,
            categories,
            currencies,
            base_currency=self._base_currency,
            existing=selected,
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.reload()

    def _manage_variants(self) -> None:
        selected = self._selected_product()
        if selected is None:
            return

        dialog = VariantsDialog(self._catalog, selected, parent=self)
        dialog.exec()
        self.reload()

    def _toggle_product_active(self) -> None:
        selected = self._selected_product()
        if selected is None:
            return

        target = not selected.is_active
        action = "Activate" if target else "Deactivate"
        answer = QMessageBox.question(
            self,
            f"{action} product",
            f"{action} product {selected.name!r}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            self._catalog.set_product_active(
                selected.product_id, is_active=target
            )
        except Exception as exc:
            QMessageBox.critical(
                self, f"Could not {action.lower()} product", str(exc)
            )
            return
        self.reload()
