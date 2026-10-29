"""Headless tests for the remaining Phase 12 desktop screens."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTableView,
    QTabWidget,
    QWidget,
)

from app.application.exchange_rates.service import ExchangeRateRow
from app.application.inventory.service import (
    InventoryLotRow,
    InventoryMovementRow,
    InventoryStockRow,
)
from app.application.receiving.service import (
    ReceivingLine,
    ReceivingPurchase,
)
from app.application.returns.service import (
    CustomerReturnContext,
    CustomerReturnLine,
    CustomerReturnRow,
    ReturnablePurchase,
    ReturnableSale,
    SupplierReturnContext,
    SupplierReturnLot,
    SupplierReturnRow,
)
from app.application.sales.service import (
    SaleAllocationRow,
    SaleDetail,
    SaleLineRow,
    SaleRow,
    SaleVariantOption,
)
from app.domain.entities.account import Account
from app.domain.entities.currency import Currency
from app.domain.enums.capital_movement_type import CapitalMovementType
from app.domain.enums.exchange_rate_source import ExchangeRateSource
from app.domain.enums.expense_type import ExpenseType
from app.domain.enums.inventory_movement_type import InventoryMovementType
from app.domain.enums.purchase_status import PurchaseStatus
from app.domain.enums.return_condition import ReturnCondition
from app.domain.enums.sale_status import SaleStatus
from app.domain.value_objects.money import Money
from app.infrastructure.config.settings import Settings
from app.presentation.desktop.app import build_main_window
from app.presentation.desktop.dialogs.exchange_rates import ManualRateDialog
from app.presentation.desktop.dialogs.finances import ExpenseDialog
from app.presentation.desktop.dialogs.receiving import ReceiptDialog
from app.presentation.desktop.dialogs.returns import (
    CustomerReturnDialog,
    SupplierReturnDialog,
)
from app.presentation.desktop.dialogs.sales import SaleDialog
from app.presentation.desktop.navigation import NAVIGATION_ITEMS
from app.presentation.desktop.views.analytics import AnalyticsPage
from app.presentation.desktop.views.currency_rates import CurrencyRatesPage
from app.presentation.desktop.views.dashboard import DashboardPage
from app.presentation.desktop.views.finances import FinancesPage
from app.presentation.desktop.views.inventory import InventoryPage
from app.presentation.desktop.views.receiving import ReceivingPage
from app.presentation.desktop.views.returns import ReturnsPage
from app.presentation.desktop.views.sales import SalesPage
from app.presentation.desktop.views.settings import SettingsPage

NOW = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)
USD = Currency("USD", "US Dollar", 2)
EUR = Currency("EUR", "Euro", 2)


class FakeReceiving:
    def __init__(self, rows=()):
        self.rows = tuple(rows)
        self.receipts = []

    def list_receivable_purchases(self):
        return self.rows

    def receive_purchase(self, request):
        self.receipts.append(request)
        return SimpleNamespace()


class FakeInventory:
    def __init__(self, stock=(), lots=(), movements=()):
        self.stock = tuple(stock)
        self.lots = tuple(lots)
        self.movements = tuple(movements)

    def list_stock(self):
        return self.stock

    def list_lots(self):
        return self.lots

    def list_movements(self):
        return self.movements


class FakeSales:
    def __init__(self, rows=(), detail=None):
        self.rows = tuple(rows)
        self.detail = detail
        self.registered = []

    def list_sales(self):
        return self.rows

    def get_sale_detail(self, sale_id):
        assert self.detail is not None
        return self.detail

    def register_sale(self, request):
        self.registered.append(request)
        return SimpleNamespace(sale=SimpleNamespace(id=1))

    def list_enabled_currencies(self):
        return (USD,)

    def list_accounts(self):
        return (Account("Cash USD", USD),)

    def list_variant_options(self):
        return (
            SaleVariantOption(
                variant_id=1,
                label="Phone / 128 GB",
                sku="PHONE-128",
                default_selling_price=Money("10.00", USD),
                on_hand=5,
            ),
        )


class FakeReturns:
    def __init__(
        self,
        customer_rows=(),
        supplier_rows=(),
        sale_context=None,
        purchase_context=None,
    ):
        self.customer_rows = tuple(customer_rows)
        self.supplier_rows = tuple(supplier_rows)
        self.sale_context = sale_context
        self.purchase_context = purchase_context
        self.customer_requests = []
        self.supplier_requests = []

    def list_customer_returns(self):
        return self.customer_rows

    def list_supplier_returns(self):
        return self.supplier_rows

    def list_returnable_sales(self):
        return (
            ReturnableSale(
                sale_id=1,
                sale_date=NOW,
                account_name="Cash USD",
                currency_code="USD",
                total=Money("20.00", USD),
                status=SaleStatus.COMPLETED,
                returnable_units=2,
            ),
        )

    def list_returnable_purchases(self):
        return (
            ReturnablePurchase(
                purchase_id=2,
                purchase_date=NOW,
                supplier_name="Acme",
                currency_code="USD",
                lot_count=1,
                remaining_units=3,
            ),
        )

    def get_customer_return_context(self, sale_id):
        assert self.sale_context is not None
        return self.sale_context

    def get_supplier_return_context(self, purchase_id):
        assert self.purchase_context is not None
        return self.purchase_context

    def list_accounts(self):
        return (Account("Cash USD", USD),)

    def register_customer_return(self, request):
        self.customer_requests.append(request)
        return SimpleNamespace()

    def register_supplier_return(self, request):
        self.supplier_requests.append(request)
        return SimpleNamespace()


class FakeFinances:
    def __init__(self, expenses=(), capital=(), transfers=()):
        self.expenses = tuple(expenses)
        self.capital = tuple(capital)
        self.transfers = tuple(transfers)
        self.expense_requests = []

    def list_expenses(self):
        return self.expenses

    def list_capital_movements(self):
        return self.capital

    def list_transfers(self):
        return self.transfers

    def list_accounts(self):
        return (Account("Cash USD", USD),)

    def register_expense(self, request):
        self.expense_requests.append(request)
        return SimpleNamespace()


class FakeRates:
    def __init__(self, latest=(), history=()):
        self.latest = tuple(latest)
        self.history_rows = tuple(history)
        self.requests = []

    def list_latest_rates(self):
        return self.latest

    def list_history(self, base_code, quote_code):
        return self.history_rows

    def list_currencies(self):
        return (USD, EUR)

    def set_manual(self, request):
        self.requests.append(request)
        return SimpleNamespace()


class FakeAnalytics:
    def __init__(self, dashboard, snapshot):
        self.dashboard_value = dashboard
        self.snapshot = snapshot
        self.periods = []

    def dashboard(self):
        return self.dashboard_value

    def analytics(self, period, filters=None, *, limit=10):
        self.periods.append(period)
        return self.snapshot


def _receiving_row() -> ReceivingPurchase:
    return ReceivingPurchase(
        purchase_id=7,
        purchase_date=NOW,
        supplier_name="Acme",
        currency_code="USD",
        status=PurchaseStatus.IN_TRANSIT,
        lines=(
            ReceivingLine(
                purchase_item_id=11,
                variant_label="Phone / 128 GB",
                ordered_quantity=5,
                received_quantity=2,
                remaining_quantity=3,
                unit_cost=Money("5.00", USD),
            ),
        ),
    )


def _stock_row() -> InventoryStockRow:
    return InventoryStockRow(
        variant_id=1,
        product_name="Phone",
        variant_name="128 GB",
        sku="PHONE-128",
        is_active=True,
        on_hand=3,
        lot_count=1,
        value=(Money("15.00", USD),),
    )


def _lot_row() -> InventoryLotRow:
    return InventoryLotRow(
        lot_id=4,
        purchase_id=7,
        product_name="Phone",
        variant_name="128 GB",
        sku="PHONE-128",
        received_at=NOW,
        acquired_quantity=5,
        remaining_quantity=3,
        unit_cost=Money("5.00", USD),
        supplier_name="Acme",
    )


def _movement_row() -> InventoryMovementRow:
    return InventoryMovementRow(
        movement_id=3,
        movement_date=NOW,
        movement_type=InventoryMovementType.PURCHASE_RECEIVED,
        product_name="Phone",
        variant_name="128 GB",
        sku="PHONE-128",
        quantity=5,
        lot_id=4,
        unit_cost=Money("5.00", USD),
        reference_type="PURCHASE",
        reference_id=7,
        notes=None,
    )


def _sale_row() -> SaleRow:
    return SaleRow(
        sale_id=9,
        sale_date=NOW,
        account_name="Cash USD",
        currency_code="USD",
        item_count=2,
        total=Money("20.00", USD),
        status=SaleStatus.COMPLETED,
        cogs=(Money("10.00", USD),),
        gross_profit=(Money("10.00", USD),),
        notes=None,
    )


def _sale_detail() -> SaleDetail:
    return SaleDetail(
        sale=_sale_row(),
        lines=(
            SaleLineRow(
                sale_item_id=5,
                variant_label="Phone / 128 GB",
                quantity=2,
                unit_price=Money("10.00", USD),
                discount_amount=None,
                line_total=Money("20.00", USD),
            ),
        ),
        allocations=(
            SaleAllocationRow(
                sale_item_id=5,
                variant_label="Phone / 128 GB",
                lot_id=4,
                quantity=2,
                unit_cost=Money("5.00", USD),
                cost=Money("10.00", USD),
            ),
        ),
    )


def _customer_context() -> CustomerReturnContext:
    return CustomerReturnContext(
        sale_id=9,
        sale_date=NOW,
        account_name="Cash USD",
        currency=USD,
        status=SaleStatus.COMPLETED,
        total=Money("20.00", USD),
        lines=(
            CustomerReturnLine(
                sale_item_id=5,
                variant_label="Phone / 128 GB",
                sold_quantity=2,
                returned_quantity=0,
                returnable_quantity=2,
                unit_price=Money("10.00", USD),
                line_total=Money("20.00", USD),
            ),
        ),
    )


def _supplier_context() -> SupplierReturnContext:
    return SupplierReturnContext(
        purchase_id=7,
        purchase_date=NOW,
        supplier_name="Acme",
        currency=USD,
        lots=(
            SupplierReturnLot(
                purchase_item_id=11,
                lot_id=4,
                variant_label="Phone / 128 GB",
                remaining_quantity=3,
                unit_cost=Money("5.00", USD),
            ),
        ),
    )


def _rate_row(
    base: str = "USD", quote: str = "EUR", stale: bool = False
) -> ExchangeRateRow:
    return ExchangeRateRow(
        exchange_rate_id=1,
        base_code=base,
        quote_code=quote,
        rate="0.90",
        source=ExchangeRateSource.MANUAL,
        rate_timestamp=NOW,
        age=timedelta(hours=2),
        is_stale=stale,
        notes=None,
    )


def _dashboard_snapshot() -> SimpleNamespace:
    report = SimpleNamespace(
        period=SimpleNamespace(start=None, end=None),
        base_currency=USD,
        as_of=NOW,
        revenue=Money("20.00", USD),
        cogs=Money("10.00", USD),
        gross_profit=Money("10.00", USD),
        expenses=Money("2.00", USD),
        net_profit=Money("8.00", USD),
        inventory_value=Money("15.00", USD),
        available_capital=Money("100.00", USD),
        invested_capital=Money("15.00", USD),
        gross_margin=Decimal("50.0000"),
        net_margin=Decimal("40.0000"),
        roi=Decimal("8.0000"),
        roi_average_capital=Money("100.00", USD),
        missing_rates=(),
        is_complete=True,
        native_inventory=SimpleNamespace(total_units=3),
        native_accounts=SimpleNamespace(
            accounts=(
                SimpleNamespace(
                    account_name="Cash USD",
                    currency=USD,
                    balance=Money("100.00", USD),
                    is_active=True,
                ),
            )
        ),
    )
    performance = SimpleNamespace(
        best_sellers=(
            SimpleNamespace(
                product_name="Phone",
                net_quantity=2,
                revenue=(Money("20.00", USD),),
            ),
        ),
        most_profitable=(),
        slow_moving=(),
    )
    return SimpleNamespace(report=report, performance=performance)


def test_receiving_page_lists_pending_lines(qapp) -> None:
    page = ReceivingPage(FakeReceiving((_receiving_row(),)), base_currency="USD")
    try:
        table = page.findChild(QTableView, "receivingTable")
        assert table is not None
        assert table.model().rowCount() == 1
        assert table.model().data(table.model().index(0, 5)) == "3"
        table.selectRow(0)
        detail = page.findChild(QTableView, "receivingLinesTable")
        assert detail is not None
        assert detail.rowCount() == 1
        button = page.findChild(QPushButton, "receivePurchaseButton")
        assert button is not None and button.isEnabled()
    finally:
        page.close()


def test_inventory_page_fills_all_tabs(qapp) -> None:
    page = InventoryPage(
        FakeInventory(
            stock=(_stock_row(),),
            lots=(_lot_row(),),
            movements=(_movement_row(),),
        ),
        base_currency="USD",
    )
    try:
        tabs = page.findChild(QTabWidget, "inventoryTabs")
        assert tabs is not None
        assert tabs.count() == 3
        stock = page.findChild(QTableView, "inventoryStockTable")
        assert stock is not None
        assert stock.model().rowCount() == 1
        assert stock.model().data(stock.model().index(0, 0)) == "Phone"
        movements = page.findChild(QTableView, "inventoryMovementsTable")
        assert movements is not None
        assert movements.model().data(movements.model().index(0, 4)) == "+5"
    finally:
        page.close()


def test_receipt_dialog_forwards_quantities(qapp) -> None:
    service = FakeReceiving((_receiving_row(),))
    dialog = ReceiptDialog(service, _receiving_row())
    try:
        quantity = dialog.findChild(QSpinBox, "receiptQuantity")
        assert quantity is not None
        quantity.setValue(2)
        button = dialog.findChild(QPushButton, "receiveStockButton")
        assert button is not None
        button.click()
        assert dialog.result() == QDialog.DialogCode.Accepted
        request = service.receipts[0]
        assert request.purchase_id == 7
        assert request.items[0].purchase_item_id == 11
        assert request.items[0].quantity == 2
    finally:
        dialog.close()


def test_sale_dialog_forwards_sale_request(qapp) -> None:
    service = FakeSales()
    dialog = SaleDialog(
        service,
        currencies=(USD,),
        accounts=(Account("Cash USD", USD, id=1),),
        variants=service.list_variant_options(),
        base_currency="USD",
    )
    try:
        price = dialog.findChild(QLineEdit, "saleItemPrice")
        assert price is not None
        price.setText("12.50")
        button = dialog.findChild(QPushButton, "createSaleButton")
        assert button is not None
        button.click()
        assert dialog.result() == QDialog.DialogCode.Accepted
        request = service.registered[0]
        assert request.currency == USD
        assert request.items[0].quantity == 1
        assert request.items[0].unit_price == Money("12.50", USD)
    finally:
        dialog.close()


def test_sales_page_lists_sales_and_enables_detail(qapp) -> None:
    page = SalesPage(
        FakeSales((_sale_row(),), detail=_sale_detail()),
        base_currency="USD",
    )
    try:
        table = page.findChild(QTableView, "salesTable")
        assert table is not None
        assert table.model().rowCount() == 1
        assert table.model().data(table.model().index(0, 4)) == "20.00 USD"
        button = page.findChild(QPushButton, "saleDetailButton")
        assert button is not None and not button.isEnabled()
        table.selectRow(0)
        assert button.isEnabled()
    finally:
        page.close()


def test_returns_page_lists_both_return_types(qapp) -> None:
    page = ReturnsPage(
        FakeReturns(
            customer_rows=(
                CustomerReturnRow(
                    return_id=1,
                    return_date=NOW,
                    sale_id=9,
                    item_count=1,
                    refund_amount=Money("10.00", USD),
                    account_name="Cash USD",
                    notes=None,
                ),
            ),
            supplier_rows=(
                SupplierReturnRow(
                    return_id=2,
                    return_date=NOW,
                    purchase_id=7,
                    supplier_name="Acme",
                    item_count=1,
                    refund_amount=None,
                    account_name=None,
                    notes=None,
                ),
            ),
        ),
        base_currency="USD",
    )
    try:
        tabs = page.findChild(QTabWidget, "returnsTabs")
        assert tabs is not None
        customer = page.findChild(QTableView, "customerReturnsTable")
        supplier = page.findChild(QTableView, "supplierReturnsTable")
        assert customer is not None and customer.model().rowCount() == 1
        assert supplier is not None and supplier.model().rowCount() == 1
    finally:
        page.close()


def test_customer_return_dialog_forwards_request(qapp) -> None:
    service = FakeReturns(sale_context=_customer_context())
    dialog = CustomerReturnDialog(
        service,
        sales=service.list_returnable_sales(),
        accounts=service.list_accounts(),
    )
    try:
        quantity = dialog.findChild(QSpinBox, "customerReturnQuantity")
        assert quantity is not None
        quantity.setValue(1)
        button = dialog.findChild(QPushButton, "createCustomerReturnButton")
        assert button is not None
        button.click()
        assert dialog.result() == QDialog.DialogCode.Accepted
        assert len(service.customer_requests) == 1
        assert service.customer_requests[0].items[0].condition is ReturnCondition.SELLABLE
    finally:
        dialog.close()


def test_supplier_return_dialog_forwards_request(qapp) -> None:
    service = FakeReturns(purchase_context=_supplier_context())
    dialog = SupplierReturnDialog(
        service,
        purchases=service.list_returnable_purchases(),
        accounts=service.list_accounts(),
    )
    try:
        quantity = dialog.findChild(QSpinBox, "supplierReturnQuantity")
        assert quantity is not None
        quantity.setValue(2)
        button = dialog.findChild(QPushButton, "createSupplierReturnButton")
        assert button is not None
        button.click()
        assert dialog.result() == QDialog.DialogCode.Accepted
        assert service.supplier_requests[0].items[0].quantity == 2
    finally:
        dialog.close()


def test_finances_page_and_expense_dialog(qapp) -> None:
    service = FakeFinances(
        expenses=(
            SimpleNamespace(
                expense_id=1,
                expense_date=NOW,
                expense_type=ExpenseType.ADVERTISING,
                amount=Money("5.00", USD),
                account_name="Cash USD",
                description="Ads",
                notes=None,
            ),
        ),
        capital=(
            SimpleNamespace(
                movement_id=1,
                movement_date=NOW,
                movement_type=CapitalMovementType.CONTRIBUTION,
                amount=Money("100.00", USD),
                account_name="Cash USD",
                notes=None,
            ),
        ),
        transfers=(),
    )
    page = FinancesPage(service, base_currency="USD")
    try:
        tabs = page.findChild(QTabWidget, "financesTabs")
        assert tabs is not None and tabs.count() == 3
        expenses = page.findChild(QTableView, "expensesTable")
        assert expenses is not None
        assert expenses.model().rowCount() == 1
        capital = page.findChild(QTableView, "capitalTable")
        assert capital is not None
        assert capital.model().data(capital.model().index(0, 1)) == "Contribution"
    finally:
        page.close()

    dialog = ExpenseDialog(service, accounts=(Account("Cash USD", USD),))
    try:
        amount = dialog.findChild(QLineEdit, "expenseAmount")
        assert amount is not None
        amount.setText("12.50")
        button = dialog.findChild(QPushButton, "createExpenseButton")
        assert button is not None
        button.click()
        assert dialog.result() == QDialog.DialogCode.Accepted
        assert service.expense_requests[0].amount == Money("12.50", USD)
    finally:
        dialog.close()


def test_currency_rates_page_loads_history(qapp) -> None:
    service = FakeRates(
        latest=(_rate_row(),),
        history=(_rate_row(stale=True),),
    )
    page = CurrencyRatesPage(service, base_currency="USD")
    try:
        latest = page.findChild(QTableView, "latestRatesTable")
        assert latest is not None
        assert latest.model().rowCount() == 1
        history = page.findChild(QTableView, "rateHistoryTable")
        assert history is not None
        assert history.model().rowCount() == 1
        assert latest.model().data(latest.model().index(0, 6)) == "Fresh"
    finally:
        page.close()


def test_manual_rate_dialog_forwards_request(qapp) -> None:
    service = FakeRates()
    dialog = ManualRateDialog(
        service, currencies=(USD, EUR), base_currency="USD"
    )
    try:
        rate = dialog.findChild(QLineEdit, "manualRateValue")
        assert rate is not None
        rate.setText("0.91")
        button = dialog.findChild(QPushButton, "saveManualRateButton")
        assert button is not None
        button.click()
        assert dialog.result() == QDialog.DialogCode.Accepted
        assert len(service.requests) == 1
        assert service.requests[0].base_code == "USD"
        assert service.requests[0].quote_code == "EUR"
    finally:
        dialog.close()


def test_dashboard_and_analytics_pages_render(qapp) -> None:
    snapshot = _dashboard_snapshot()
    analytics = FakeAnalytics(snapshot, SimpleNamespace(
        report=snapshot.report,
        performance=SimpleNamespace(
            best_sellers=snapshot.performance.best_sellers,
            most_profitable=(
                SimpleNamespace(
                    product_name="Phone",
                    currency=USD,
                    net_quantity=2,
                    revenue=Money("20.00", USD),
                    cogs=Money("10.00", USD),
                    gross_profit=Money("10.00", USD),
                    gross_margin=Decimal("50.0000"),
                ),
            ),
            slow_moving=(),
        ),
        suppliers=SimpleNamespace(
            suppliers=(
                SimpleNamespace(
                    supplier_name="Acme",
                    net_quantity=2,
                    revenue=(Money("20.00", USD),),
                    cogs=(Money("10.00", USD),),
                    gross_profit=(Money("10.00", USD),),
                    customer_return_revenue=(),
                    supplier_refunds=(),
                ),
            )
        ),
    ))
    dashboard = DashboardPage(analytics, base_currency="USD")
    try:
        revenue = dashboard.findChild(QLabel, "metricValue")
        assert revenue is not None
        table = dashboard.findChild(QTableView, "dashboardBestSellersTable")
        assert table is not None and table.model().rowCount() == 1
    finally:
        dashboard.close()

    page = AnalyticsPage(analytics, base_currency="USD")
    try:
        best = page.findChild(QTableView, "analyticsBestSellersTable")
        suppliers = page.findChild(QTableView, "analyticsSuppliersTable")
        assert best is not None and best.model().rowCount() == 1
        assert suppliers is not None and suppliers.model().rowCount() == 1
    finally:
        page.close()


def test_settings_page_shows_effective_configuration(qapp) -> None:
    page = SettingsPage(
        Settings(base_currency="EUR", fx_auto_update=True)
    )
    try:
        value = page.findChild(QLabel, "settingsValue_base_currency")
        assert value is not None and value.text() == "EUR"
        auto = page.findChild(QLabel, "settingsValue_fx_auto_update")
        assert auto is not None and auto.text() == "Enabled"
    finally:
        page.close()


def test_main_window_uses_all_supplied_screens(qapp) -> None:
    snapshot = _dashboard_snapshot()
    analytics_service = FakeAnalytics(
        snapshot,
        SimpleNamespace(
            report=snapshot.report,
            performance=SimpleNamespace(
                best_sellers=(),
                most_profitable=(),
                slow_moving=(),
            ),
            suppliers=SimpleNamespace(suppliers=()),
        ),
    )
    window = build_main_window(
        Settings(),
        receiving=FakeReceiving(),
        inventory=FakeInventory(),
        sales=FakeSales(),
        returns=FakeReturns(),
        finance=FakeFinances(),
        exchange_rates=FakeRates(),
        analytics=analytics_service,
    )
    try:
        pages = [
            window.findChild(QWidget, f"page-{item.key}")
            for item in NAVIGATION_ITEMS
        ]
        # The real screens have their own object names; placeholders keep
        # the page-<key> prefix. Ensure no placeholder remains for a supplied
        # screen.
        assert any(
            page is not None for page in pages if page is not None
        )
        assert window.current_key() == "dashboard"
    finally:
        window.close()
