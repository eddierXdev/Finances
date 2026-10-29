"""Application services that feed the remaining desktop screens."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import Session

from app.application.analytics.models import AnalyticsPeriod
from app.application.analytics.service import AnalyticsService
from app.application.exchange_rates.service import ExchangeRateService
from app.application.exchange_rates.set_manual_exchange_rate import (
    SetManualExchangeRateRequest,
)
from app.application.finances.capital import CapitalMovementRequest
from app.application.finances.exchange_currency import (
    ExchangeCurrencyRequest,
)
from app.application.finances.operations_service import (
    FinanceOperationsService,
)
from app.application.finances.register_expense import RegisterExpenseRequest
from app.application.finances.transfer_money import TransferMoneyRequest
from app.application.inventory import ReceivePurchaseRequest, ReceiptItemRequest
from app.application.purchases import (
    PurchaseItemRequest,
    RegisterPurchase,
    RegisterPurchaseRequest,
    UpdatePurchaseStatus,
    UpdatePurchaseStatusRequest,
)
from app.application.receiving.service import ReceivingService
from app.application.returns.register_customer_return import (
    CustomerReturnItemRequest,
    RegisterCustomerReturnRequest,
)
from app.application.returns.register_supplier_return import (
    RegisterSupplierReturnRequest,
    SupplierReturnItemRequest,
)
from app.application.returns.service import ReturnsService
from app.application.sales.register_sale import (
    RegisterSaleRequest,
    SaleItemRequest,
)
from app.application.sales.service import SalesService
from app.domain.entities.account import Account
from app.domain.entities.currency import Currency
from app.domain.entities.product import Product
from app.domain.entities.product_variant import ProductVariant
from app.domain.entities.supplier import Supplier
from app.domain.enums.capital_movement_type import CapitalMovementType
from app.domain.enums.expense_type import ExpenseType
from app.domain.enums.purchase_status import PurchaseStatus
from app.domain.enums.return_condition import ReturnCondition
from app.domain.value_objects.money import Money
from app.infrastructure.database.repositories import (
    SqlAlchemyAccountRepository,
    SqlAlchemyCurrencyRepository,
    SqlAlchemyProductRepository,
    SqlAlchemyProductVariantRepository,
    SqlAlchemySupplierRepository,
)
from app.infrastructure.database.session import create_session_factory
from app.infrastructure.database.unit_of_work import (
    SqlAlchemyUnitOfWorkFactory,
)

NOW = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)


@pytest.fixture
def uow_factory(migrated_engine) -> SqlAlchemyUnitOfWorkFactory:
    return SqlAlchemyUnitOfWorkFactory(
        create_session_factory(migrated_engine)
    )


@pytest.fixture
def seed(db_session: Session) -> SimpleNamespace:
    currencies = SqlAlchemyCurrencyRepository(db_session)
    usd = currencies.get_by_code("USD")
    assert usd is not None
    eur = currencies.get_by_code("EUR")
    if eur is None:
        eur = currencies.add(Currency("EUR", "Euro", 2))
    accounts = SqlAlchemyAccountRepository(db_session)
    cash = accounts.add(Account("Cash USD", usd))
    bank = accounts.add(Account("Bank USD", usd))
    euro_cash = accounts.add(Account("Cash EUR", eur))
    supplier = SqlAlchemySupplierRepository(db_session).add(
        Supplier(name="Acme Supplier")
    )
    products = SqlAlchemyProductRepository(db_session)
    product = products.add(
        Product(
            name="Phone",
            default_selling_price=Money("10.00", usd),
        )
    )
    variant = SqlAlchemyProductVariantRepository(db_session).add(
        ProductVariant(
            product_id=product.id,
            variant_name="128 GB",
            sku="PHONE-128",
        )
    )
    db_session.commit()
    return SimpleNamespace(
        usd=usd,
        eur=eur,
        cash=cash,
        bank=bank,
        euro_cash=euro_cash,
        supplier=supplier,
        product=product,
        variant=variant,
    )


def _register_purchase(
    uow_factory: SqlAlchemyUnitOfWorkFactory,
    seed: SimpleNamespace,
    *,
    quantity: int = 10,
    unit_price: str = "5.00",
    in_transit: bool = True,
):
    with uow_factory.unit_of_work() as uow:
        result = RegisterPurchase(
            accounts=uow.accounts,
            purchases=uow.purchases,
            items=uow.purchase_items,
            costs=uow.purchase_costs,
            allocations=uow.purchase_allocations,
            exchange_rates=uow.exchange_rates,
            transactions=uow.transactions,
        ).execute(
            RegisterPurchaseRequest(
                currency=seed.usd,
                purchase_date=NOW,
                items=(
                    PurchaseItemRequest(
                        variant_id=seed.variant.id,
                        quantity=quantity,
                        unit_price=Money(unit_price, seed.usd),
                    ),
                ),
                supplier_id=seed.supplier.id,
                account_id=seed.cash.id,
            )
        )
        if in_transit:
            transitions = UpdatePurchaseStatus(uow.purchases)
            for target in (
                PurchaseStatus.SHIPPED,
                PurchaseStatus.IN_TRANSIT,
            ):
                transitions.execute(
                    UpdatePurchaseStatusRequest(result.purchase.id, target)
                )
        uow.commit()
        return result


def _receive_all(
    uow_factory: SqlAlchemyUnitOfWorkFactory,
    registered,
    *,
    received_at: datetime = NOW,
):
    item = registered.items[0]
    assert item.id is not None
    service = ReceivingService(uow_factory)
    return service.receive_purchase(
        ReceivePurchaseRequest(
            purchase_id=registered.purchase.id,
            items=(
                ReceiptItemRequest(item.id, item.quantity),
            ),
            received_at=received_at,
        )
    )


def _register_sale(
    uow_factory: SqlAlchemyUnitOfWorkFactory,
    seed: SimpleNamespace,
    *,
    quantity: int = 2,
    unit_price: str = "10.00",
):
    service = SalesService(uow_factory)
    return service.register_sale(
        RegisterSaleRequest(
            account_id=seed.cash.id,
            currency=seed.usd,
            sale_date=NOW + timedelta(hours=1),
            items=(
                SaleItemRequest(
                    variant_id=seed.variant.id,
                    quantity=quantity,
                    unit_price=Money(unit_price, seed.usd),
                ),
            ),
        )
    )


def test_receiving_and_inventory_read_models(
    uow_factory, seed
) -> None:
    registered = _register_purchase(uow_factory, seed)
    receiving = ReceivingService(uow_factory)
    rows = receiving.list_receivable_purchases()
    assert len(rows) == 1
    assert rows[0].purchase_id == registered.purchase.id
    assert rows[0].supplier_name == "Acme Supplier"
    assert rows[0].lines[0].remaining_quantity == 10

    item = rows[0].lines[0]
    progress = receiving.receive_purchase(
        ReceivePurchaseRequest(
            purchase_id=rows[0].purchase_id,
            items=(ReceiptItemRequest(item.purchase_item_id, 4),),
            received_at=NOW,
        )
    )
    assert progress.purchase.status is PurchaseStatus.PARTIALLY_RECEIVED
    assert progress.lots[0].remaining_quantity == 4
    assert progress.movements[0].quantity == 4

    remaining_row = receiving.list_receivable_purchases()[0]
    assert remaining_row.lines[0].received_quantity == 4
    assert remaining_row.lines[0].remaining_quantity == 6

    from app.application.inventory.service import InventoryService

    inventory = InventoryService(uow_factory)
    stock = inventory.list_stock()
    assert stock[0].on_hand == 4
    assert stock[0].label == "Phone / 128 GB"
    lots = inventory.list_lots()
    assert len(lots) == 1
    assert lots[0].remaining_quantity == 4
    movements = inventory.list_movements()
    assert len(movements) == 1
    assert movements[0].quantity == 4


def test_sales_and_returns_services(uow_factory, seed) -> None:
    registered = _register_purchase(uow_factory, seed, quantity=6)
    _receive_all(uow_factory, registered)

    sales = SalesService(uow_factory)
    options = sales.list_variant_options()
    assert options[0].variant_id == seed.variant.id
    assert options[0].on_hand == 6
    assert options[0].default_selling_price == Money("10.00", seed.usd)

    sale = _register_sale(uow_factory, seed, quantity=2)
    report = sales.list_sales()
    assert len(report) == 1
    assert report[0].total == Money("20.00", seed.usd)
    assert report[0].cogs == (Money("10.00", seed.usd),)
    assert report[0].gross_profit == (Money("10.00", seed.usd),)

    detail = sales.get_sale_detail(sale.sale.id)
    assert detail.lines[0].quantity == 2
    assert detail.allocations[0].quantity == 2

    returns = ReturnsService(uow_factory)
    returnable = returns.list_returnable_sales()
    assert len(returnable) == 1
    context = returns.get_customer_return_context(sale.sale.id)
    assert context.lines[0].returnable_quantity == 2
    line = context.lines[0]
    returned = returns.register_customer_return(
        RegisterCustomerReturnRequest(
            sale_id=sale.sale.id,
            return_date=NOW + timedelta(hours=2),
            items=(
                CustomerReturnItemRequest(
                    sale_item_id=line.sale_item_id,
                    quantity=1,
                    condition=ReturnCondition.SELLABLE,
                ),
            ),
            account_id=seed.cash.id,
            refund_amount=Money("10.00", seed.usd),
        )
    )
    assert returned.total_refunded == Money("10.00", seed.usd)
    assert returns.list_customer_returns()[0].refund_amount == Money(
        "10.00", seed.usd
    )

    after_return = returns.get_customer_return_context(sale.sale.id)
    assert after_return.lines[0].returnable_quantity == 1

    purchase_context = returns.list_returnable_purchases()
    assert len(purchase_context) == 1
    supplier_context = returns.get_supplier_return_context(
        registered.purchase.id
    )
    lot = supplier_context.lots[0]
    returned_supplier = returns.register_supplier_return(
        RegisterSupplierReturnRequest(
            purchase_id=registered.purchase.id,
            return_date=NOW + timedelta(hours=3),
            items=(
                SupplierReturnItemRequest(
                    purchase_item_id=lot.purchase_item_id,
                    inventory_lot_id=lot.lot_id,
                    quantity=1,
                ),
            ),
        )
    )
    assert len(returned_supplier.items) == 1
    assert len(returns.list_supplier_returns()) == 1


def test_finance_and_exchange_services(uow_factory, seed) -> None:
    finance = FinanceOperationsService(uow_factory)
    finance.add_capital(
        CapitalMovementRequest(
            account_id=seed.cash.id,
            amount=Money("100.00", seed.usd),
            movement_date=NOW,
        )
    )
    finance.withdraw_capital(
        CapitalMovementRequest(
            account_id=seed.cash.id,
            amount=Money("10.00", seed.usd),
            movement_date=NOW,
        )
    )
    finance.register_expense(
        RegisterExpenseRequest(
            account_id=seed.cash.id,
            expense_type=ExpenseType.ADVERTISING,
            amount=Money("5.00", seed.usd),
            expense_date=NOW,
        )
    )
    finance.transfer_money(
        TransferMoneyRequest(
            source_account_id=seed.cash.id,
            destination_account_id=seed.bank.id,
            amount=Money("20.00", seed.usd),
            transfer_date=NOW,
        )
    )

    rates = ExchangeRateService(
        uow_factory,
        freshness=timedelta(hours=24),
        clock=lambda: NOW,
    )
    rates.set_manual(
        SetManualExchangeRateRequest(
            base_code="USD",
            quote_code="EUR",
            rate=Decimal("0.90"),
            rate_timestamp=NOW,
        )
    )
    rates.set_manual(
        SetManualExchangeRateRequest(
            base_code="EUR",
            quote_code="USD",
            rate=Decimal("1.10"),
            rate_timestamp=NOW,
        )
    )
    usd_to_eur = next(
        row
        for row in rates.list_latest_rates()
        if row.base_code == "USD" and row.quote_code == "EUR"
    )
    exchange = finance.exchange_currency(
        ExchangeCurrencyRequest(
            source_account_id=seed.bank.id,
            destination_account_id=seed.euro_cash.id,
            source_amount=Money("10.00", seed.usd),
            exchange_rate_id=usd_to_eur.exchange_rate_id,
            transfer_date=NOW,
        )
    )
    assert exchange.destination_amount.currency == seed.eur
    assert exchange.destination_amount == Money("9.00", seed.eur)

    expenses = finance.list_expenses()
    assert expenses[0].expense_type is ExpenseType.ADVERTISING
    capital = finance.list_capital_movements()
    assert {row.movement_type for row in capital} == {
        CapitalMovementType.CONTRIBUTION,
        CapitalMovementType.WITHDRAWAL,
    }
    transfers = finance.list_transfers()
    assert len(transfers) == 2
    assert any(row.is_cross_currency for row in transfers)


def test_exchange_rate_service_freshness_history(uow_factory, seed) -> None:
    rates = ExchangeRateService(
        uow_factory,
        freshness=timedelta(hours=1),
        clock=lambda: NOW + timedelta(hours=2),
    )
    rates.set_manual(
        SetManualExchangeRateRequest(
            base_code="USD",
            quote_code="EUR",
            rate=Decimal("0.90"),
            rate_timestamp=NOW,
        )
    )
    latest = rates.list_latest_rates()
    assert len(latest) == 1
    assert latest[0].is_stale is True
    assert latest[0].rate == "0.90"
    history = rates.list_history("USD", "EUR")
    assert len(history) == 1


def test_analytics_service_snapshot(uow_factory, seed) -> None:
    registered = _register_purchase(uow_factory, seed, quantity=5)
    _receive_all(uow_factory, registered)
    _register_sale(uow_factory, seed, quantity=2)

    analytics = AnalyticsService(
        uow_factory,
        base_currency="USD",
        slow_moving_days=30,
    )
    dashboard = analytics.dashboard()
    assert dashboard.report.revenue == Money("20.00", seed.usd)
    assert dashboard.report.cogs == Money("10.00", seed.usd)
    assert dashboard.report.net_profit == Money("10.00", seed.usd)
    assert dashboard.performance.best_sellers[0].product_name == "Phone"

    snapshot = analytics.analytics(
        AnalyticsPeriod(start=NOW - timedelta(days=1), end=NOW + timedelta(days=1))
    )
    assert snapshot.report.revenue == Money("20.00", seed.usd)
    assert snapshot.performance.most_profitable[0].product_name == "Phone"
    assert snapshot.suppliers.suppliers[0].supplier_name == "Acme Supplier"


def test_analytics_service_dashboard_overview_prepares_charts(
    uow_factory,
    seed,
) -> None:
    registered = _register_purchase(uow_factory, seed, quantity=5)
    _receive_all(uow_factory, registered)
    _register_sale(uow_factory, seed, quantity=2)

    analytics = AnalyticsService(
        uow_factory,
        base_currency="USD",
        slow_moving_days=30,
    )
    overview = analytics.dashboard_overview(limit=5)

    assert overview.charts.sales_evolution
    assert overview.charts.granularity == "day"
    assert sum(
        (point.revenue.amount for point in overview.charts.sales_evolution),
        Decimal("0"),
    ) == overview.report.revenue.amount
    assert [item.key for item in overview.charts.revenue_expenses] == [
        "revenue",
        "expenses",
        "gross_profit",
        "net_profit",
    ]
    assert overview.charts.revenue_expenses[0].amount == Money(
        "20.00", seed.usd
    )
    assert overview.charts.top_products[0].label == "Phone"
    assert overview.charts.top_products[0].quantity == 2
