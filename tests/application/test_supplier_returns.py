"""Supplier returns against a migrated SQLite database."""

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
    PurchaseCostRequest,
    PurchaseItemRequest,
    RegisterPurchase,
    RegisterPurchaseRequest,
    UpdatePurchaseStatus,
    UpdatePurchaseStatusRequest,
)
from app.application.returns import (
    RegisterSupplierReturn,
    RegisterSupplierReturnRequest,
    SupplierReturnItemRequest,
)
from app.application.suppliers import CreateSupplier, CreateSupplierRequest
from app.domain.entities.account import Account
from app.domain.entities.currency import Currency
from app.domain.entities.product import Product
from app.domain.entities.product_variant import ProductVariant
from app.domain.enums.allocation_method import AllocationMethod
from app.domain.enums.financial_transaction_type import (
    FinancialTransactionType,
)
from app.domain.enums.inventory_movement_type import InventoryMovementType
from app.domain.enums.purchase_cost_type import PurchaseCostType
from app.domain.enums.purchase_status import PurchaseStatus
from app.domain.exceptions import (
    AccountCurrencyMismatchError,
    ExcessSupplierReturnError,
    InactiveAccountError,
    InvalidSupplierReturnError,
    InventoryLotNotFoundError,
    PurchaseCurrencyMismatchError,
    PurchaseItemNotFoundError,
    PurchaseNotFoundError,
    SupplierRefundError,
)
from app.domain.value_objects.money import Money
from app.infrastructure.database.repositories import (
    SqlAlchemyAccountRepository,
    SqlAlchemyCurrencyRepository,
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
    SqlAlchemySupplierRepository,
    SqlAlchemySupplierReturnItemRepository,
    SqlAlchemySupplierReturnRepository,
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
    costs: tuple[PurchaseCostRequest, ...] = (),
    receipt_quantities: tuple[int, ...] | None = None,
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
            supplier_id=supplier_id,
            items=(
                PurchaseItemRequest(
                    variant_id=variant_id,
                    quantity=quantity,
                    unit_price=Money(price, currency),
                ),
            ),
            costs=costs,
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

    quantities = receipt_quantities or (quantity,)
    for index, received_quantity in enumerate(quantities):
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
                items=(
                    ReceiptItemRequest(item.id, received_quantity),
                ),
                received_at=received_at + timedelta(days=index),
            )
        )
    return registered, purchase_account


def _return_service(db_session) -> RegisterSupplierReturn:
    return RegisterSupplierReturn(
        accounts=SqlAlchemyAccountRepository(db_session),
        purchases=SqlAlchemyPurchaseRepository(db_session),
        purchase_items=SqlAlchemyPurchaseItemRepository(db_session),
        lots=SqlAlchemyInventoryLotRepository(db_session),
        supplier_returns=SqlAlchemySupplierReturnRepository(db_session),
        return_items=SqlAlchemySupplierReturnItemRepository(db_session),
        movements=SqlAlchemyInventoryMovementRepository(db_session),
        transactions=SqlAlchemyFinancialTransactionRepository(
            db_session
        ),
    )


def _return_item(purchase_item, lot, quantity: int) -> SupplierReturnItemRequest:
    assert purchase_item.id is not None
    assert lot.id is not None
    return SupplierReturnItemRequest(
        purchase_item_id=purchase_item.id,
        inventory_lot_id=lot.id,
        quantity=quantity,
    )


def _return(
    db_session,
    purchase,
    items: tuple[SupplierReturnItemRequest, ...] | list[
        SupplierReturnItemRequest
    ],
    *,
    account: Account | None = None,
    refund: Money | None = None,
    return_date: datetime = LATER,
    notes: str | None = None,
):
    return _return_service(db_session).execute(
        RegisterSupplierReturnRequest(
            purchase_id=purchase.id,
            return_date=return_date,
            items=tuple(items),
            account_id=account.id if account is not None else None,
            refund_amount=refund,
            notes=notes,
        )
    )


