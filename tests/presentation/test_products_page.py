"""Products screen and dialog tests (headless)."""

from __future__ import annotations

from types import SimpleNamespace

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QStackedWidget,
    QTableView,
    QTreeWidget,
)

from app.application.attributes.manage_attributes import AttributeSummary
from app.application.products.list_products import ProductListItem
from app.application.products.variants import VariantListItem
from app.domain.entities.attribute import Attribute, AttributeValue
from app.domain.entities.category import Category
from app.domain.entities.currency import Currency
from app.domain.value_objects.money import Money
from app.infrastructure.config.settings import Settings
from app.presentation.desktop.app import build_main_window
from app.presentation.desktop.dialogs.catalog import (
    CategoryDialog,
    ProductDialog,
)
from app.presentation.desktop.dialogs.variants import (
    AttributesDialog,
    VariantDialog,
    VariantsDialog,
)
from app.presentation.desktop.navigation import NAVIGATION_ITEMS
from app.presentation.desktop.views.products import ProductsPage

USD = Currency(code="USD", name="US Dollar", decimal_places=2)
EUR = Currency(code="EUR", name="Euro", decimal_places=2)


class FakeCatalog:
    def __init__(
        self,
        products=(),
        categories=(),
        currencies=(),
        variants=(),
        attribute_summaries=(),
    ) -> None:
        self.products = tuple(products)
        self.categories = tuple(categories)
        self.currencies = tuple(currencies)
        self.variants = tuple(variants)
        self.attribute_summaries = tuple(attribute_summaries)
        self.list_calls: list[bool] = []
        self.created_products: list = []
        self.created_categories: list = []
        self.updated_products: list = []
        self.product_active_changes: list[tuple[int, bool]] = []
        self.created_variants: list = []
        self.updated_variants: list = []
        self.variant_active_changes: list[tuple[int, bool]] = []
        self.created_attributes: list = []
        self.created_attribute_values: list = []

    def list_products(self, *, include_inactive: bool = False):
        self.list_calls.append(include_inactive)
        if include_inactive:
            return self.products
        return tuple(product for product in self.products if product.is_active)

    def create_product(self, request):
        self.created_products.append(request)
        return SimpleNamespace(id=len(self.created_products))

    def update_product(self, request):
        self.updated_products.append(request)
        return SimpleNamespace(id=request.product_id)

    def set_product_active(self, product_id: int, *, is_active: bool):
        self.product_active_changes.append((product_id, is_active))
        return SimpleNamespace(id=product_id, is_active=is_active)

    def list_categories(self):
        return self.categories

    def create_category(self, request):
        self.created_categories.append(request)
        return Category(
            name=request.name,
            description=request.description,
            id=len(self.created_categories),
        )

    def list_enabled_currencies(self):
        return self.currencies

    def list_variants(
        self, product_id: int, *, include_inactive: bool = False
    ):
        if include_inactive:
            return self.variants
        return tuple(
            variant for variant in self.variants if variant.is_active
        )

    def create_variant(self, request):
        self.created_variants.append(request)
        return SimpleNamespace(id=len(self.created_variants))

    def update_variant(self, request):
        self.updated_variants.append(request)
        return SimpleNamespace(id=request.variant_id)

    def set_variant_active(self, variant_id: int, *, is_active: bool):
        self.variant_active_changes.append((variant_id, is_active))
        return SimpleNamespace(id=variant_id, is_active=is_active)

    def list_attributes(self):
        return self.attribute_summaries

    def create_attribute(self, request):
        self.created_attributes.append(request)
        return Attribute(name=request.name, id=len(self.created_attributes))

    def create_attribute_value(self, request):
        self.created_attribute_values.append(request)
        return AttributeValue(
            attribute_id=request.attribute_id,
            value=request.value,
            id=len(self.created_attribute_values),
        )


def _item(
    name: str,
    *,
    price: str | None = None,
    active: bool = True,
    category: str | None = None,
    category_id: int | None = None,
    description: str | None = None,
    product_id: int = 1,
) -> ProductListItem:
    return ProductListItem(
        product_id=product_id,
        name=name,
        brand="North",
        category_id=category_id,
        category_name=category,
        description=description,
        default_selling_price=(
            Money(price, USD) if price is not None else None
        ),
        variant_count=1,
        is_active=active,
    )


