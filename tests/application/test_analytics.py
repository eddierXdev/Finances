"""Analytics use cases against a migrated SQLite database."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.application.analytics import (
    AnalyticsFilters,
    AnalyticsPeriod,
    GetAccountBalances,
    GetBusinessSummary,
    GetConsolidatedReport,
    GetInventoryValue,
    GetProductPerformance,
    GetSupplierProfitability,
)
from app.application.exchange_rates import (
    SetManualExchangeRate,
    SetManualExchangeRateRequest,
)
from app.application.finances import (
    AddCapital,
    CapitalMovementRequest,
    RegisterExpense,
    RegisterExpenseRequest,
)
from app.application.inventory import (
    ReceivePurchase,
    ReceivePurchaseRequest,
    ReceiptItemRequest,
)
from app.application.purchases import (
    PurchaseItemRequest,
    RegisterPurchase,
    RegisterPurchaseRequest,
    UpdatePurchaseStatus,
    UpdatePurchaseStatusRequest,
)
from app.application.returns import (
    CustomerReturnItemRequest,
    RegisterCustomerReturn,
    RegisterCustomerReturnRequest,
    RegisterSupplierReturn,
    RegisterSupplierReturnRequest,
    SupplierReturnItemRequest,
)
from app.application.sales import (
    RegisterSale,
    RegisterSaleRequest,
    SaleItemRequest,
)
from app.application.suppliers import CreateSupplier, CreateSupplierRequest
from app.domain.entities.account import Account
from app.domain.entities.category import Category
from app.domain.entities.currency import Currency
from app.domain.entities.product import Product
from app.domain.entities.product_variant import ProductVariant
from app.domain.enums.expense_type import ExpenseType
from app.domain.enums.purchase_status import PurchaseStatus
from app.domain.enums.return_condition import ReturnCondition
from app.domain.value_objects.money import Money
from app.infrastructure.database.repositories import (
    SqlAlchemyAccountRepository,
    SqlAlchemyAnalyticsRepository,
    SqlAlchemyCapitalMovementRepository,
    SqlAlchemyCategoryRepository,
    SqlAlchemyCurrencyRepository,
    SqlAlchemyCustomerRepository,
    SqlAlchemyCustomerReturnItemRepository,
    SqlAlchemyCustomerReturnRepository,
    SqlAlchemyExchangeRateRepository,
    SqlAlchemyExpenseRepository,
    SqlAlchemyFinancialTransactionRepository,
    SqlAlchemyInventoryLotRepository,
    SqlAlchemyInventoryMovementRepository,
    SqlAlchemyProductRepository,
    SqlAlchemyProductVariantRepository,
    SqlAlchemyPurchaseCostAllocationRepository,
    SqlAlchemyPurchaseCostRepository,
    SqlAlchemyPurchaseItemRepository,
    SqlAlchemyPurchaseRepository,
    SqlAlchemyReturnLotAllocationRepository,
    SqlAlchemySaleItemLotAllocationRepository,
    SqlAlchemySaleItemRepository,
    SqlAlchemySaleRepository,
    SqlAlchemySupplierRepository,
    SqlAlchemySupplierReturnItemRepository,
    SqlAlchemySupplierReturnRepository,
)

NOW = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)
EARLIER = NOW - timedelta(hours=1)
LATER = NOW + timedelta(days=1)
LATER_STILL = NOW + timedelta(days=2)
PERIOD = AnalyticsPeriod(start=EARLIER, end=LATER_STILL + timedelta(hours=1))


def _currency(db_session, code: str = "USD") -> Currency:
    currency = SqlAlchemyCurrencyRepository(db_session).get_by_code(code)
    assert currency is not None
    return currency


def _account(
    db_session,
    code: str = "USD",
    *,
    name: str | None = None,
    active: bool = True,
) -> Account:
    return SqlAlchemyAccountRepository(db_session).add(
        Account(
            name=name or f"Cash {code}",
            currency=_currency(db_session, code),
            is_active=active,
        )
    )


def _variant(
    db_session,
    name: str = "Phone",
    *,
    category_id: int | None = None,
) -> ProductVariant:
    product = SqlAlchemyProductRepository(db_session).add(
        Product(name=name, category_id=category_id)
    )
    return SqlAlchemyProductVariantRepository(db_session).add(
        ProductVariant(product_id=product.id, variant_name=name)
    )


def _supplier(db_session, name: str = "Acme"):
    return CreateSupplier(
        SqlAlchemySupplierRepository(db_session)
    ).execute(CreateSupplierRequest(name=name))


def _purchase(
    db_session,
    *,
    variant_id: int,
    quantity: int,
    price: str,
    supplier_id: int | None = None,
    received_at: datetime = NOW,
    currency_code: str = "USD",
):
    currency = _currency(db_session, currency_code)
    purchase_account = _account(
        db_session,
        currency_code,
        name=f"Purchases {currency_code}",
    )
    purchases = SqlAlchemyPurchaseRepository(db_session)
    registered = RegisterPurchase(
        accounts=SqlAlchemyAccountRepository(db_session),
        purchases=purchases,
        items=SqlAlchemyPurchaseItemRepository(db_session),
        costs=SqlAlchemyPurchaseCostRepository(db_session),
        allocations=SqlAlchemyPurchaseCostAllocationRepository(db_session),
        exchange_rates=SqlAlchemyExchangeRateRepository(db_session),
        transactions=SqlAlchemyFinancialTransactionRepository(db_session),
    ).execute(
        RegisterPurchaseRequest(
            currency=currency,
            purchase_date=received_at,
            supplier_id=supplier_id,
            items=(
                PurchaseItemRequest(
                    variant_id=variant_id,
                    quantity=quantity,
                    unit_price=Money(price, currency),
                ),
            ),
            account_id=purchase_account.id,
        )
    )
    item = registered.items[0]
    assert item.id is not None

    status_service = UpdatePurchaseStatus(purchases)
    for target in (PurchaseStatus.SHIPPED, PurchaseStatus.IN_TRANSIT):
        status_service.execute(
            UpdatePurchaseStatusRequest(registered.purchase.id, target)
        )

    ReceivePurchase(
        purchases=purchases,
        items=SqlAlchemyPurchaseItemRepository(db_session),
        allocations=SqlAlchemyPurchaseCostAllocationRepository(db_session),
        lots=SqlAlchemyInventoryLotRepository(db_session),
        movements=SqlAlchemyInventoryMovementRepository(db_session),
    ).execute(
        ReceivePurchaseRequest(
            purchase_id=registered.purchase.id,
            items=(ReceiptItemRequest(item.id, quantity),),
            received_at=received_at,
        )
    )
    return registered, purchase_account


def _sale_service(db_session) -> RegisterSale:
    return RegisterSale(
        accounts=SqlAlchemyAccountRepository(db_session),
        customers=SqlAlchemyCustomerRepository(db_session),
        variants=SqlAlchemyProductVariantRepository(db_session),
        sales=SqlAlchemySaleRepository(db_session),
        items=SqlAlchemySaleItemRepository(db_session),
        allocations=SqlAlchemySaleItemLotAllocationRepository(db_session),
        lots=SqlAlchemyInventoryLotRepository(db_session),
        movements=SqlAlchemyInventoryMovementRepository(db_session),
        transactions=SqlAlchemyFinancialTransactionRepository(db_session),
    )


def _item(
    variant_id: int,
    quantity: int,
    price: str,
    currency: Currency,
    *,
    discount: str | None = None,
) -> SaleItemRequest:
    return SaleItemRequest(
        variant_id=variant_id,
        quantity=quantity,
        unit_price=Money(price, currency),
        discount_amount=(
            Money(discount, currency) if discount is not None else None
        ),
    )


def _sell(
    db_session,
    account: Account,
    items,
    *,
    sale_date: datetime = NOW,
    **kwargs,
):
    return _sale_service(db_session).execute(
        RegisterSaleRequest(
            account_id=account.id,
            currency=account.currency,
            sale_date=sale_date,
            items=tuple(items),
            **kwargs,
        )
    )


def _customer_return(
    db_session,
    sale,
    items,
    *,
    account: Account,
    refund: Money,
    return_date: datetime = LATER,
):
    return RegisterCustomerReturn(
        accounts=SqlAlchemyAccountRepository(db_session),
        sales=SqlAlchemySaleRepository(db_session),
        sale_items=SqlAlchemySaleItemRepository(db_session),
        sale_allocations=SqlAlchemySaleItemLotAllocationRepository(db_session),
        customer_returns=SqlAlchemyCustomerReturnRepository(db_session),
        return_items=SqlAlchemyCustomerReturnItemRepository(db_session),
        return_allocations=SqlAlchemyReturnLotAllocationRepository(db_session),
        lots=SqlAlchemyInventoryLotRepository(db_session),
        movements=SqlAlchemyInventoryMovementRepository(db_session),
        transactions=SqlAlchemyFinancialTransactionRepository(db_session),
    ).execute(
        RegisterCustomerReturnRequest(
            sale_id=sale.id,
            return_date=return_date,
            items=tuple(items),
            account_id=account.id,
            refund_amount=refund,
        )
    )


def _supplier_return(
    db_session,
    purchase,
    items,
    *,
    account: Account,
    refund: Money,
    return_date: datetime = LATER,
):
    return RegisterSupplierReturn(
        accounts=SqlAlchemyAccountRepository(db_session),
        purchases=SqlAlchemyPurchaseRepository(db_session),
        purchase_items=SqlAlchemyPurchaseItemRepository(db_session),
        lots=SqlAlchemyInventoryLotRepository(db_session),
        supplier_returns=SqlAlchemySupplierReturnRepository(db_session),
        return_items=SqlAlchemySupplierReturnItemRepository(db_session),
        movements=SqlAlchemyInventoryMovementRepository(db_session),
        transactions=SqlAlchemyFinancialTransactionRepository(db_session),
    ).execute(
        RegisterSupplierReturnRequest(
            purchase_id=purchase.id,
            return_date=return_date,
            items=tuple(items),
            account_id=account.id,
            refund_amount=refund,
        )
    )


def _add_capital(db_session, account: Account, amount: str) -> None:
    AddCapital(
        SqlAlchemyAccountRepository(db_session),
        SqlAlchemyCapitalMovementRepository(db_session),
        SqlAlchemyFinancialTransactionRepository(db_session),
    ).execute(
        CapitalMovementRequest(
            account_id=account.id,
            amount=Money(amount, account.currency),
            movement_date=EARLIER,
        )
    )


def _expense(db_session, account: Account, amount: str) -> None:
    RegisterExpense(
        accounts=SqlAlchemyAccountRepository(db_session),
        expenses=SqlAlchemyExpenseRepository(db_session),
        transactions=SqlAlchemyFinancialTransactionRepository(db_session),
    ).execute(
        RegisterExpenseRequest(
            account_id=account.id,
            expense_type=ExpenseType.ADVERTISING,
            amount=Money(amount, account.currency),
            expense_date=NOW,
        )
    )


def _analytics(db_session) -> SqlAlchemyAnalyticsRepository:
    return SqlAlchemyAnalyticsRepository(db_session)


def _summary(db_session) -> GetBusinessSummary:
    return GetBusinessSummary(_analytics(db_session))


def _products(db_session) -> GetProductPerformance:
    return GetProductPerformance(
        _analytics(db_session), slow_moving_days=30
    )


def _suppliers(db_session) -> GetSupplierProfitability:
    return GetSupplierProfitability(_analytics(db_session))


def _inventory(db_session) -> GetInventoryValue:
    return GetInventoryValue(_analytics(db_session))


def _accounts(db_session) -> GetAccountBalances:
    return GetAccountBalances(
        SqlAlchemyAccountRepository(db_session),
        SqlAlchemyFinancialTransactionRepository(db_session),
    )


def _consolidated(db_session, *, base_currency: str = "USD"):
    return GetConsolidatedReport(
        _summary(db_session),
        _inventory(db_session),
        _accounts(db_session),
        SqlAlchemyCurrencyRepository(db_session),
        SqlAlchemyExchangeRateRepository(db_session),
        SqlAlchemyCapitalMovementRepository(db_session),
        base_currency=base_currency,
    )


def _set_rate(
    db_session,
    base: str,
    quote: str,
    rate: str,
    *,
    timestamp: datetime = NOW,
) -> None:
    SetManualExchangeRate(
        SqlAlchemyCurrencyRepository(db_session),
        SqlAlchemyExchangeRateRepository(db_session),
    ).execute(
        SetManualExchangeRateRequest(
            base_code=base,
            quote_code=quote,
            rate=Decimal(rate),
            rate_timestamp=timestamp,
        )
    )


def _scenario(db_session):
    supplier = _supplier(db_session)
    phone = _variant(db_session, "Phone")
    case = _variant(db_session, "Case")

    phone_purchase, _ = _purchase(
        db_session,
        variant_id=phone.id,
        quantity=10,
        price="5.00",
        supplier_id=supplier.id,
    )
    case_purchase, _ = _purchase(
        db_session,
        variant_id=case.id,
        quantity=5,
        price="4.00",
        supplier_id=supplier.id,
    )

    sale_account = _account(db_session, "USD", name="Sales")
    _add_capital(db_session, sale_account, "1000.00")

    sale = _sell(
        db_session,
        sale_account,
        [_item(phone.id, 4, "12.00", sale_account.currency, discount="2.00")],
    )

    _customer_return(
        db_session,
        sale.sale,
        [
            CustomerReturnItemRequest(
                sale_item_id=sale.items[0].id,
                quantity=1,
                condition=ReturnCondition.SELLABLE,
            )
        ],
        account=sale_account,
        refund=Money("10.00", sale_account.currency),
    )

    expense_account = _account(db_session, "USD", name="Expenses")
    _add_capital(db_session, expense_account, "100.00")
    _expense(db_session, expense_account, "5.00")

    refund_account = _account(db_session, "USD", name="Supplier refunds")
    _add_capital(db_session, refund_account, "100.00")
    case_lot = SqlAlchemyInventoryLotRepository(db_session).list_for_purchase(
        case_purchase.purchase.id
    )[0]
    _supplier_return(
        db_session,
        case_purchase.purchase,
        [
            SupplierReturnItemRequest(
                purchase_item_id=case_purchase.items[0].id,
                inventory_lot_id=case_lot.id,
                quantity=2,
            )
        ],
        account=refund_account,
        refund=Money("8.00", refund_account.currency),
    )

    return {
        "supplier": supplier,
        "phone": phone,
        "case": case,
        "sale": sale,
        "sale_account": sale_account,
        "expense_account": expense_account,
        "refund_account": refund_account,
    }


def test_business_summary_accounts_for_discounts_returns_and_expenses(
    db_session,
) -> None:
    _scenario(db_session)

    summary = _summary(db_session).execute(PERIOD)

    assert summary.revenue == (Money("34.50", _currency(db_session)),)
    assert summary.cogs == (Money("15.00", _currency(db_session)),)
    assert summary.gross_profit == (
        Money("19.50", _currency(db_session)),
    )
    assert summary.expenses == (Money("5.00", _currency(db_session)),)
    assert summary.net_profit == (Money("14.50", _currency(db_session)),)
    assert summary.customer_refunds == (
        Money("10.00", _currency(db_session)),
    )
    assert summary.supplier_refunds == (
        Money("8.00", _currency(db_session)),
    )
    assert summary.supplier_return_cost == (
        Money("8.00", _currency(db_session)),
    )
    assert summary.units_sold == 3
    assert summary.sale_count == 1
    assert summary.return_count == 1
    assert summary.cross_currency_sale_count == 0
    assert summary.margins[0].gross_margin == Decimal("56.5217")
    assert summary.margins[0].net_margin == Decimal("42.0290")


def test_product_performance_ranks_best_sellers_profit_and_slow_stock(
    db_session,
) -> None:
    scenario = _scenario(db_session)

    report = _products(db_session).execute(PERIOD)

    assert len(report.best_sellers) == 1
    best = report.best_sellers[0]
    assert best.product_id == scenario["phone"].product_id
    assert best.net_quantity == 3
    assert best.revenue == (Money("34.50", _currency(db_session)),)

    assert len(report.most_profitable) == 1
    profitable = report.most_profitable[0]
    assert profitable.product_id == scenario["phone"].product_id
    assert profitable.revenue == Money("34.50", _currency(db_session))
    assert profitable.cogs == Money("15.00", _currency(db_session))
    assert profitable.gross_profit == Money("19.50", _currency(db_session))
    assert profitable.gross_margin == Decimal("56.5217")

    assert len(report.slow_moving) == 1
    slow = report.slow_moving[0]
    assert slow.product_id == scenario["case"].product_id
    assert slow.remaining_quantity == 3
    assert slow.inventory_value == (Money("12.00", _currency(db_session)),)
    assert slow.last_sale_date is None
    assert slow.days_since_last_sale is None


def test_product_filter_uses_full_sale_discount_denominator(db_session) -> None:
    phone = _variant(db_session, "Phone")
    case = _variant(db_session, "Case")
    _purchase(db_session, variant_id=phone.id, quantity=2, price="5.00")
    _purchase(db_session, variant_id=case.id, quantity=1, price="10.00")
    sale_account = _account(db_session, "USD", name="Sales")

    _sell(
        db_session,
        sale_account,
        [
            _item(phone.id, 2, "10.00", sale_account.currency),
            _item(case.id, 1, "20.00", sale_account.currency),
        ],
        discount_amount=Money("4.00", sale_account.currency),
    )

    summary = _summary(db_session).execute(
        PERIOD, AnalyticsFilters(product_id=phone.product_id)
    )
    products = _products(db_session).execute(
        PERIOD, AnalyticsFilters(product_id=phone.product_id)
    )

    assert summary.revenue == (Money("18.00", _currency(db_session)),)
    assert summary.cogs == (Money("10.00", _currency(db_session)),)
    assert summary.gross_profit == (
        Money("8.00", _currency(db_session)),
    )
    assert products.best_sellers[0].net_quantity == 2
    assert products.best_sellers[0].revenue == (
        Money("18.00", _currency(db_session)),
    )
    assert products.most_profitable[0].gross_profit == Money(
        "8.00", _currency(db_session)
    )


def test_supplier_and_category_filters_scope_sales(db_session) -> None:
    categories = SqlAlchemyCategoryRepository(db_session)
    phone_category = categories.add(Category(name="Phones"))
    case_category = categories.add(Category(name="Cases"))
    acme = _supplier(db_session, "Acme")
    beta = _supplier(db_session, "Beta")
    phone = _variant(
        db_session, "Phone", category_id=phone_category.id
    )
    case = _variant(db_session, "Case", category_id=case_category.id)
    _purchase(
        db_session,
        variant_id=phone.id,
        quantity=2,
        price="5.00",
        supplier_id=acme.id,
    )
    _purchase(
        db_session,
        variant_id=case.id,
        quantity=1,
        price="10.00",
        supplier_id=beta.id,
    )
    sale_account = _account(db_session, "USD", name="Sales")
    _sell(
        db_session,
        sale_account,
        [
            _item(phone.id, 2, "10.00", sale_account.currency),
            _item(case.id, 1, "20.00", sale_account.currency),
        ],
    )

    by_supplier = _summary(db_session).execute(
        PERIOD, AnalyticsFilters(supplier_id=acme.id)
    )
    by_category = _summary(db_session).execute(
        PERIOD, AnalyticsFilters(category_id=case_category.id)
    )

    assert by_supplier.revenue == (Money("20.00", _currency(db_session)),)
    assert by_supplier.cogs == (Money("10.00", _currency(db_session)),)
    assert by_category.revenue == (Money("20.00", _currency(db_session)),)
    assert by_category.cogs == (Money("10.00", _currency(db_session)),)


def test_supplier_profitability_attributes_sales_returns_and_refunds(
    db_session,
) -> None:
    scenario = _scenario(db_session)

    report = _suppliers(db_session).execute(PERIOD)

    assert len(report.suppliers) == 1
    supplier = report.suppliers[0]
    assert supplier.supplier_id == scenario["supplier"].id
    assert supplier.supplier_name == "Acme"
    assert supplier.net_quantity == 3
    assert supplier.revenue == (Money("34.50", _currency(db_session)),)
    assert supplier.cogs == (Money("15.00", _currency(db_session)),)
    assert supplier.gross_profit == (
        Money("19.50", _currency(db_session)),
    )
    assert supplier.customer_return_revenue == (
        Money("11.50", _currency(db_session)),
    )
    assert supplier.customer_return_cogs == (
        Money("5.00", _currency(db_session)),
    )
    assert supplier.supplier_refunds == (
        Money("8.00", _currency(db_session)),
    )
    assert supplier.supplier_return_cost == (
        Money("8.00", _currency(db_session)),
    )
    assert supplier.cross_currency_sale_count == 0


def test_account_balances_and_inventory_value_are_native(db_session) -> None:
    scenario = _scenario(db_session)

    balances = _accounts(db_session).execute(
        PERIOD.end,
        AnalyticsFilters(account_id=scenario["sale_account"].id),
    )
    inventory = _inventory(db_session).execute(PERIOD.end)

    assert balances.accounts[0].balance == Money(
        "1036.00", _currency(db_session)
    )
    assert balances.totals == (Money("1036.00", _currency(db_session)),)
    assert inventory.inventory_value == (
        Money("47.00", _currency(db_session)),
    )
    assert inventory.total_units == 10


def test_period_filters_sales_and_returns_by_their_own_dates(
    db_session,
) -> None:
    _scenario(db_session)

    sale_only = _summary(db_session).execute(
        AnalyticsPeriod(start=NOW, end=NOW)
    )
    return_only = _summary(db_session).execute(
        AnalyticsPeriod(start=LATER, end=LATER)
    )

    assert sale_only.revenue == (Money("46.00", _currency(db_session)),)
    assert sale_only.cogs == (Money("20.00", _currency(db_session)),)
    assert sale_only.gross_profit == (
        Money("26.00", _currency(db_session)),
    )
    assert sale_only.customer_refunds == ()
    assert sale_only.units_sold == 4
    assert sale_only.return_count == 0

    assert return_only.revenue == (Money("-11.50", _currency(db_session)),)
    assert return_only.cogs == (Money("-5.00", _currency(db_session)),)
    assert return_only.gross_profit == (
        Money("-6.50", _currency(db_session)),
    )
    assert return_only.customer_refunds == (
        Money("10.00", _currency(db_session)),
    )
    assert return_only.supplier_refunds == (
        Money("8.00", _currency(db_session)),
    )
    assert return_only.units_sold == -1
    assert return_only.sale_count == 0
    assert return_only.return_count == 1


def test_cross_currency_sale_is_excluded_from_native_profit_and_consolidated(
    db_session,
) -> None:
    variant = _variant(db_session, "Phone")
    _purchase(
        db_session,
        variant_id=variant.id,
        quantity=1,
        price="5.00",
        currency_code="EUR",
    )
    sale_account = _account(db_session, "USD", name="Sales")

    _sell(
        db_session,
        sale_account,
        [_item(variant.id, 1, "12.00", sale_account.currency)],
    )

    summary = _summary(db_session).execute(PERIOD)
    products = _products(db_session).execute(PERIOD)
    suppliers = _suppliers(db_session).execute(PERIOD)

    assert summary.revenue == (Money("12.00", _currency(db_session)),)
    assert summary.cogs == (Money("5.00", _currency(db_session, "EUR")),)
    assert summary.gross_profit == ()
    assert summary.units_sold == 1
    assert summary.cross_currency_sale_count == 1
    assert summary.margins[0].gross_margin is None
    assert summary.margins[0].net_margin is None
    assert products.most_profitable == ()
    assert products.best_sellers[0].net_quantity == 1
    assert suppliers.suppliers[0].gross_profit == ()
    assert suppliers.suppliers[0].cross_currency_sale_count == 1

    _set_rate(db_session, "USD", "EUR", "0.90")
    report = _consolidated(db_session).execute(PERIOD)

    assert report.revenue == Money("12.00", _currency(db_session))
    assert report.cogs == Money("5.56", _currency(db_session))
    assert report.gross_profit == Money("6.44", _currency(db_session))
    assert report.is_complete is True


def test_consolidated_report_converts_eur_and_calculates_roi(
    db_session,
) -> None:
    _scenario(db_session)
    eur_account = _account(db_session, "EUR", name="EUR cash")
    _add_capital(db_session, eur_account, "90.00")
    _set_rate(db_session, "USD", "EUR", "0.90")

    report = _consolidated(db_session).execute(PERIOD)

    assert report.base_currency.code == "USD"
    assert report.revenue == Money("34.50", _currency(db_session))
    assert report.cogs == Money("15.00", _currency(db_session))
    assert report.gross_profit == Money("19.50", _currency(db_session))
    assert report.expenses == Money("5.00", _currency(db_session))
    assert report.net_profit == Money("14.50", _currency(db_session))
    assert report.inventory_value == Money("47.00", _currency(db_session))
    assert report.available_capital == Money(
        "1269.00", _currency(db_session)
    )
    assert report.invested_capital == Money("47.00", _currency(db_session))
    assert report.roi_average_capital == Money(
        "1300.00", _currency(db_session)
    )
    assert report.roi == Decimal("1.1154")
    assert report.missing_rates == ()
    assert report.is_complete is True
    assert report.native_accounts.totals == (
        Money("90.00", _currency(db_session, "EUR")),
        Money("1169.00", _currency(db_session)),
    )


def test_zero_balances_do_not_require_an_exchange_rate(db_session) -> None:
    _account(db_session, "CUP", name="Empty CUP")

    report = _consolidated(db_session).execute(PERIOD)

    assert report.is_complete is True
    assert report.missing_rates == ()
    assert report.available_capital == Money("0.00", _currency(db_session))


def test_consolidated_report_reports_missing_rates_without_inventing_fx(
    db_session,
) -> None:
    cup_account = _account(db_session, "CUP", name="CUP cash")
    _add_capital(db_session, cup_account, "50.00")

    report = _consolidated(db_session).execute(PERIOD)

    assert report.is_complete is False
    assert report.missing_rates[0].base_code == "USD"
    assert report.missing_rates[0].quote_code == "CUP"
    assert report.available_capital == Money("0.00", _currency(db_session))
    assert report.roi is None
    assert report.native_accounts.totals == (
        Money("50.00", _currency(db_session, "CUP")),
    )
