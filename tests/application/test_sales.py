"""FIFO sales against a migrated SQLite database."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.application.inventory import (
    GetVariantStock,
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
from app.application.sales import (
    RegisterSale,
    RegisterSaleRequest,
    SaleItemRequest,
)
from app.domain.entities.account import Account
from app.domain.entities.currency import Currency
from app.domain.entities.product import Product
from app.domain.entities.product_variant import ProductVariant
from app.domain.enums.financial_transaction_type import (
    FinancialTransactionType,
)
from app.domain.enums.inventory_movement_type import InventoryMovementType
from app.domain.enums.purchase_status import PurchaseStatus
from app.domain.enums.sale_status import SaleStatus
from app.domain.exceptions import (
    AccountCurrencyMismatchError,
    CustomerNotFoundError,
    InactiveAccountError,
    InsufficientStockError,
    InvalidSaleError,
    VariantNotFoundError,
)
from app.domain.sales_costing import sale_cogs
from app.domain.value_objects.money import Money
from app.infrastructure.database.models import CustomerModel
from app.infrastructure.database.repositories import (
    SqlAlchemyAccountRepository,
    SqlAlchemyCurrencyRepository,
    SqlAlchemyCustomerRepository,
    SqlAlchemyExchangeRateRepository,
    SqlAlchemyFinancialTransactionRepository,
    SqlAlchemyInventoryLotRepository,
    SqlAlchemyInventoryMovementRepository,
    SqlAlchemyProductRepository,
    SqlAlchemyProductVariantRepository,
    SqlAlchemyPurchaseCostAllocationRepository,
    SqlAlchemyPurchaseCostRepository,
    SqlAlchemyPurchaseItemRepository,
    SqlAlchemyPurchaseRepository,
    SqlAlchemySaleItemLotAllocationRepository,
    SqlAlchemySaleItemRepository,
    SqlAlchemySaleRepository,
)

NOW = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)
LATER = NOW + timedelta(days=1)
LATER_STILL = NOW + timedelta(days=2)


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


def _variant(db_session, name: str = "Phone") -> ProductVariant:
    product = SqlAlchemyProductRepository(db_session).add(
        Product(name=name)
    )
    return SqlAlchemyProductVariantRepository(db_session).add(
        ProductVariant(product_id=product.id, variant_name=name)
    )


def _purchase(
    db_session,
    *,
    variant_id: int,
    quantity: int,
    price: str,
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
        allocations=SqlAlchemyPurchaseCostAllocationRepository(
            db_session
        ),
        exchange_rates=SqlAlchemyExchangeRateRepository(db_session),
        transactions=SqlAlchemyFinancialTransactionRepository(
            db_session
        ),
    ).execute(
        RegisterPurchaseRequest(
            currency=currency,
            purchase_date=received_at,
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
        allocations=SqlAlchemyPurchaseCostAllocationRepository(
            db_session
        ),
        lots=SqlAlchemyInventoryLotRepository(db_session),
        movements=SqlAlchemyInventoryMovementRepository(db_session),
    ).execute(
        ReceivePurchaseRequest(
            purchase_id=registered.purchase.id,
            items=(ReceiptItemRequest(item.id, quantity),),
            received_at=received_at,
        )
    )
    return registered


def _sale_service(db_session) -> RegisterSale:
    return RegisterSale(
        accounts=SqlAlchemyAccountRepository(db_session),
        customers=SqlAlchemyCustomerRepository(db_session),
        variants=SqlAlchemyProductVariantRepository(db_session),
        sales=SqlAlchemySaleRepository(db_session),
        items=SqlAlchemySaleItemRepository(db_session),
        allocations=SqlAlchemySaleItemLotAllocationRepository(
            db_session
        ),
        lots=SqlAlchemyInventoryLotRepository(db_session),
        movements=SqlAlchemyInventoryMovementRepository(db_session),
        transactions=SqlAlchemyFinancialTransactionRepository(
            db_session
        ),
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
    items: list[SaleItemRequest] | tuple[SaleItemRequest, ...],
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


def _stock(db_session, variant_id: int) -> int:
    return GetVariantStock(
        SqlAlchemyProductVariantRepository(db_session),
        SqlAlchemyInventoryLotRepository(db_session),
    ).execute(variant_id).quantity


def test_one_lot_sale_consumes_stock_and_records_fifo_cogs(
    db_session,
) -> None:
    variant = _variant(db_session)
    _purchase(
        db_session, variant_id=variant.id, quantity=10, price="5.00"
    )
    account = _account(db_session)

    result = _sell(
        db_session,
        account,
        [_item(variant.id, 4, "12.00", account.currency)],
    )

    assert result.sale.status is SaleStatus.COMPLETED
    assert result.sale.account_id == account.id
    assert result.revenue == Money("48", account.currency)
    assert result.cogs == Money("20", account.currency)
    assert result.gross_profit == Money("28", account.currency)
    assert result.cogs_by_currency == (Money("20", account.currency),)

    assert len(result.items) == 1
    item = result.items[0]
    assert item.sale.id == result.sale.id
    assert item.line_total == Money("48", account.currency)

    assert len(result.allocations) == 1
    allocation = result.allocations[0]
    assert allocation.quantity == 4
    assert allocation.unit_cost_snapshot == Money("5", account.currency)
    assert allocation.cogs == Money("20", account.currency)

    assert len(result.movements) == 1
    movement = result.movements[0]
    assert movement.movement_type is InventoryMovementType.SALE
    assert movement.quantity == -4
    assert movement.inventory_lot_id == allocation.inventory_lot.id
    assert movement.reference_type == "SALE"
    assert movement.reference_id == result.sale.id

    assert _stock(db_session, variant.id) == 6

    entries = SqlAlchemyFinancialTransactionRepository(
        db_session
    ).list_for_account(account.id)
    assert len(entries) == 1
    assert entries[0].transaction_type is FinancialTransactionType.SALE
    assert entries[0].amount == Money("48", account.currency)
    assert entries[0].sale_id == result.sale.id
    assert SqlAlchemyFinancialTransactionRepository(
        db_session
    ).get_balance(account) == Money("48", account.currency)

    stored_sale = SqlAlchemySaleRepository(db_session).get_by_id(
        result.sale.id
    )
    assert stored_sale is not None
    assert stored_sale.status is SaleStatus.COMPLETED
    assert stored_sale.customer_id is None

    stored_items = SqlAlchemySaleItemRepository(db_session).list_for_sale(
        result.sale.id
    )
    assert [stored.id for stored in stored_items] == [item.id]
    stored_allocations = (
        SqlAlchemySaleItemLotAllocationRepository(db_session)
        .list_for_sale_item(item.id)
    )
    assert [stored.id for stored in stored_allocations] == [
        allocation.id
    ]
    assert (
        SqlAlchemySaleItemLotAllocationRepository(db_session)
        .list_for_sale(result.sale.id)
        == [allocation]
    )
    assert (
        SqlAlchemySaleItemLotAllocationRepository(db_session)
        .list_for_lot(allocation.inventory_lot.id)
        == [allocation]
    )


def test_multi_lot_sale_uses_fifo_and_preserves_historical_cogs(
    db_session,
) -> None:
    variant = _variant(db_session)
    _purchase(
        db_session,
        variant_id=variant.id,
        quantity=10,
        price="5.00",
        received_at=NOW,
    )
    _purchase(
        db_session,
        variant_id=variant.id,
        quantity=10,
        price="7.00",
        received_at=LATER,
    )
    account = _account(db_session)

    result = _sell(
        db_session,
        account,
        [_item(variant.id, 12, "12.00", account.currency)],
    )

    assert [
        (allocation.quantity, allocation.unit_cost_snapshot)
        for allocation in result.allocations
    ] == [
        (10, Money("5", account.currency)),
        (2, Money("7", account.currency)),
    ]
    assert result.revenue == Money("144", account.currency)
    assert result.cogs == Money("64", account.currency)
    assert result.gross_profit == Money("80", account.currency)
    assert [movement.quantity for movement in result.movements] == [
        -10,
        -2,
    ]
    assert _stock(db_session, variant.id) == 8

    _purchase(
        db_session,
        variant_id=variant.id,
        quantity=10,
        price="9.00",
        received_at=LATER_STILL,
    )
    stored = SqlAlchemySaleItemLotAllocationRepository(
        db_session
    ).list_for_sale(result.sale.id)
    assert [
        (allocation.quantity, allocation.unit_cost_snapshot)
        for allocation in stored
    ] == [
        (10, Money("5", account.currency)),
        (2, Money("7", account.currency)),
    ]
    assert sale_cogs(stored) == Money("64", account.currency)


def test_exact_exhaustion_leaves_zero_stock(db_session) -> None:
    variant = _variant(db_session)
    _purchase(
        db_session, variant_id=variant.id, quantity=10, price="5.00"
    )
    account = _account(db_session)

    result = _sell(
        db_session,
        account,
        [_item(variant.id, 10, "12.00", account.currency)],
    )

    assert result.allocations[0].quantity == 10
    assert result.movements[0].quantity == -10
    assert _stock(db_session, variant.id) == 0


def test_insufficient_stock_writes_nothing(db_session) -> None:
    variant = _variant(db_session)
    _purchase(
        db_session, variant_id=variant.id, quantity=4, price="5.00"
    )
    account = _account(db_session)

    with pytest.raises(InsufficientStockError):
        _sell(
            db_session,
            account,
            [_item(variant.id, 5, "12.00", account.currency)],
        )

    assert SqlAlchemySaleRepository(db_session).list_all() == []
    assert _stock(db_session, variant.id) == 4
    assert SqlAlchemyFinancialTransactionRepository(
        db_session
    ).list_for_account(account.id) == []
    assert [
        movement.movement_type
        for movement in SqlAlchemyInventoryMovementRepository(
            db_session
        ).list_by_variant(variant.id)
    ] == [InventoryMovementType.PURCHASE_RECEIVED]


def test_later_insufficient_item_does_not_write_earlier_items(
    db_session,
) -> None:
    first_variant = _variant(db_session, "Phone")
    second_variant = _variant(db_session, "Tablet")
    _purchase(
        db_session,
        variant_id=first_variant.id,
        quantity=10,
        price="5.00",
    )
    account = _account(db_session)

    with pytest.raises(InsufficientStockError):
        _sell(
            db_session,
            account,
            [
                _item(first_variant.id, 2, "12.00", account.currency),
                _item(second_variant.id, 1, "20.00", account.currency),
            ],
        )

    assert SqlAlchemySaleRepository(db_session).list_all() == []
    assert _stock(db_session, first_variant.id) == 10
    assert _stock(db_session, second_variant.id) == 0
    assert SqlAlchemyFinancialTransactionRepository(
        db_session
    ).list_for_account(account.id) == []


def test_duplicate_variant_lines_share_fifo_without_over_allocation(
    db_session,
) -> None:
    variant = _variant(db_session)
    _purchase(
        db_session,
        variant_id=variant.id,
        quantity=6,
        price="5.00",
        received_at=NOW,
    )
    _purchase(
        db_session,
        variant_id=variant.id,
        quantity=6,
        price="7.00",
        received_at=LATER,
    )
    account = _account(db_session)

    result = _sell(
        db_session,
        account,
        [
            _item(variant.id, 4, "10.00", account.currency),
            _item(variant.id, 8, "10.00", account.currency),
        ],
    )

    assert [
        (allocation.quantity, allocation.unit_cost_snapshot)
        for allocation in result.allocations
    ] == [
        (4, Money("5", account.currency)),
        (2, Money("5", account.currency)),
        (6, Money("7", account.currency)),
    ]
    assert result.revenue == Money("120", account.currency)
    assert result.cogs == Money("72", account.currency)
    assert result.gross_profit == Money("48", account.currency)
    assert _stock(db_session, variant.id) == 0


def test_item_and_sale_discounts_reduce_revenue(db_session) -> None:
    variant = _variant(db_session)
    _purchase(
        db_session, variant_id=variant.id, quantity=10, price="5.00"
    )
    account = _account(db_session)

    result = _sell(
        db_session,
        account,
        [_item(variant.id, 2, "10.00", account.currency, discount="1.00")],
        discount_amount=Money("2", account.currency),
    )

    assert result.revenue == Money("17", account.currency)
    assert result.cogs == Money("10", account.currency)
    assert result.gross_profit == Money("7", account.currency)
    entries = SqlAlchemyFinancialTransactionRepository(
        db_session
    ).list_for_account(account.id)
    assert entries[0].amount == Money("17", account.currency)


def test_cross_currency_sale_keeps_cogs_in_purchase_currency(
    db_session,
) -> None:
    variant = _variant(db_session)
    _purchase(
        db_session,
        variant_id=variant.id,
        quantity=10,
        price="5.00",
        currency_code="EUR",
    )
    usd_account = _account(db_session, "USD")
    eur = _currency(db_session, "EUR")

    result = _sell(
        db_session,
        usd_account,
        [_item(variant.id, 2, "12.00", usd_account.currency)],
    )

    assert result.revenue == Money("24", usd_account.currency)
    assert result.cogs == Money("10", eur)
    assert result.gross_profit is None
    assert result.cogs_by_currency == (Money("10", eur),)
    assert (
        SqlAlchemyFinancialTransactionRepository(db_session)
        .list_for_account(usd_account.id)[0]
        .amount
        == Money("24", usd_account.currency)
    )


def test_sale_with_lots_in_two_currencies_reports_cogs_per_currency(
    db_session,
) -> None:
    variant = _variant(db_session)
    _purchase(
        db_session,
        variant_id=variant.id,
        quantity=5,
        price="5.00",
        received_at=NOW,
        currency_code="EUR",
    )
    _purchase(
        db_session,
        variant_id=variant.id,
        quantity=5,
        price="7.00",
        received_at=LATER,
        currency_code="USD",
    )
    usd_account = _account(db_session, "USD")
    eur = _currency(db_session, "EUR")
    usd = _currency(db_session, "USD")

    result = _sell(
        db_session,
        usd_account,
        [_item(variant.id, 8, "12.00", usd_account.currency)],
    )

    assert result.revenue == Money("96", usd)
    assert result.cogs is None
    assert result.gross_profit is None
    assert result.cogs_by_currency == (
        Money("25", eur),
        Money("21", usd),
    )


def test_optional_customer_is_validated_and_listed(db_session) -> None:
    variant = _variant(db_session)
    _purchase(
        db_session, variant_id=variant.id, quantity=10, price="5.00"
    )
    account = _account(db_session)
    customer = CustomerModel(name="Ana")
    db_session.add(customer)
    db_session.flush()
    assert customer.id is not None

    result = _sell(
        db_session,
        account,
        [_item(variant.id, 1, "12.00", account.currency)],
        customer_id=customer.id,
    )

    assert result.sale.customer_id == customer.id
    assert [
        sale.id
        for sale in SqlAlchemySaleRepository(db_session).list_by_customer(
            customer.id
        )
    ] == [result.sale.id]

    with pytest.raises(CustomerNotFoundError):
        _sell(
            db_session,
            account,
            [_item(variant.id, 1, "12.00", account.currency)],
            customer_id=9999,
        )
    assert len(SqlAlchemySaleRepository(db_session).list_all()) == 1


def test_inactive_account_is_rejected_before_writing(db_session) -> None:
    variant = _variant(db_session)
    inactive = _account(
        db_session, "USD", name="Closed", active=False
    )

    with pytest.raises(InactiveAccountError):
        _sell(
            db_session,
            inactive,
            [_item(variant.id, 1, "10.00", inactive.currency)],
        )

    assert SqlAlchemySaleRepository(db_session).list_all() == []


def test_sale_currency_must_match_the_account(db_session) -> None:
    variant = _variant(db_session)
    account = _account(db_session, "USD")
    eur = _currency(db_session, "EUR")

    with pytest.raises(AccountCurrencyMismatchError):
        _sale_service(db_session).execute(
            RegisterSaleRequest(
                account_id=account.id,
                currency=eur,
                sale_date=NOW,
                items=(
                    SaleItemRequest(
                        variant_id=variant.id,
                        quantity=1,
                        unit_price=Money("10", eur),
                    ),
                ),
            )
        )

    assert SqlAlchemySaleRepository(db_session).list_all() == []


def test_empty_sale_is_rejected(db_session) -> None:
    account = _account(db_session)

    with pytest.raises(InvalidSaleError):
        _sale_service(db_session).execute(
            RegisterSaleRequest(
                account_id=account.id,
                currency=account.currency,
                sale_date=NOW,
                items=(),
            )
        )


def test_unknown_variant_is_rejected_before_writing(db_session) -> None:
    account = _account(db_session)

    with pytest.raises(VariantNotFoundError):
        _sell(
            db_session,
            account,
            [_item(9999, 1, "10.00", account.currency)],
        )

    assert SqlAlchemySaleRepository(db_session).list_all() == []


def test_sale_discount_cannot_exceed_the_subtotal(db_session) -> None:
    variant = _variant(db_session)
    _purchase(
        db_session, variant_id=variant.id, quantity=10, price="5.00"
    )
    account = _account(db_session)

    with pytest.raises(InvalidSaleError):
        _sell(
            db_session,
            account,
            [_item(variant.id, 1, "10.00", account.currency)],
            discount_amount=Money("11", account.currency),
        )

    assert SqlAlchemySaleRepository(db_session).list_all() == []
    assert _stock(db_session, variant.id) == 10


def test_zero_revenue_sale_is_rejected_before_writing(db_session) -> None:
    variant = _variant(db_session)
    _purchase(
        db_session, variant_id=variant.id, quantity=10, price="5.00"
    )
    account = _account(db_session)

    with pytest.raises(InvalidSaleError):
        _sell(
            db_session,
            account,
            [
                _item(
                    variant.id,
                    1,
                    "10.00",
                    account.currency,
                    discount="10.00",
                )
            ],
        )

    assert SqlAlchemySaleRepository(db_session).list_all() == []
    assert _stock(db_session, variant.id) == 10
    assert SqlAlchemyFinancialTransactionRepository(
        db_session
    ).list_for_account(account.id) == []