def test_products_page_shows_rows_and_formatted_money(qapp) -> None:
    catalog = FakeCatalog(
        products=(
            _item("T-Shirt", price="19.99", category="Clothing"),
            _item("Mug", price="5", product_id=2),
        )
    )
    page = ProductsPage(catalog, base_currency="USD")
    try:
        table = page.findChild(QTableView, "productsTable")
        assert table is not None
        model = table.model()

        assert model.rowCount() == 2
        assert model.data(model.index(0, 0)) == "T-Shirt"
        assert model.data(model.index(0, 2)) == "Clothing"
        assert model.data(model.index(0, 4)) == "19.99 USD"
        assert model.data(model.index(0, 5)) == "Active"

        footer = page.findChild(QLabel, "productsFooter")
        assert footer is not None
        assert footer.text() == "2 products"
    finally:
        page.close()


def test_search_filters_by_name_brand_or_category(qapp) -> None:
    catalog = FakeCatalog(
        products=(
            _item("Red Shirt", category="Clothing"),
            _item("Blue Mug", product_id=2),
        )
    )
    page = ProductsPage(catalog, base_currency="USD")
    try:
        search = page.findChild(QLineEdit, "productSearch")
        table = page.findChild(QTableView, "productsTable")
        footer = page.findChild(QLabel, "productsFooter")
        assert search is not None
        assert table is not None
        assert footer is not None

        search.setText("mug")
        assert table.model().rowCount() == 1
        assert table.model().data(table.model().index(0, 0)) == "Blue Mug"
        assert footer.text() == "1 of 2 products"

        search.clear()
        assert table.model().rowCount() == 2
    finally:
        page.close()


def test_show_inactive_reloads_with_the_flag(qapp) -> None:
    catalog = FakeCatalog(
        products=(
            _item("Current"),
            _item("Retired", active=False, product_id=2),
        )
    )
    page = ProductsPage(catalog, base_currency="USD")
    try:
        table = page.findChild(QTableView, "productsTable")
        checkbox = page.findChild(QCheckBox, "showInactiveProducts")
        assert table is not None
        assert checkbox is not None
        assert table.model().rowCount() == 1

        checkbox.setChecked(True)

        assert catalog.list_calls[-1] is True
        assert table.model().rowCount() == 2
    finally:
        page.close()


def test_load_errors_are_shown_inline_instead_of_crashing(qapp) -> None:
    class BrokenCatalog(FakeCatalog):
        def list_products(self, *, include_inactive: bool = False):
            raise RuntimeError("database unavailable")

    page = ProductsPage(BrokenCatalog(), base_currency="USD")
    try:
        banner = page.findChild(QLabel, "errorBanner")
        assert banner is not None
        assert banner.text() == "Could not load products: database unavailable"
        assert not banner.isHidden()
    finally:
        page.close()


def test_empty_catalog_shows_the_empty_state(qapp) -> None:
    page = ProductsPage(FakeCatalog(), base_currency="USD")
    try:
        table = page.findChild(QTableView, "productsTable")
        stack = page.findChild(QStackedWidget, "productsContent")
        footer = page.findChild(QLabel, "productsFooter")
        assert table is not None
        assert stack is not None
        assert footer is not None

        assert stack.currentWidget() is not table
        assert footer.text() == "No products"
    finally:
        page.close()


def test_main_window_uses_the_real_products_screen(qapp) -> None:
    catalog = FakeCatalog(
        categories=(Category(name="Clothing", id=1),),
        currencies=(USD,),
    )
    window = build_main_window(Settings(base_currency="USD"), catalog)
    try:
        stack = window.findChild(QStackedWidget, "pageStack")
        assert stack is not None
        product_index = [item.key for item in NAVIGATION_ITEMS].index(
            "products"
        )
        assert isinstance(stack.widget(product_index), ProductsPage)
    finally:
        window.close()


