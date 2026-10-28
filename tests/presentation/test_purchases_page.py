"""Purchases screen and dialog tests (headless)."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QStackedWidget,
    QTableView,
    QTableWidget,
)

from app.application.purchases.list_purchases import (
    PurchaseCostDetail,
    PurchaseDetail,
    PurchaseItemDetail,
    PurchaseListItem,
    VariantOption,
)
from app.application.purchases.register_purchase_payment import (
    RegisterPurchasePaymentRequest,
)
from app.application.purchases.update_purchase_status import (
    UpdatePurchaseStatusRequest,
)
from app.domain.entities.account import Account
from app.domain.entities.currency import Currency
from app.domain.entities.supplier import Supplier
from app.domain.enums.allocation_method import AllocationMethod
from app.domain.enums.purchase_cost_type import PurchaseCostType
from app.domain.enums.purchase_status import PurchaseStatus
from app.domain.value_objects.money import Money
from app.infrastructure.config.settings import Settings
from app.presentation.desktop.app import build_main_window
from app.presentation.desktop.dialogs.purchases import (
    PurchaseDetailDialog,
    PurchaseDialog,
    PurchasePaymentDialog,
    PurchaseStatusDialog,
    SupplierDialog,
)
from app.presentation.desktop.navigation import NAVIGATION_ITEMS
from app.presentation.desktop.views.purchases import PurchasesPage

USD = Currency(code="USD", name="US Dollar", decimal_places=2)
EUR = Currency(code="EUR", name="Euro", decimal_places=2)


class FakePurchases:
    def __init__(
        self,
        rows=(),
        *,
        currencies=(USD,),
        suppliers=(),
        accounts=(),
        variants=(),
        detail=None,
    ) -> None:
        self.rows = tuple(rows)
        self.currencies = tuple(currencies)
        self.suppliers = tuple(suppliers)
        self.accounts = tuple(accounts)
        self.variants = tuple(variants)
        self.detail = detail
        self.created_requests: list = []
        self.payments: list[RegisterPurchasePaymentRequest] = []
        self.status_updates: list[UpdatePurchaseStatusRequest] = []
        self.created_suppliers: list = []

    def list_purchases(self):
        return self.rows

    def get_purchase_detail(self, purchase_id: int):
        assert self.detail is not None
        return self.detail

    def list_suppliers(self, *, include_inactive: bool = False):
        return self.suppliers

    def create_supplier(self, request):
        self.created_suppliers.append(request)
        return Supplier(name=request.name, id=len(self.created_suppliers))

    def list_accounts(self, *, include_inactive: bool = False):
        return self.accounts

    def list_enabled_currencies(self):
        return self.currencies

    def list_variant_options(self):
        return self.variants

    def create_purchase(self, request):
        self.created_requests.append(request)
        return SimpleNamespace(purchase=SimpleNamespace(id=1))

    def register_payment(self, request):
        self.payments.append(request)
        return SimpleNamespace(id=request.purchase_id)

    def update_status(self, request):
        self.status_updates.append(request)
        return SimpleNamespace(id=request.purchase_id)


def _row(
    purchase_id: int = 1,
    *,
    supplier: str | None = "Acme",
    status: PurchaseStatus = PurchaseStatus.PENDING,
    total: str = "25.00",
    account: str | None = None,
    allowed=(PurchaseStatus.CANCELLED,),
    order: str | None = "ORD-1",
    tracking: str | None = "TRACK-1",
    currency: Currency = USD,
) -> PurchaseListItem:
    return PurchaseListItem(
        purchase_id=purchase_id,
        purchase_date=datetime(2026, 10, 27, 12, 0, tzinfo=UTC),
        supplier_id=1 if supplier else None,
        supplier_name=supplier,
        currency_code=currency.code,
        item_count=2,
        total=Money(total, currency),
        status=status,
        account_name=account,
        order_number=order,
        tracking_number=tracking,
        notes=None,
        allowed_statuses=tuple(allowed),
    )


def _variant() -> VariantOption:
    return VariantOption(
        variant_id=1,
        label="Phone / Black (PHONE-1)",
        product_name="Phone",
        variant_name="Black",
        sku="PHONE-1",
    )


def _account() -> Account:
    return Account(name="Cash USD", currency=USD, id=1)


def _supplier() -> Supplier:
    return Supplier(name="Acme Trading", id=1)


def test_purchases_page_lists_totals_payments_and_status(qapp) -> None:
    service = FakePurchases(
        rows=(
            _row(1),
            _row(
                2,
                status=PurchaseStatus.PURCHASED,
                account="Cash USD",
                allowed=(PurchaseStatus.SHIPPED, PurchaseStatus.IN_TRANSIT),
            ),
        )
    )
    page = PurchasesPage(service, base_currency="USD")
    try:
        table = page.findChild(QTableView, "purchasesTable")
        footer = page.findChild(QLabel, "purchasesFooter")
        assert table is not None
        assert footer is not None
        model = table.model()
        assert model.rowCount() == 2
        assert model.data(model.index(0, 0)) == "2026-10-27"
        assert model.data(model.index(0, 1)) == "Acme"
        assert model.data(model.index(0, 4)) == "25.00 USD"
        assert model.data(model.index(0, 5)) == "Unpaid"
        assert model.data(model.index(0, 6)) == "Pending"
        assert model.data(model.index(1, 5)) == "Paid · Cash USD"
        assert model.data(model.index(1, 6)) == "Purchased"
        assert footer.text() == "2 purchases"
    finally:
        page.close()


def test_purchase_search_and_status_filter(qapp) -> None:
    service = FakePurchases(
        rows=(
            _row(1),
            _row(
                2,
                status=PurchaseStatus.PURCHASED,
                account="Cash USD",
                allowed=(PurchaseStatus.SHIPPED,),
            ),
        )
    )
    page = PurchasesPage(service, base_currency="USD")
    try:
        search = page.findChild(QLineEdit, "purchaseSearch")
        status = page.findChild(QComboBox, "purchaseStatusFilter")
        table = page.findChild(QTableView, "purchasesTable")
        footer = page.findChild(QLabel, "purchasesFooter")
        stack = page.findChild(QStackedWidget, "purchasesContent")
        assert search is not None
        assert status is not None
        assert table is not None
        assert footer is not None
        assert stack is not None

        index = status.findData(PurchaseStatus.PURCHASED)
        status.setCurrentIndex(index)
        assert table.model().rowCount() == 1
        assert table.model().data(table.model().index(0, 0)) == "2026-10-27"
        assert footer.text() == "1 of 2 purchases"

        search.setText("missing")
        assert stack.currentWidget() is not table
        assert footer.text() == "0 of 2 purchases"

        search.clear()
        status.setCurrentIndex(0)
        assert table.model().rowCount() == 2
    finally:
        page.close()


def test_purchase_selection_enables_only_valid_actions(qapp) -> None:
    service = FakePurchases(
        rows=(
            _row(1),
            _row(
                2,
                status=PurchaseStatus.RECEIVED,
                account="Cash USD",
                allowed=(),
            ),
        )
    )
    page = PurchasesPage(service, base_currency="USD")
    try:
        table = page.findChild(QTableView, "purchasesTable")
        detail = page.findChild(QPushButton, "purchaseDetailButton")
        pay = page.findChild(QPushButton, "purchasePayButton")
        status = page.findChild(QPushButton, "purchaseStatusButton")
        assert table is not None
        assert detail is not None
        assert pay is not None
        assert status is not None
        assert not detail.isEnabled()
        assert not pay.isEnabled()
        assert not status.isEnabled()

        table.selectRow(0)
        assert detail.isEnabled()
        assert pay.isEnabled()
        assert status.isEnabled()

        table.selectRow(1)
        assert detail.isEnabled()
        assert not pay.isEnabled()
        assert not status.isEnabled()
    finally:
        page.close()


def test_empty_purchases_page_shows_empty_state(qapp) -> None:
    page = PurchasesPage(FakePurchases(), base_currency="USD")
    try:
        table = page.findChild(QTableView, "purchasesTable")
        stack = page.findChild(QStackedWidget, "purchasesContent")
        footer = page.findChild(QLabel, "purchasesFooter")
        assert table is not None
        assert stack is not None
        assert footer is not None
        assert stack.currentWidget() is not table
        assert footer.text() == "No purchases"
    finally:
        page.close()


def test_purchase_dialog_sends_items_costs_and_payment(qapp) -> None:
    service = FakePurchases(
        suppliers=(_supplier(),),
        accounts=(_account(),),
        variants=(_variant(),),
    )
    dialog = PurchaseDialog(
        service,
        currencies=(USD,),
        suppliers=service.suppliers,
        accounts=service.accounts,
        variants=service.variants,
        base_currency="USD",
    )
    try:
        dialog.findChild(QLineEdit, "purchaseOrderNumber").setText("ORD-9")
        dialog.findChild(QLineEdit, "purchaseTrackingNumber").setText(
            "TRACK-9"
        )
        supplier = dialog.findChild(QComboBox, "purchaseSupplier")
        account = dialog.findChild(QComboBox, "purchasePaymentAccount")
        assert supplier is not None
        assert account is not None
        supplier.setCurrentIndex(supplier.findData(1))
        account.setCurrentIndex(account.findData(1))

        items = dialog.findChild(QTableWidget, "purchaseItemsTable")
        assert items is not None
        items.cellWidget(0, 1).setValue(2)
        items.cellWidget(0, 2).setText("10.00")

        dialog.findChild(QPushButton, "addPurchaseCostButton").click()
        costs = dialog.findChild(QTableWidget, "purchaseCostsTable")
        assert costs is not None
        costs.cellWidget(0, 1).setText("5.00")

        dialog.findChild(QPushButton, "createPurchaseButton").click()

        assert dialog.result() == QDialog.DialogCode.Accepted
        assert len(service.created_requests) == 1
        request = service.created_requests[0]
        assert request.currency == USD
        assert request.supplier_id == 1
        assert request.account_id == 1
        assert request.order_number == "ORD-9"
        assert request.tracking_number == "TRACK-9"
        assert len(request.items) == 1
        assert request.items[0].variant_id == 1
        assert request.items[0].quantity == 2
        assert request.items[0].unit_price == Money("10.00", USD)
        assert len(request.costs) == 1
        assert request.costs[0].cost_type is PurchaseCostType.SHIPPING
        assert request.costs[0].amount == Money("5.00", USD)
        assert (
            request.costs[0].allocation_method
            is AllocationMethod.BY_QUANTITY
        )
    finally:
        dialog.close()


def test_supplier_dialog_creates_a_supplier(qapp) -> None:
    service = FakePurchases()
    dialog = SupplierDialog(service)
    try:
        dialog.findChild(QLineEdit, "supplierName").setText("Acme Trading")
        dialog.findChild(QLineEdit, "supplierContact").setText("sales@acme")
        dialog.findChild(QPushButton, "createSupplierButton").click()

        assert dialog.result() == QDialog.DialogCode.Accepted
        assert len(service.created_suppliers) == 1
        request = service.created_suppliers[0]
        assert request.name == "Acme Trading"
        assert request.contact == "sales@acme"
        assert dialog.created_supplier is not None
        assert dialog.created_supplier.id == 1
    finally:
        dialog.close()


def test_payment_dialog_uses_matching_currency_accounts(qapp) -> None:
    service = FakePurchases(
        accounts=(
            _account(),
            Account(name="Euro Wallet", currency=EUR, id=2),
        )
    )
    dialog = PurchasePaymentDialog(
        service,
        _row(1),
        service.accounts,
    )
    try:
        account = dialog.findChild(QComboBox, "purchasePaymentDialogAccount")
        assert account is not None
        assert account.count() == 1
        assert account.currentData() == 1
        dialog.findChild(
            QPushButton, "registerPurchasePaymentButton"
        ).click()

        assert dialog.result() == QDialog.DialogCode.Accepted
        assert len(service.payments) == 1
        assert service.payments[0].purchase_id == 1
        assert service.payments[0].account_id == 1
    finally:
        dialog.close()


def test_status_dialog_only_offers_allowed_logistics_targets(qapp) -> None:
    service = FakePurchases()
    purchase = _row(
        1,
        status=PurchaseStatus.PURCHASED,
        account="Cash USD",
        allowed=(PurchaseStatus.SHIPPED, PurchaseStatus.IN_TRANSIT),
    )
    dialog = PurchaseStatusDialog(service, purchase)
    try:
        status = dialog.findChild(QComboBox, "purchaseTargetStatus")
        assert status is not None
        assert status.count() == 2
        assert status.itemData(0) == PurchaseStatus.SHIPPED

        status.setCurrentIndex(1)
        dialog.findChild(QPushButton, "updatePurchaseStatusButton").click()

        assert dialog.result() == QDialog.DialogCode.Accepted
        assert len(service.status_updates) == 1
        assert (
            service.status_updates[0].status is PurchaseStatus.IN_TRANSIT
        )
    finally:
        dialog.close()


def test_detail_dialog_shows_items_and_costs(qapp) -> None:
    purchase = _row(1)
    detail = PurchaseDetail(
        purchase=purchase,
        items=(
            PurchaseItemDetail(
                item_id=1,
                variant_label="Phone / Black (PHONE-1)",
                quantity=2,
                unit_price=Money("10.00", USD),
                line_total=Money("20.00", USD),
                weight=None,
            ),
        ),
        costs=(
            PurchaseCostDetail(
                cost_id=1,
                cost_type=PurchaseCostType.SHIPPING,
                amount=Money("5.00", USD),
                normalized_amount=Money("5.00", USD),
                allocation_method=AllocationMethod.BY_QUANTITY,
                description="Courier",
            ),
        ),
    )
    dialog = PurchaseDetailDialog(detail)
    try:
        items = dialog.findChild(QTableWidget, "purchaseDetailItemsTable")
        costs = dialog.findChild(QTableWidget, "purchaseDetailCostsTable")
        assert items is not None
        assert costs is not None
        assert items.rowCount() == 1
        assert items.item(0, 0).text() == "Phone / Black (PHONE-1)"
        assert costs.rowCount() == 1
        assert costs.item(0, 4).text() == "Courier"
    finally:
        dialog.close()


def test_page_detail_action_opens_the_detail_dialog(
    qapp, monkeypatch
) -> None:
    purchase = _row(1)
    detail = PurchaseDetail(purchase=purchase, items=(), costs=())
    service = FakePurchases(rows=(purchase,), detail=detail)
    page = PurchasesPage(service, base_currency="USD")
    opened = []

    class FakeDialog:
        def __init__(self, received, *, parent=None) -> None:
            opened.append(received)

        def exec(self):
            return QDialog.DialogCode.Accepted

    monkeypatch.setattr(
        "app.presentation.desktop.views.purchases.PurchaseDetailDialog",
        FakeDialog,
    )
    try:
        table = page.findChild(QTableView, "purchasesTable")
        assert table is not None
        table.selectRow(0)
        page.findChild(QPushButton, "purchaseDetailButton").click()
        assert opened == [detail]
    finally:
        page.close()


def test_main_window_uses_the_real_purchases_screen(qapp) -> None:
    window = build_main_window(
        Settings(base_currency="USD"), purchases=FakePurchases()
    )
    try:
        stack = window.findChild(QStackedWidget, "pageStack")
        assert stack is not None
        purchase_index = [
            item.key for item in NAVIGATION_ITEMS
        ].index("purchases")
        assert isinstance(
            stack.widget(purchase_index), PurchasesPage
        )
    finally:
        window.close()