def _lots(db_session, purchase_id: int):
    return SqlAlchemyInventoryLotRepository(db_session).list_for_purchase(
        purchase_id
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


def test_partial_supplier_return_reduces_exact_lot_and_records_refund(
    db_session,
) -> None:
    supplier = _supplier(db_session)
    variant = _variant(db_session)
    registered, purchase_account = _purchase(
        db_session,
        variant_id=variant.id,
        quantity=10,
        price="5.00",
        supplier_id=supplier.id,
    )
    lot = _lots(db_session, registered.purchase.id)[0]
    refund_account = _account(db_session, "USD", name="Refunds")

    returned = _return(
        db_session,
        registered.purchase,
        [_return_item(registered.items[0], lot, 3)],
        account=refund_account,
        refund=Money("15", refund_account.currency),
        notes="  damaged units ",
    )

    assert returned.supplier_return.purchase_id == registered.purchase.id
    assert returned.supplier_return.supplier_id == supplier.id
    assert returned.supplier_return.account_id == refund_account.id
    assert returned.supplier_return.refund_amount == Money(
        "15", refund_account.currency
    )
    assert returned.supplier_return.notes == "damaged units"
    assert returned.total_refunded == Money("15", refund_account.currency)

    assert len(returned.items) == 1
    item = returned.items[0]
    assert item.purchase_item_id == registered.items[0].id
    assert item.inventory_lot_id == lot.id
    assert item.quantity == 3
    assert item.unit_cost_snapshot == Money(
        "5", refund_account.currency
    )
    assert item.cost == Money("15", refund_account.currency)

    assert len(returned.movements) == 1
    movement = returned.movements[0]
    assert movement.movement_type is InventoryMovementType.SUPPLIER_RETURN
    assert movement.quantity == -3
    assert movement.inventory_lot_id == lot.id
    assert movement.unit_cost == Money("5", refund_account.currency)
    assert movement.reference_type == "SUPPLIER_RETURN"
    assert movement.reference_id == returned.supplier_return.id

    assert _stock(db_session, variant.id) == 7

    assert returned.refund is not None
    assert (
        returned.refund.transaction_type
        is FinancialTransactionType.SUPPLIER_REFUND
    )
    assert returned.refund.amount == Money(
        "15", refund_account.currency
    )
    assert (
        returned.refund.supplier_return_id
        == returned.supplier_return.id
    )
    assert returned.refund.purchase_id is None
    assert returned.refund.sale_id is None

    assert [
        (entry.transaction_type, entry.amount)
        for entry in _entries(db_session, refund_account)
    ] == [
        (
            FinancialTransactionType.SUPPLIER_REFUND,
            Money("15", refund_account.currency),
        )
    ]
    assert SqlAlchemyFinancialTransactionRepository(
        db_session
    ).get_balance(refund_account) == Money(
        "15", refund_account.currency
    )

    stored_purchase = SqlAlchemyPurchaseRepository(db_session).get_by_id(
        registered.purchase.id
    )
    assert stored_purchase is not None
    assert stored_purchase.status is PurchaseStatus.RECEIVED
    stored_item = SqlAlchemyPurchaseItemRepository(
        db_session
    ).get_by_id(registered.items[0].id)
    assert stored_item is not None
    assert stored_item.quantity == 10
    assert stored_item.unit_price == Money(
        "5", purchase_account.currency
    )

    stored_lot = SqlAlchemyInventoryLotRepository(db_session).get_by_id(
        lot.id
    )
    assert stored_lot is not None
    assert stored_lot.acquired_quantity == 10
    assert stored_lot.remaining_quantity == 7
    assert stored_lot.unit_cost == Money("5", purchase_account.currency)

    stored_return = SqlAlchemySupplierReturnRepository(
        db_session
    ).get_by_id(returned.supplier_return.id)
    assert stored_return is not None
    assert stored_return.refund_amount == Money(
        "15", refund_account.currency
    )
    assert SqlAlchemySupplierReturnRepository(
        db_session
    ).list_for_purchase(registered.purchase.id) == [stored_return]
    assert [
        stored.id
        for stored in SqlAlchemySupplierReturnItemRepository(
            db_session
        ).list_for_purchase(registered.purchase.id)
    ] == [item.id]

    movements = SqlAlchemyInventoryMovementRepository(
        db_session
    ).list_by_variant(variant.id)
    assert [entry.movement_type for entry in movements] == [
        InventoryMovementType.PURCHASE_RECEIVED,
        InventoryMovementType.SUPPLIER_RETURN,
    ]
    assert [
        entry.transaction_type
        for entry in _entries(db_session, purchase_account)
    ] == [FinancialTransactionType.PURCHASE]


def test_partial_returns_preserve_the_historical_lot_cost(db_session) -> None:
    variant = _variant(db_session)
    currency = _currency(db_session)
    registered, _ = _purchase(
        db_session,
        variant_id=variant.id,
        quantity=10,
        price="5.00",
        costs=(
            PurchaseCostRequest(
                cost_type=PurchaseCostType.SHIPPING,
                amount=Money("20", currency),
                allocation_method=AllocationMethod.BY_QUANTITY,
            ),
        ),
    )
    lot = _lots(db_session, registered.purchase.id)[0]
    assert lot.unit_cost == Money("7", currency)

    first = _return(
        db_session,
        registered.purchase,
        [_return_item(registered.items[0], lot, 2)],
    )

    assert first.items[0].unit_cost_snapshot == Money("7", currency)
    assert first.items[0].cost == Money("14", currency)
    assert first.movements[0].unit_cost == Money("7", currency)
    assert _stock(db_session, variant.id) == 8

    second = _return(
        db_session,
        registered.purchase,
        [_return_item(registered.items[0], lot, 3)],
        return_date=LATER_STILL,
    )

    assert second.items[0].unit_cost_snapshot == Money("7", currency)
    assert second.movements[0].unit_cost == Money("7", currency)
    assert _stock(db_session, variant.id) == 5
    assert len(
        SqlAlchemySupplierReturnRepository(db_session).list_for_purchase(
            registered.purchase.id
        )
    ) == 2


def test_wrong_lot_return_is_rejected_before_writing(db_session) -> None:
    variant = _variant(db_session)
    first, _ = _purchase(
        db_session,
        variant_id=variant.id,
        quantity=10,
        price="5.00",
    )
    second, _ = _purchase(
        db_session,
        variant_id=variant.id,
        quantity=10,
        price="6.00",
        received_at=LATER,
    )
    first_lot = _lots(db_session, first.purchase.id)[0]
    second_lot = _lots(db_session, second.purchase.id)[0]

    with pytest.raises(InvalidSupplierReturnError):
        _return(
            db_session,
            first.purchase,
            [_return_item(first.items[0], second_lot, 1)],
        )

    with pytest.raises(InvalidSupplierReturnError):
        _return(
            db_session,
            first.purchase,
            [_return_item(second.items[0], first_lot, 1)],
        )

    assert SqlAlchemySupplierReturnRepository(db_session).list_all() == []
    assert _stock(db_session, variant.id) == 20


def test_excess_return_is_rejected_before_writing(db_session) -> None:
    variant = _variant(db_session)
    registered, _ = _purchase(
        db_session,
        variant_id=variant.id,
        quantity=10,
        price="5.00",
    )
    lot = _lots(db_session, registered.purchase.id)[0]

    with pytest.raises(ExcessSupplierReturnError):
        _return(
            db_session,
            registered.purchase,
            [_return_item(registered.items[0], lot, 11)],
        )

    first = _return(
        db_session,
        registered.purchase,
        [_return_item(registered.items[0], lot, 4)],
    )
    assert first.supplier_return.id is not None
    assert _stock(db_session, variant.id) == 6

    with pytest.raises(ExcessSupplierReturnError):
        _return(
            db_session,
            registered.purchase,
            [_return_item(registered.items[0], lot, 7)],
            return_date=LATER_STILL,
        )

    with pytest.raises(ExcessSupplierReturnError):
        _return(
            db_session,
            registered.purchase,
            [
                _return_item(registered.items[0], lot, 4),
                _return_item(registered.items[0], lot, 3),
            ],
            return_date=LATER_STILL,
        )

    assert len(
        SqlAlchemySupplierReturnRepository(db_session).list_all()
    ) == 1
    assert _stock(db_session, variant.id) == 6


def test_supplier_refund_requires_a_matching_active_account(
    db_session,
) -> None:
    variant = _variant(db_session)
    registered, _ = _purchase(
        db_session,
        variant_id=variant.id,
        quantity=10,
        price="5.00",
    )
    lot = _lots(db_session, registered.purchase.id)[0]
    usd_account = _account(db_session, "USD", name="Refunds")
    eur_account = _account(db_session, "EUR")
    inactive_account = _account(
        db_session, "USD", name="Closed", active=False
    )
    item = _return_item(registered.items[0], lot, 1)

    with pytest.raises(InvalidSupplierReturnError):
        _return(
            db_session,
            registered.purchase,
            [item],
            refund=Money("5", usd_account.currency),
        )
    with pytest.raises(InvalidSupplierReturnError):
        _return(
            db_session,
            registered.purchase,
            [item],
            account=usd_account,
        )
    with pytest.raises(InactiveAccountError):
        _return(
            db_session,
            registered.purchase,
            [item],
            account=inactive_account,
            refund=Money("5", usd_account.currency),
        )
    with pytest.raises(AccountCurrencyMismatchError):
        _return(
            db_session,
            registered.purchase,
            [item],
            account=eur_account,
            refund=Money("5", usd_account.currency),
        )
    with pytest.raises(PurchaseCurrencyMismatchError):
        _return(
            db_session,
            registered.purchase,
            [item],
            account=usd_account,
            refund=Money("5", eur_account.currency),
        )
    for amount in ("0", "-1"):
        with pytest.raises(SupplierRefundError):
            _return(
                db_session,
                registered.purchase,
                [item],
                account=usd_account,
                refund=Money(amount, usd_account.currency),
            )

    assert SqlAlchemySupplierReturnRepository(db_session).list_all() == []
    assert _stock(db_session, variant.id) == 10


def test_supplier_return_without_refund_still_removes_stock(
    db_session,
) -> None:
    variant = _variant(db_session)
    registered, purchase_account = _purchase(
        db_session,
        variant_id=variant.id,
        quantity=5,
        price="8.00",
    )
    lot = _lots(db_session, registered.purchase.id)[0]

    returned = _return(
        db_session,
        registered.purchase,
        [_return_item(registered.items[0], lot, 2)],
    )

    assert returned.supplier_return.supplier_id is None
    assert returned.supplier_return.account_id is None
    assert returned.supplier_return.refund_amount is None
    assert returned.refund is None
    assert returned.movements[0].quantity == -2
    assert _stock(db_session, variant.id) == 3
    assert [
        entry.transaction_type
        for entry in _entries(db_session, purchase_account)
    ] == [FinancialTransactionType.PURCHASE]


def test_empty_and_unknown_references_are_rejected(db_session) -> None:
    variant = _variant(db_session)
    registered, _ = _purchase(
        db_session,
        variant_id=variant.id,
        quantity=10,
        price="5.00",
    )
    lot = _lots(db_session, registered.purchase.id)[0]

    with pytest.raises(InvalidSupplierReturnError):
        _return(db_session, registered.purchase, [])

    with pytest.raises(PurchaseNotFoundError):
        _return(
            db_session,
            replace(registered.purchase, id=9999),
            [_return_item(registered.items[0], lot, 1)],
        )

    with pytest.raises(PurchaseItemNotFoundError):
        _return(
            db_session,
            registered.purchase,
            [
                SupplierReturnItemRequest(
                    purchase_item_id=9999,
                    inventory_lot_id=lot.id,
                    quantity=1,
                )
            ],
        )

    with pytest.raises(InventoryLotNotFoundError):
        _return(
            db_session,
            registered.purchase,
            [
                SupplierReturnItemRequest(
                    purchase_item_id=registered.items[0].id,
                    inventory_lot_id=9999,
                    quantity=1,
                )
            ],
        )

    assert SqlAlchemySupplierReturnRepository(db_session).list_all() == []
    assert _stock(db_session, variant.id) == 10


def test_return_uses_only_the_referenced_lot(db_session) -> None:
    variant = _variant(db_session)
    registered, _ = _purchase(
        db_session,
        variant_id=variant.id,
        quantity=10,
        price="5.00",
        receipt_quantities=(4, 6),
    )
    first_lot, second_lot = _lots(
        db_session, registered.purchase.id
    )

    returned = _return(
        db_session,
        registered.purchase,
        [_return_item(registered.items[0], second_lot, 2)],
    )

    assert returned.items[0].inventory_lot_id == second_lot.id
    assert returned.movements[0].inventory_lot_id == second_lot.id
    stored_first = SqlAlchemyInventoryLotRepository(
        db_session
    ).get_by_id(first_lot.id)
    stored_second = SqlAlchemyInventoryLotRepository(
        db_session
    ).get_by_id(second_lot.id)
    assert stored_first is not None
    assert stored_second is not None
    assert stored_first.remaining_quantity == 4
    assert stored_second.remaining_quantity == 4
    assert _stock(db_session, variant.id) == 8


def test_partial_supplier_refunds_accumulate(db_session) -> None:
    variant = _variant(db_session)
    registered, _ = _purchase(
        db_session,
        variant_id=variant.id,
        quantity=10,
        price="5.00",
    )
    lot = _lots(db_session, registered.purchase.id)[0]
    account = _account(db_session, "USD", name="Refunds")

    first = _return(
        db_session,
        registered.purchase,
        [_return_item(registered.items[0], lot, 2)],
        account=account,
        refund=Money("10", account.currency),
    )
    assert first.total_refunded == Money("10", account.currency)

    second = _return(
        db_session,
        registered.purchase,
        [_return_item(registered.items[0], lot, 3)],
        account=account,
        refund=Money("15", account.currency),
        return_date=LATER_STILL,
    )

    assert second.total_refunded == Money("25", account.currency)
    assert SqlAlchemyFinancialTransactionRepository(
        db_session
    ).get_balance(account) == Money("25", account.currency)
    assert _stock(db_session, variant.id) == 5


def test_historical_return_can_map_an_inactive_refund_account(
    db_session,
) -> None:
    variant = _variant(db_session)
    registered, _ = _purchase(
        db_session,
        variant_id=variant.id,
        quantity=10,
        price="5.00",
    )
    lot = _lots(db_session, registered.purchase.id)[0]
    account = _account(db_session, "USD", name="Refunds")

    returned = _return(
        db_session,
        registered.purchase,
        [_return_item(registered.items[0], lot, 1)],
        account=account,
        refund=Money("5", account.currency),
    )
    deactivated = SqlAlchemyAccountRepository(db_session).save(
        replace(account, is_active=False)
    )

    stored_return = SqlAlchemySupplierReturnRepository(
        db_session
    ).get_by_id(returned.supplier_return.id)
    assert stored_return is not None
    assert stored_return.account is not None
    assert stored_return.account.id == deactivated.id
    assert stored_return.account.is_active is False