def test_product_dialog_sends_a_complete_request(qapp) -> None:
    category = Category(name="Clothing", id=1)
    catalog = FakeCatalog(
        categories=(category,),
        currencies=(EUR, USD),
    )
    dialog = ProductDialog(
        catalog,
        catalog.categories,
        catalog.currencies,
        base_currency="USD",
    )
    try:
        dialog.findChild(QLineEdit, "productName").setText("T-Shirt")
        dialog.findChild(QLineEdit, "productBrand").setText("North")
        dialog.findChild(QLineEdit, "productPrice").setText("19.99")
        dialog.findChild(QPlainTextEdit, "productDescription").setPlainText(
            "Cotton shirt"
        )
        dialog.findChild(QComboBox, "productCategory").setCurrentIndex(1)
        dialog.findChild(QLineEdit, "productSku").setText("TS-001")
        dialog.findChild(QLineEdit, "productVariantName").setText("Red")

        currency = dialog.findChild(QComboBox, "productCurrency")
        assert currency is not None
        assert currency.currentData().code == "USD"

        dialog.findChild(QPushButton, "createProductButton").click()

        assert dialog.result() == QDialog.DialogCode.Accepted
        assert len(catalog.created_products) == 1
        request = catalog.created_products[0]
        assert request.name == "T-Shirt"
        assert request.brand == "North"
        assert request.category_id == 1
        assert request.description == "Cotton shirt"
        assert request.default_selling_price == Money("19.99", USD)
        assert len(request.variants) == 1
        assert request.variants[0].sku == "TS-001"
        assert request.variants[0].variant_name == "Red"
    finally:
        dialog.close()


def test_product_dialog_uses_the_default_variant_when_no_variant_is_typed(
    qapp,
) -> None:
    catalog = FakeCatalog(currencies=(USD,))
    dialog = ProductDialog(
        catalog,
        (),
        catalog.currencies,
        base_currency="USD",
    )
    try:
        dialog.findChild(QLineEdit, "productName").setText("Plain Mug")
        dialog.findChild(QPushButton, "createProductButton").click()

        request = catalog.created_products[0]
        assert request.default_selling_price is None
        assert request.variants == ()
    finally:
        dialog.close()


def test_category_dialog_sends_a_category_request(qapp) -> None:
    catalog = FakeCatalog()
    dialog = CategoryDialog(catalog)
    try:
        dialog.findChild(QLineEdit, "categoryName").setText("Clothing")
        dialog.findChild(
            QPlainTextEdit, "categoryDescription"
        ).setPlainText("Apparel")
        dialog.findChild(QPushButton, "createCategoryButton").click()

        assert dialog.result() == QDialog.DialogCode.Accepted
        assert len(catalog.created_categories) == 1
        request = catalog.created_categories[0]
        assert request.name == "Clothing"
        assert request.description == "Apparel"
    finally:
        dialog.close()


def test_product_dialog_edit_mode_prefills_and_updates(qapp) -> None:
    existing = _item(
        "T-Shirt",
        price="19.99",
        category="Clothing",
        category_id=1,
        description="Cotton shirt",
        product_id=7,
    )
    catalog = FakeCatalog(
        categories=(Category(name="Clothing", id=1),),
        currencies=(EUR, USD),
    )
    dialog = ProductDialog(
        catalog,
        catalog.categories,
        catalog.currencies,
        base_currency="USD",
        existing=existing,
    )
    try:
        assert dialog.findChild(QLineEdit, "productName").text() == "T-Shirt"
        assert dialog.findChild(QLineEdit, "productPrice").text() == "19.99"
        category = dialog.findChild(QComboBox, "productCategory")
        assert category.currentData() == 1
        currency = dialog.findChild(QComboBox, "productCurrency")
        assert currency.currentData().code == "USD"
        assert (
            dialog.findChild(
                QPlainTextEdit, "productDescription"
            ).toPlainText()
            == "Cotton shirt"
        )
        variant_group = dialog.findChild(
            QGroupBox, "initialVariantGroup"
        )
        assert variant_group is not None
        assert variant_group.isHidden()

        dialog.findChild(QLineEdit, "productName").setText("Updated T-Shirt")
        dialog.findChild(QLineEdit, "productPrice").setText("21.50")
        dialog.findChild(QPushButton, "createProductButton").click()

        assert dialog.result() == QDialog.DialogCode.Accepted
        assert len(catalog.updated_products) == 1
        request = catalog.updated_products[0]
        assert request.product_id == 7
        assert request.name == "Updated T-Shirt"
        assert request.category_id == 1
        assert request.default_selling_price == Money("21.50", USD)
        assert request.description == "Cotton shirt"
    finally:
        dialog.close()


def test_edit_dialog_keeps_a_disabled_price_currency(qapp) -> None:
    existing = _item("Legacy", price="5.00", product_id=4)
    catalog = FakeCatalog(currencies=(EUR,))
    dialog = ProductDialog(
        catalog,
        (),
        catalog.currencies,
        base_currency="USD",
        existing=existing,
    )
    try:
        currency = dialog.findChild(QComboBox, "productCurrency")
        assert currency is not None
        assert currency.currentData().code == "USD"
    finally:
        dialog.close()


