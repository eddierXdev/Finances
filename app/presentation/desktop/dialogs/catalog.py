"""Catalog dialogs for creating products and categories."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal, InvalidOperation

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.application.products.catalog import ProductCatalogService
from app.application.products.categories import CreateCategoryRequest
from app.application.products.create_product import (
    CreateProductRequest,
    ProductVariantRequest,
)
from app.application.products.list_products import ProductListItem
from app.application.products.update_product import UpdateProductRequest
from app.domain.entities.category import Category
from app.domain.entities.currency import Currency
from app.domain.value_objects.money import Money


class ProductDialog(QDialog):
    """Collect and persist a new or edited product.

    The dialog calls the application service. It never writes to the database
    and never calculates prices or stock.
    """

    def __init__(
        self,
        catalog: ProductCatalogService,
        categories: Sequence[Category],
        currencies: Sequence[Currency],
        *,
        base_currency: str,
        existing: ProductListItem | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        if not currencies:
            raise ValueError("At least one enabled currency is required.")

        self._catalog = catalog
        self._categories = tuple(categories)
        self._currencies = tuple(currencies)
        self._base_currency = base_currency
        self._existing = existing

        self.setWindowTitle(
            "Edit product" if existing is not None else "New product"
        )
        self.setModal(True)
        self.resize(520, 540)
        self._build_ui()
        if existing is not None:
            self._apply_existing(existing)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        self._title = QLabel("New product", self)
        self._title.setObjectName("dialogTitle")
        layout.addWidget(self._title)

        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self._name = QLineEdit(self)
        self._name.setObjectName("productName")
        self._name.setPlaceholderText("Product name")
        form.addRow("Name *", self._name)

        self._category = QComboBox(self)
        self._category.setObjectName("productCategory")
        self._category.addItem("No category", None)
        for category in self._categories:
            self._category.addItem(category.name, category.id)
        form.addRow("Category", self._category)

        self._brand = QLineEdit(self)
        self._brand.setObjectName("productBrand")
        self._brand.setPlaceholderText("Optional brand")
        form.addRow("Brand", self._brand)

        price_row = QHBoxLayout()
        self._price = QLineEdit(self)
        self._price.setObjectName("productPrice")
        self._price.setPlaceholderText("Leave empty for no default price")
        price_row.addWidget(self._price, 1)

        self._currency = QComboBox(self)
        self._currency.setObjectName("productCurrency")
        self._currency.setFixedWidth(92)
        default_index = 0
        for index, currency in enumerate(self._currencies):
            self._currency.addItem(currency.code, currency)
            if currency.code == self._base_currency:
                default_index = index
        self._currency.setCurrentIndex(default_index)
        price_row.addWidget(self._currency)
        form.addRow("Default price", price_row)

        self._description = QPlainTextEdit(self)
        self._description.setObjectName("productDescription")
        self._description.setPlaceholderText("Optional description")
        self._description.setFixedHeight(74)
        form.addRow("Description", self._description)

        layout.addLayout(form)

        variant_group = QGroupBox("Initial variant (optional)", self)
        variant_group.setObjectName("initialVariantGroup")
        variant_form = QFormLayout(variant_group)
        self._variant_group = variant_group
        self._sku = QLineEdit(variant_group)
        self._sku.setObjectName("productSku")
        self._sku.setPlaceholderText("Optional unique SKU")
        variant_form.addRow("SKU", self._sku)

        self._variant_name = QLineEdit(variant_group)
        self._variant_name.setObjectName("productVariantName")
        self._variant_name.setPlaceholderText("For example: Red, Large")
        variant_form.addRow("Variant name", self._variant_name)

        variant_note = QLabel(
            "Leave both fields empty to create the internal default variant.",
            variant_group,
        )
        variant_note.setObjectName("fieldHint")
        variant_note.setWordWrap(True)
        variant_form.addRow(variant_note)
        layout.addWidget(variant_group)

        layout.addStretch(1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel, self)
        self._create_button = QPushButton("Create product", self)
        self._create_button.setObjectName("createProductButton")
        self._create_button.setProperty("variant", "primary")
        self._create_button.setDefault(True)
        buttons.addButton(
            self._create_button, QDialogButtonBox.ButtonRole.AcceptRole
        )
        buttons.rejected.connect(self.reject)
        self._create_button.clicked.connect(self._submit)
        layout.addWidget(buttons)

    def _submit(self) -> None:
        try:
            fields = self._parse_fields()
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid product", str(exc))
            return

        try:
            if self._existing is None:
                self._catalog.create_product(self._build_request(fields))
            else:
                self._catalog.update_product(
                    self._build_update_request(fields)
                )
        except Exception as exc:
            QMessageBox.critical(
                self,
                (
                    "Could not update product"
                    if self._existing is not None
                    else "Could not create product"
                ),
                str(exc),
            )
            return

        self.accept()

    def _apply_existing(self, existing: ProductListItem) -> None:
        self._title.setText("Edit product")
        self._create_button.setText("Save changes")
        self._name.setText(existing.name)
        self._brand.setText(existing.brand or "")
        self._description.setPlainText(existing.description or "")

        if existing.category_id is not None:
            index = self._category.findData(existing.category_id)
            if index >= 0:
                self._category.setCurrentIndex(index)

        if existing.default_selling_price is not None:
            self._price.setText(
                format(existing.default_selling_price.amount, "f")
            )
            currency_code = (
                existing.default_selling_price.currency.code
            )
            selected_index = -1
            for index in range(self._currency.count()):
                currency = self._currency.itemData(index)
                if (
                    isinstance(currency, Currency)
                    and currency.code == currency_code
                ):
                    selected_index = index
                    break
            if selected_index < 0:
                self._currency.addItem(
                    existing.default_selling_price.currency.code,
                    existing.default_selling_price.currency,
                )
                selected_index = self._currency.count() - 1
            self._currency.setCurrentIndex(selected_index)

        self._variant_group.hide()

    def _parse_fields(
        self,
    ) -> tuple[str, int | None, str | None, str | None, Money | None]:
        name = self._name.text().strip()
        if not name:
            raise ValueError("Product name is required.")

        category_id = self._category.currentData()
        if category_id is not None and (
            isinstance(category_id, bool)
            or not isinstance(category_id, int)
        ):
            raise ValueError("Select a valid category.")

        price_text = self._price.text().strip()
        price = None
        if price_text:
            currency = self._currency.currentData()
            if not isinstance(currency, Currency):
                raise ValueError(
                    "Select a currency for the default selling price."
                )

            try:
                amount = Decimal(price_text)
            except InvalidOperation as exc:
                raise ValueError(
                    "Default price must be a valid decimal amount."
                ) from exc
            if not amount.is_finite():
                raise ValueError(
                    "Default price must be a valid decimal amount."
                )

            price = Money(amount, currency)
            if price.is_negative:
                raise ValueError("Default price cannot be negative.")

        return (
            name,
            category_id,
            self._description.toPlainText().strip() or None,
            self._brand.text().strip() or None,
            price,
        )

    def _build_request(
        self,
        fields: tuple[
            str, int | None, str | None, str | None, Money | None
        ],
    ) -> CreateProductRequest:
        name, category_id, description, brand, price = fields

        sku = self._sku.text().strip() or None
        variant_name = self._variant_name.text().strip() or None
        variants: tuple[ProductVariantRequest, ...] = ()
        if sku is not None or variant_name is not None:
            variants = (
                ProductVariantRequest(
                    sku=sku,
                    variant_name=variant_name,
                ),
            )

        return CreateProductRequest(
            name=name,
            category_id=category_id,
            description=description,
            brand=brand,
            default_selling_price=price,
            variants=variants,
        )

    def _build_update_request(
        self,
        fields: tuple[
            str, int | None, str | None, str | None, Money | None
        ],
    ) -> UpdateProductRequest:
        if self._existing is None:
            raise RuntimeError("Update request requires an existing product.")

        name, category_id, description, brand, price = fields
        return UpdateProductRequest(
            product_id=self._existing.product_id,
            name=name,
            category_id=category_id,
            description=description,
            brand=brand,
            default_selling_price=price,
        )


class CategoryDialog(QDialog):
    """Collect and persist a new product category."""

    def __init__(
        self,
        catalog: ProductCatalogService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._catalog = catalog
        self.setWindowTitle("New category")
        self.setModal(True)
        self.resize(420, 240)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel("New category", self)
        title.setObjectName("dialogTitle")
        layout.addWidget(title)

        form = QFormLayout()
        self._name = QLineEdit(self)
        self._name.setObjectName("categoryName")
        self._name.setPlaceholderText("Category name")
        form.addRow("Name *", self._name)

        self._description = QPlainTextEdit(self)
        self._description.setObjectName("categoryDescription")
        self._description.setPlaceholderText("Optional description")
        self._description.setFixedHeight(70)
        form.addRow("Description", self._description)
        layout.addLayout(form)
        layout.addStretch(1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel, self)
        self._create_button = QPushButton("Create category", self)
        self._create_button.setObjectName("createCategoryButton")
        self._create_button.setProperty("variant", "primary")
        self._create_button.setDefault(True)
        buttons.addButton(
            self._create_button, QDialogButtonBox.ButtonRole.AcceptRole
        )
        buttons.rejected.connect(self.reject)
        self._create_button.clicked.connect(self._submit)
        layout.addWidget(buttons)

    def _submit(self) -> None:
        name = self._name.text().strip()
        if not name:
            QMessageBox.warning(self, "Invalid category", "Name is required.")
            return

        try:
            self._catalog.create_category(
                CreateCategoryRequest(
                    name=name,
                    description=(
                        self._description.toPlainText().strip() or None
                    ),
                )
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Could not create category",
                str(exc),
            )
            return

        self.accept()
