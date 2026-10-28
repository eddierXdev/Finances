"""Customer returns against a migrated SQLite database."""

from __future__ import annotations

from dataclasses import replace
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
from app.application.returns import (
    CustomerReturnItemRequest,
    RegisterCustomerReturn,
    RegisterCustomerReturnRequest,
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
from app.domain.enums.return_condition import ReturnCondition
from app.domain.enums.sale_status import SaleStatus
from app.domain.exceptions import (
    AccountCurrencyMismatchError,
    CustomerRefundError,
    ExcessReturnError,
    InactiveAccountError,
    InvalidCustomerReturnError,
    SaleCurrencyMismatchError,
    SaleItemNotFoundError,
)
from app.domain.value_objects.money import Money
from app.infrastructure.database.repositories import (
    SqlAlchemyAccountRepository,
    SqlAlchemyCurrencyRepository,
    SqlAlchemyCustomerRepository,
    SqlAlchemyCustomerReturnItemRepository,
    SqlAlchemyCustomerReturnRepository,
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
    SqlAlchemyReturnLotAllocationRepository,
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


def _return_service(db_session) -> RegisterCustomerReturn:
    return RegisterCustomerReturn(
        accounts=SqlAlchemyAccountRepository(db_session),
        sales=SqlAlchemySaleRepository(db_session),
        sale_items=SqlAlchemySaleItemRepository(db_session),
        sale_allocations=SqlAlchemySaleItemLotAllocationRepository(
            db_session
        ),
        customer_returns=SqlAlchemyCustomerReturnRepository(db_session),
        return_items=SqlAlchemyCustomerReturnItemRepository(db_session),
        return_allocations=SqlAlchemyReturnLotAllocationRepository(
            db_session
        ),
        lots=SqlAlchemyInventoryLotRepository(db_session),
        movements=SqlAlchemyInventoryMovementRepository(db_session),
        transactions=SqlAlchemyFinancialTransactionRepository(
            db_session
        ),
    )


def _return_item(
    sale_item,
    quantity: int,
    condition: ReturnCondition = ReturnCondition.SELLABLE,
) -> CustomerReturnItemRequest:
    return CustomerReturnItemRequest(
        sale_item_id=sale_item.id,
        quantity=quantity,
        condition=condition,
    )


def _return(
    db_session,
    sale,
    items: tuple[CustomerReturnItemRequest, ...] | list[
        CustomerReturnItemRequest
    ],
    *,
    account: Account | None = None,
    refund: Money | None = None,
    return_date: datetime = LATER,
    notes: str | None = None,
):
    return _return_service(db_session).execute(
        RegisterCustomerReturnRequest(
            sale_id=sale.id,
            return_date=return_date,
            items=tuple(items),
            account_id=account.id if account is not None else None,
            refund_amount=refund,
            notes=notes,
        )
    )


def _stock(db_session, variant_id: int) -> int:
    return GetVariantStock(
        SqlAlchemyProductVariantRepository(db_session),
        SqlAlchemyInventoryLotRepository(db_session),
    ).execute(variant_id).quantity


def _entries(db_session, account: Account):
    return SqlAlchemyFinancialTransactionRepository(
        db_session
    ).list_for_account(account.id)


def test_sellable_return_restores_lot_and_records_customer_refund(
    db_session,
) -> None:
    variant = _variant(db_session)
    _purchase(
        db_session, variant_id=variant.id, quantity=10, price="5.00"
    )
    account = _account(db_session)
    sold = _sell(
        db_session,
        account,
        [_item(variant.id, 4, "12.00", account.currency)],
    )
    assert _stock(db_session, variant.id) == 6

    returned = _return(
        db_session,
        sold.sale,
        [_return_item(sold.items[0], 2)],
        account=account,
        refund=Money("24", account.currency),
    )

    assert returned.customer_return.sale_id == sold.sale.id
    assert returned.customer_return.account_id == account.id
    assert returned.customer_return.refund_amount == Money(
        "24", account.currency
    )
    assert returned.customer_return.notes is None
    assert returned.sale.status is SaleStatus.PARTIALLY_REFUNDED
    assert returned.total_refunded == Money("24", account.currency)

    assert len(returned.items) == 1
    item = returned.items[0]
    assert item.sale_item_id == sold.items[0].id
    assert item.quantity == 2
    assert item.condition is ReturnCondition.SELLABLE

    assert len(returned.allocations) == 1
    allocation = returned.allocations[0]
    assert (
        allocation.sale_item_lot_allocation.id
        == sold.allocations[0].id
    )
    assert allocation.inventory_lot_id == sold.allocations[0].inventory_lot.id
    assert allocation.quantity == 2
    assert allocation.unit_cost_snapshot == Money("5", account.currency)
    assert allocation.cost == Money("10", account.currency)

    assert len(returned.movements) == 1
    movement = returned.movements[0]
    assert movement.movement_type is InventoryMovementType.CUSTOMER_RETURN
    assert movement.quantity == 2
    assert movement.inventory_lot_id == sold.allocations[0].inventory_lot.id
    assert movement.unit_cost == Money("5", account.currency)
    assert movement.reference_type == "CUSTOMER_RETURN"
    assert movement.reference_id == returned.customer_return.id

    assert _stock(db_session, variant.id) == 8

    assert returned.refund is not None
    assert (
        returned.refund.transaction_type
        is FinancialTransactionType.CUSTOMER_REFUND
    )
    assert returned.refund.amount == Money("-24", account.currency)
    assert returned.refund.customer_return_id == returned.customer_return.id
    assert returned.refund.sale_id is None

    entries = _entries(db_session, account)
    assert [
        (entry.transaction_type, entry.amount) for entry in entries
    ] == [
        (FinancialTransactionType.SALE, Money("48", account.currency)),
        (
            FinancialTransactionType.CUSTOMER_REFUND,
            Money("-24", account.currency),
        ),
    ]
    assert SqlAlchemyFinancialTransactionRepository(
        db_session
    ).get_balance(account) == Money("24", account.currency)

    stored_sale = SqlAlchemySaleRepository(db_session).get_by_id(
        sold.sale.id
    )
    assert stored_sale is not None
    assert stored_sale.status is SaleStatus.PARTIALLY_REFUNDED
    assert stored_sale.notes == sold.sale.notes
    assert stored_sale.discount_amount == sold.sale.discount_amount

    stored_return = SqlAlchemyCustomerReturnRepository(
        db_session
    ).get_by_id(returned.customer_return.id)
    assert stored_return is not None
    assert stored_return.refund_amount == Money("24", account.currency)
    assert (
        SqlAlchemyCustomerReturnRepository(db_session).list_for_sale(
            sold.sale.id
        )
        == [stored_return]
    )
    assert [
        stored.id
        for stored in SqlAlchemyCustomerReturnItemRepository(
            db_session
        ).list_for_sale(sold.sale.id)
    ] == [item.id]
    assert [
        stored.id
        for stored in SqlAlchemyReturnLotAllocationRepository(
            db_session
        ).list_for_sale(sold.sale.id)
    ] == [allocation.id]


def test_damaged_return_is_recorded_without_restoring_sellable_stock(
    db_session,
) -> None:
    variant = _variant(db_session)
    _purchase(
        db_session, variant_id=variant.id, quantity=10, price="5.00"
    )
    account = _account(db_session)
    sold = _sell(
        db_session,
        account,
        [_item(variant.id, 4, "12.00", account.currency)],
    )

    returned = _return(
        db_session,
        sold.sale,
        [_return_item(sold.items[0], 2, ReturnCondition.DAMAGED)],
    )

    assert returned.customer_return.refund_amount is None
    assert returned.customer_return.account_id is None
    assert returned.refund is None
    assert returned.total_refunded == Money("0", account.currency)
    assert returned.sale.status is SaleStatus.COMPLETED
    assert returned.movements == ()
    assert len(returned.allocations) == 1
    assert returned.allocations[0].quantity == 2
    assert _stock(db_session, variant.id) == 6

    movements = SqlAlchemyInventoryMovementRepository(
        db_session
    ).list_by_variant(variant.id)
    assert [movement.movement_type for movement in movements] == [
        InventoryMovementType.PURCHASE_RECEIVED,
        InventoryMovementType.SALE,
    ]
    assert [
        entry.transaction_type for entry in _entries(db_session, account)
    ] == [FinancialTransactionType.SALE]


def test_partial_fifo_reversal_uses_the_most_recent_allocation_first(
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
    sold = _sell(
        db_session,
        account,
        [_item(variant.id, 12, "12.00", account.currency)],
    )
    assert [
        (allocation.quantity, allocation.unit_cost_snapshot)
        for allocation in sold.allocations
    ] == [
        (10, Money("5", account.currency)),
        (2, Money("7", account.currency)),
    ]
    assert _stock(db_session, variant.id) == 8

    first = _return(
        db_session,
        sold.sale,
        [_return_item(sold.items[0], 1)],
        return_date=LATER_STILL,
    )

    assert len(first.allocations) == 1
    assert (
        first.allocations[0].sale_item_lot_allocation.id
        == sold.allocations[1].id
    )
    assert first.allocations[0].quantity == 1
    assert first.allocations[0].unit_cost_snapshot == Money(
        "7", account.currency
    )
    assert first.movements[0].unit_cost == Money("7", account.currency)
    assert _stock(db_session, variant.id) == 9

    second = _return(
        db_session,
        sold.sale,
        [_return_item(sold.items[0], 2)],
        return_date=LATER_STILL + timedelta(days=1),
    )

    assert [
        (
            allocation.sale_item_lot_allocation.id,
            allocation.quantity,
            allocation.unit_cost_snapshot,
        )
        for allocation in second.allocations
    ] == [
        (sold.allocations[1].id, 1, Money("7", account.currency)),
        (sold.allocations[0].id, 1, Money("5", account.currency)),
    ]
    assert [movement.quantity for movement in second.movements] == [1, 1]
    assert _stock(db_session, variant.id) == 11


def test_excess_return_is_rejected_before_writing(db_session) -> None:
    variant = _variant(db_session)
    _purchase(
        db_session, variant_id=variant.id, quantity=10, price="5.00"
    )
    account = _account(db_session)
    sold = _sell(
        db_session,
        account,
        [_item(variant.id, 2, "12.00", account.currency)],
    )

    with pytest.raises(ExcessReturnError):
        _return(
            db_session,
            sold.sale,
            [_return_item(sold.items[0], 3)],
            account=account,
            refund=Money("36", account.currency),
        )

    assert SqlAlchemyCustomerReturnRepository(db_session).list_all() == []
    assert _stock(db_session, variant.id) == 8
    assert [
        entry.transaction_type for entry in _entries(db_session, account)
    ] == [FinancialTransactionType.SALE]
    assert (
        SqlAlchemySaleRepository(db_session)
        .get_by_id(sold.sale.id)
        .status
        is SaleStatus.COMPLETED
    )

    first = _return(
        db_session,
        sold.sale,
        [_return_item(sold.items[0], 2)],
    )
    assert first.customer_return.id is not None

    with pytest.raises(ExcessReturnError):
        _return(
            db_session,
            sold.sale,
            [_return_item(sold.items[0], 1)],
        )

    assert len(SqlAlchemyCustomerReturnRepository(db_session).list_all()) == 1


def test_full_refund_sets_refunded_status_and_rejects_later_returns(
    db_session,
) -> None:
    variant = _variant(db_session)
    _purchase(
        db_session, variant_id=variant.id, quantity=10, price="5.00"
    )
    account = _account(db_session)
    sold = _sell(
        db_session,
        account,
        [_item(variant.id, 4, "12.00", account.currency)],
    )

    returned = _return(
        db_session,
        sold.sale,
        [_return_item(sold.items[0], 4)],
        account=account,
        refund=Money("48", account.currency),
    )

    assert returned.sale.status is SaleStatus.REFUNDED
    assert returned.total_refunded == Money("48", account.currency)
    assert returned.refund is not None
    assert returned.refund.amount == Money("-48", account.currency)
    assert SqlAlchemyFinancialTransactionRepository(
        db_session
    ).get_balance(account) == Money("0", account.currency)
    assert _stock(db_session, variant.id) == 10

    with pytest.raises(InvalidCustomerReturnError):
        _return(
            db_session,
            sold.sale,
            [_return_item(sold.items[0], 1)],
        )


def test_partial_refund_then_full_refund_updates_status_cumulatively(
    db_session,
) -> None:
    variant = _variant(db_session)
    _purchase(
        db_session, variant_id=variant.id, quantity=10, price="5.00"
    )
    account = _account(db_session)
    sold = _sell(
        db_session,
        account,
        [_item(variant.id, 4, "12.00", account.currency)],
    )

    first = _return(
        db_session,
        sold.sale,
        [_return_item(sold.items[0], 1)],
        account=account,
        refund=Money("10", account.currency),
    )
    assert first.sale.status is SaleStatus.PARTIALLY_REFUNDED
    assert first.total_refunded == Money("10", account.currency)

    second = _return(
        db_session,
        sold.sale,
        [_return_item(sold.items[0], 1)],
        account=account,
        refund=Money("38", account.currency),
        return_date=LATER_STILL,
    )

    assert second.sale.status is SaleStatus.REFUNDED
    assert second.total_refunded == Money("48", account.currency)
    assert SqlAlchemyFinancialTransactionRepository(
        db_session
    ).get_balance(account) == Money("0", account.currency)


def test_return_without_refund_keeps_an_existing_partial_refund_status(
    db_session,
) -> None:
    variant = _variant(db_session)
    _purchase(
        db_session, variant_id=variant.id, quantity=10, price="5.00"
    )
    account = _account(db_session)
    sold = _sell(
        db_session,
        account,
        [_item(variant.id, 2, "10.00", account.currency)],
    )

    _return(
        db_session,
        sold.sale,
        [_return_item(sold.items[0], 1)],
        account=account,
        refund=Money("5", account.currency),
    )
    returned = _return(
        db_session,
        sold.sale,
        [_return_item(sold.items[0], 1, ReturnCondition.DAMAGED)],
        return_date=LATER_STILL,
    )

    assert returned.sale.status is SaleStatus.PARTIALLY_REFUNDED
    assert returned.total_refunded == Money("5", account.currency)
    assert returned.refund is None


def test_mixed_conditions_for_one_sale_item_are_supported(
    db_session,
) -> None:
    variant = _variant(db_session)
    _purchase(
        db_session, variant_id=variant.id, quantity=10, price="5.00"
    )
    account = _account(db_session)
    sold = _sell(
        db_session,
        account,
        [_item(variant.id, 3, "10.00", account.currency)],
    )

    returned = _return(
        db_session,
        sold.sale,
        [
            _return_item(sold.items[0], 1, ReturnCondition.SELLABLE),
            _return_item(sold.items[0], 1, ReturnCondition.DAMAGED),
        ],
    )

    assert [item.condition for item in returned.items] == [
        ReturnCondition.SELLABLE,
        ReturnCondition.DAMAGED,
    ]
    assert [allocation.quantity for allocation in returned.allocations] == [
        1,
        1,
    ]
    assert len(returned.movements) == 1
    assert returned.movements[0].quantity == 1
    assert _stock(db_session, variant.id) == 8


def test_sellable_return_can_restore_a_lot_after_later_sales(
    db_session,
) -> None:
    variant = _variant(db_session)
    _purchase(
        db_session, variant_id=variant.id, quantity=10, price="5.00"
    )
    account = _account(db_session)
    first_sale = _sell(
        db_session,
        account,
        [_item(variant.id, 4, "12.00", account.currency)],
    )
    _sell(
        db_session,
        account,
        [_item(variant.id, 6, "12.00", account.currency)],
        sale_date=LATER,
    )
    assert _stock(db_session, variant.id) == 0

    returned = _return(
        db_session,
        first_sale.sale,
        [_return_item(first_sale.items[0], 2)],
    )

    assert returned.movements[0].inventory_lot_id == (
        first_sale.allocations[0].inventory_lot.id
    )
    assert _stock(db_session, variant.id) == 2


def test_refund_requires_account_and_matching_currency(db_session) -> None:
    variant = _variant(db_session)
    _purchase(
        db_session, variant_id=variant.id, quantity=10, price="5.00"
    )
    account = _account(db_session, "USD")
    sold = _sell(
        db_session,
        account,
        [_item(variant.id, 1, "10.00", account.currency)],
    )
    eur_account = _account(db_session, "EUR")
    inactive_account = _account(
        db_session, "USD", name="Closed", active=False
    )

    with pytest.raises(InvalidCustomerReturnError):
        _return(
            db_session,
            sold.sale,
            [_return_item(sold.items[0], 1)],
            refund=Money("10", account.currency),
        )
    with pytest.raises(InvalidCustomerReturnError):
        _return(
            db_session,
            sold.sale,
            [_return_item(sold.items[0], 1)],
            account=account,
        )
    with pytest.raises(InactiveAccountError):
        _return(
            db_session,
            sold.sale,
            [_return_item(sold.items[0], 1)],
            account=inactive_account,
            refund=Money("10", account.currency),
        )
    with pytest.raises(AccountCurrencyMismatchError):
        _return(
            db_session,
            sold.sale,
            [_return_item(sold.items[0], 1)],
            account=eur_account,
            refund=Money("10", account.currency),
        )
    with pytest.raises(SaleCurrencyMismatchError):
        _return(
            db_session,
            sold.sale,
            [_return_item(sold.items[0], 1)],
            account=account,
            refund=Money("10", eur_account.currency),
        )

    assert SqlAlchemyCustomerReturnRepository(db_session).list_all() == []
    assert _stock(db_session, variant.id) == 9


def test_refund_cannot_exceed_the_sale_revenue(db_session) -> None:
    variant = _variant(db_session)
    _purchase(
        db_session, variant_id=variant.id, quantity=10, price="5.00"
    )
    account = _account(db_session)
    sold = _sell(
        db_session,
        account,
        [_item(variant.id, 1, "10.00", account.currency)],
    )

    with pytest.raises(CustomerRefundError):
        _return(
            db_session,
            sold.sale,
            [_return_item(sold.items[0], 1)],
            account=account,
            refund=Money("11", account.currency),
        )

    assert SqlAlchemyCustomerReturnRepository(db_session).list_all() == []
    assert _stock(db_session, variant.id) == 9


def test_cumulative_refunds_cannot_exceed_the_sale_revenue(
    db_session,
) -> None:
    variant = _variant(db_session)
    _purchase(
        db_session, variant_id=variant.id, quantity=10, price="5.00"
    )
    account = _account(db_session)
    sold = _sell(
        db_session,
        account,
        [_item(variant.id, 2, "10.00", account.currency)],
    )

    first = _return(
        db_session,
        sold.sale,
        [_return_item(sold.items[0], 1)],
        account=account,
        refund=Money("5", account.currency),
    )
    assert first.sale.status is SaleStatus.PARTIALLY_REFUNDED

    with pytest.raises(CustomerRefundError):
        _return(
            db_session,
            sold.sale,
            [_return_item(sold.items[0], 1)],
            account=account,
            refund=Money("16", account.currency),
            return_date=LATER_STILL,
        )

    assert len(SqlAlchemyCustomerReturnRepository(db_session).list_all()) == 1
    assert _stock(db_session, variant.id) == 9
    assert SqlAlchemyFinancialTransactionRepository(
        db_session
    ).get_balance(account) == Money("15", account.currency)


def test_refund_can_use_a_different_account_with_the_sale_currency(
    db_session,
) -> None:
    variant = _variant(db_session)
    _purchase(
        db_session, variant_id=variant.id, quantity=10, price="5.00"
    )
    sale_account = _account(db_session, "USD", name="Sales")
    refund_account = _account(db_session, "USD", name="Refunds")
    sold = _sell(
        db_session,
        sale_account,
        [_item(variant.id, 1, "10.00", sale_account.currency)],
    )

    returned = _return(
        db_session,
        sold.sale,
        [_return_item(sold.items[0], 1)],
        account=refund_account,
        refund=Money("10", sale_account.currency),
    )

    assert returned.customer_return.account_id == refund_account.id
    assert [
        entry.transaction_type for entry in _entries(db_session, sale_account)
    ] == [FinancialTransactionType.SALE]
    assert [
        entry.transaction_type
        for entry in _entries(db_session, refund_account)
    ] == [FinancialTransactionType.CUSTOMER_REFUND]
    assert SqlAlchemyFinancialTransactionRepository(
        db_session
    ).get_balance(refund_account) == Money(
        "-10", refund_account.currency
    )

    deactivated = SqlAlchemyAccountRepository(db_session).save(
        replace(refund_account, is_active=False)
    )
    stored_return = SqlAlchemyCustomerReturnRepository(
        db_session
    ).get_by_id(returned.customer_return.id)
    assert stored_return is not None
    assert stored_return.account is not None
    assert stored_return.account.id == deactivated.id
    assert stored_return.account.is_active is False


def test_empty_return_and_unknown_sale_item_are_rejected(db_session) -> None:
    variant = _variant(db_session)
    _purchase(
        db_session, variant_id=variant.id, quantity=10, price="5.00"
    )
    account = _account(db_session)
    sold = _sell(
        db_session,
        account,
        [_item(variant.id, 1, "10.00", account.currency)],
    )

    with pytest.raises(InvalidCustomerReturnError):
        _return(db_session, sold.sale, [])

    with pytest.raises(SaleItemNotFoundError):
        _return(
            db_session,
            sold.sale,
            [
                CustomerReturnItemRequest(
                    sale_item_id=9999,
                    quantity=1,
                    condition=ReturnCondition.SELLABLE,
                )
            ],
        )

    assert SqlAlchemyCustomerReturnRepository(db_session).list_all() == []
    assert _stock(db_session, variant.id) == 9


def test_return_item_must_belong_to_the_original_sale(db_session) -> None:
    variant = _variant(db_session)
    _purchase(
        db_session, variant_id=variant.id, quantity=10, price="5.00"
    )
    account = _account(db_session)
    first_sale = _sell(
        db_session,
        account,
        [_item(variant.id, 1, "10.00", account.currency)],
    )
    second_sale = _sell(
        db_session,
        account,
        [_item(variant.id, 1, "10.00", account.currency)],
        sale_date=LATER,
    )

    with pytest.raises(InvalidCustomerReturnError):
        _return(
            db_session,
            first_sale.sale,
            [_return_item(second_sale.items[0], 1)],
        )

    assert SqlAlchemyCustomerReturnRepository(db_session).list_all() == []
    assert _stock(db_session, variant.id) == 8