def test_products_page_toggles_the_selected_product(
    qapp, monkeypatch
) -> None:
    catalog = FakeCatalog(products=(_item("T-Shirt"),))
    page = ProductsPage(catalog, base_currency="USD")
    try:
        table = page.findChild(QTableView, "productsTable")
        button = page.findChild(QPushButton, "toggleProductActiveButton")
        assert table is not None
        assert button is not None
        assert not button.isEnabled()

        table.selectRow(0)
        assert button.isEnabled()
        assert button.text() == "Deactivate"

        monkeypatch.setattr(
            QMessageBox,
            "question",
            lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
        )
        button.click()

        assert catalog.product_active_changes == [(1, False)]
    finally:
        page.close()


def test_variants_dialog_lists_and_toggles_variants(
    qapp, monkeypatch
) -> None:
    summary = AttributeSummary(
        attribute_id=1,
        name="Color",
        values=(
            AttributeValue(attribute_id=1, value="Red", id=10),
            AttributeValue(attribute_id=1, value="Blue", id=11),
        ),
    )
    variant = VariantListItem(
        variant_id=5,
        product_id=1,
        sku="TS-001",
        variant_name="Red",
        barcode=None,
        is_active=True,
        attribute_value_ids=(10,),
        attribute_labels=("Color: Red",),
    )
    catalog = FakeCatalog(
        variants=(variant,),
        attribute_summaries=(summary,),
    )
    dialog = VariantsDialog(catalog, _item("T-Shirt"))
    try:
        table = dialog.findChild(QTableView, "variantsTable")
        assert table is not None
        assert table.model().rowCount() == 1
        assert table.model().data(table.model().index(0, 3)) == "Color: Red"

        table.selectRow(0)
        monkeypatch.setattr(
            QMessageBox,
            "question",
            lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
        )
        dialog.findChild(QPushButton, "toggleVariantButton").click()

        assert catalog.variant_active_changes == [(5, False)]
    finally:
        dialog.close()


def test_variant_dialog_assigns_attribute_values(qapp) -> None:
    summary = AttributeSummary(
        attribute_id=1,
        name="Color",
        values=(
            AttributeValue(attribute_id=1, value="Red", id=10),
            AttributeValue(attribute_id=1, value="Blue", id=11),
        ),
    )
    catalog = FakeCatalog(attribute_summaries=(summary,))
    dialog = VariantDialog(catalog, 1, (summary,))
    try:
        dialog.findChild(QLineEdit, "variantSku").setText("TS-002")
        dialog.findChild(QLineEdit, "variantName").setText("Blue")
        combo = dialog.findChild(QComboBox, "variantAttribute")
        assert combo is not None
        combo.setCurrentIndex(2)
        dialog.findChild(QPushButton, "saveVariantButton").click()

        assert dialog.result() == QDialog.DialogCode.Accepted
        assert len(catalog.created_variants) == 1
        request = catalog.created_variants[0]
        assert request.product_id == 1
        assert request.sku == "TS-002"
        assert request.variant_name == "Blue"
        assert request.attribute_value_ids == (11,)
    finally:
        dialog.close()


def test_attribute_dialog_creates_attributes_and_values(qapp) -> None:
    summary = AttributeSummary(
        attribute_id=1,
        name="Color",
        values=(AttributeValue(attribute_id=1, value="Red", id=10),),
    )
    catalog = FakeCatalog(attribute_summaries=(summary,))
    dialog = AttributesDialog(catalog)
    try:
        tree = dialog.findChild(QTreeWidget, "attributesTree")
        assert tree is not None
        assert tree.topLevelItemCount() == 1
        assert tree.topLevelItem(0).childCount() == 1

        tree.setCurrentItem(tree.topLevelItem(0))
        dialog.findChild(QLineEdit, "newAttributeValue").setText("Green")
        dialog.findChild(QPushButton, "addAttributeValueButton").click()

        assert len(catalog.created_attribute_values) == 1
        value_request = catalog.created_attribute_values[0]
        assert value_request.attribute_id == 1
        assert value_request.value == "Green"

        dialog.findChild(QLineEdit, "newAttributeName").setText("Size")
        dialog.findChild(QPushButton, "addAttributeButton").click()

        assert len(catalog.created_attributes) == 1
        assert catalog.created_attributes[0].name == "Size"
    finally:
        dialog.close()
