"""Receive-purchase use cases against a migrated SQLite database."""

from __future__ import annotations

from datetime import UTC, datetime

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
from app.domain.entities.account import Account
from app.domain.entities.currency import Currency
from app.domain.entities.product import Product
from app.domain.entities.product_variant import ProductVariant
from app.domain.enums.allocation_method import AllocationMethod
from app.domain.enums.inventory_movement_type import InventoryMovementType
from app.domain.enums.purchase_cost_type import PurchaseCostType
from app.domain.enums.purchase_status import PurchaseStatus
from app.domain.exceptions import (
    InvalidInventoryError,
    InvalidPurchaseTransitionError,
    OverReceiptError,
    PurchaseItemNotFoundError,
    VariantNotFoundError,
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
)

NOW = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)


def _currency(db_session, code: str = "USD") -> Currency:
    currency = SqlAlchemyCurrencyRepository(db_session).get_by_code(code)
    assert currency is not None
    return currency


def _account(db_session, name: str = "Cash USD") -> Account:
    return SqlAlchemyAccountRepository(db_session).add(
        Account(name=name, currency=_currency(db_session))
    )


def _variant(db_session, name: str = "Phone") -> ProductVariant:
    product = SqlAlchemyProductRepository(db_session).add(
        Product(name=name)
    )
    return SqlAlchemyProductVariantRepository(db_session).add(
        ProductVariant(product_id=product.id, variant_name=name)
    )


def _register(
    db_session,
    *,
    item_specs: tuple[tuple[int, int, str], ...] | None = None,
    quantity: int = 10,
    price: str = "5.00",
    paid: bool = True,
    costs: tuple[PurchaseCostRequest, ...] = (),
):
    currency = _currency(db_session)
    if item_specs is None:
        item_specs = ((_variant(db_session).id, quantity, price),)

    service = RegisterPurchase(
        accounts=SqlAlchemyAccountRepository(db_session),
        purchases=SqlAlchemyPurchaseRepository(db_session),
        items=SqlAlchemyPurchaseItemRepository(db_session),
        costs=SqlAlchemyPurchaseCostRepository(db_session),
        allocations=SqlAlchemyPurchaseCostAllocationRepository(
            db_session
        ),
        exchange_rates=SqlAlchemyExchangeRateRepository(db_session),
        transactions=SqlAlchemyFinancialTransactionRepository(
            db_session
        ),
    )
    return service.execute(
        RegisterPurchaseRequest(
            currency=currency,
            purchase_date=NOW,
            items=tuple(
                PurchaseItemRequest(
                    variant_id=variant_id,
                    quantity=item_quantity,
                    unit_price=Money(item_price, currency),
                )
                for variant_id, item_quantity, item_price in item_specs
            ),
            costs=costs,
            account_id=(
                _account(db_session).id if paid else None
            ),
        )
    )


def _in_transit(db_session, registered):
    purchases = SqlAlchemyPurchaseRepository(db_session)
    service = UpdatePurchaseStatus(purchases)
    service.execute(
        UpdatePurchaseStatusRequest(
            registered.purchase.id, PurchaseStatus.SHIPPED
        )
    )
    service.execute(
        UpdatePurchaseStatusRequest(
            registered.purchase.id, PurchaseStatus.IN_TRANSIT
        )
    )
    return purchases.get_by_id(registered.purchase.id)


def _receive(
    db_session,
    request: ReceivePurchaseRequest,
):
    service = ReceivePurchase(
        purchases=SqlAlchemyPurchaseRepository(db_session),
        items=SqlAlchemyPurchaseItemRepository(db_session),
        allocations=SqlAlchemyPurchaseCostAllocationRepository(
            db_session
        ),
        lots=SqlAlchemyInventoryLotRepository(db_session),
        movements=SqlAlchemyInventoryMovementRepository(db_session),
    )
    return service.execute(request)


def _request(
    registered,
    item_id: int,
    quantity: int,
    *,
    notes: str | None = None,
) -> ReceivePurchaseRequest:
    return ReceivePurchaseRequest(
        purchase_id=registered.purchase.id,
        items=(ReceiptItemRequest(item_id, quantity),),
        received_at=NOW,
        notes=notes,
    )


def _lots(db_session) -> SqlAlchemyInventoryLotRepository:
    return SqlAlchemyInventoryLotRepository(db_session)


def _stock(db_session) -> GetVariantStock:
    return GetVariantStock(
        SqlAlchemyProductVariantRepository(db_session),
        SqlAlchemyInventoryLotRepository(db_session),
    )


def test_partial_receipt_creates_a_lot_movement_and_stock(db_session) -> None:
    registered = _register(db_session)
    _in_transit(db_session, registered)
    item = registered.items[0]
    assert item.id is not None

    result = _receive(
        db_session,
        _request(registered, item.id, 4, notes="  First box "),
    )

    assert result.purchase.status is PurchaseStatus.PARTIALLY_RECEIVED
    lot = result.lots[0]
    assert lot.acquired_quantity == 4
    assert lot.remaining_quantity == 4
    assert lot.unit_cost == Money("5", _currency(db_session))
    assert lot.received_at == NOW

    movement = result.movements[0]
    assert movement.movement_type is InventoryMovementType.PURCHASE_RECEIVED
    assert movement.quantity == 4
    assert movement.inventory_lot_id == lot.id
    assert movement.unit_cost == lot.unit_cost
    assert movement.reference_type == "PURCHASE"
    assert movement.reference_id == registered.purchase.id
    assert movement.notes == "First box"

    stock = _stock(db_session).execute(item.variant_id)
    assert stock.quantity == 4


def test_lot_unit_cost_includes_allocated_purchase_costs(db_session) -> None:
    registered = _register(
        db_session,
        costs=(
            PurchaseCostRequest(
                cost_type=PurchaseCostType.SHIPPING,
                amount=Money("10", _currency(db_session)),
                allocation_method=AllocationMethod.BY_QUANTITY,
            ),
        ),
    )
    _in_transit(db_session, registered)
    item = registered.items[0]
    assert item.id is not None

    result = _receive(db_session, _request(registered, item.id, 4))

    assert result.lots[0].unit_cost == Money("6", _currency(db_session))


def test_multiple_receipts_complete_the_purchase(db_session) -> None:
    registered = _register(db_session)
    _in_transit(db_session, registered)
    item = registered.items[0]
    assert item.id is not None

    first = _receive(db_session, _request(registered, item.id, 4))
    second = _receive(db_session, _request(registered, item.id, 6))

    assert first.purchase.status is PurchaseStatus.PARTIALLY_RECEIVED
    assert second.purchase.status is PurchaseStatus.RECEIVED
    assert [
        lot.acquired_quantity
        for lot in _lots(db_session).list_by_variant(item.variant_id)
    ] == [4, 6]
    assert [
        movement.quantity
        for movement in SqlAlchemyInventoryMovementRepository(
            db_session
        ).list_by_variant(item.variant_id)
    ] == [4, 6]
    assert (
        _stock(db_session)
        .execute(item.variant_id)
        .quantity
        == 10
    )


def test_over_receipt_is_rejected_without_writing_anything(
    db_session,
) -> None:
    registered = _register(db_session)
    _in_transit(db_session, registered)
    item = registered.items[0]
    assert item.id is not None

    with pytest.raises(OverReceiptError):
        _receive(db_session, _request(registered, item.id, 11))

    assert _lots(db_session).list_for_purchase(
        registered.purchase.id
    ) == []
    purchase = SqlAlchemyPurchaseRepository(db_session).get_by_id(
        registered.purchase.id
    )
    assert purchase is not None
    assert purchase.status is PurchaseStatus.IN_TRANSIT

    _receive(db_session, _request(registered, item.id, 4))
    with pytest.raises(OverReceiptError):
        _receive(db_session, _request(registered, item.id, 7))

    assert (
        _stock(db_session)
        .execute(item.variant_id)
        .quantity
        == 4
    )
    assert len(
        _lots(db_session).list_for_purchase(registered.purchase.id)
    ) == 1


def test_duplicate_item_in_one_receipt_is_rejected(db_session) -> None:
    registered = _register(db_session)
    _in_transit(db_session, registered)
    item = registered.items[0]
    assert item.id is not None

    request = ReceivePurchaseRequest(
        purchase_id=registered.purchase.id,
        items=(
            ReceiptItemRequest(item.id, 2),
            ReceiptItemRequest(item.id, 3),
        ),
        received_at=NOW,
    )

    with pytest.raises(InvalidInventoryError):
        _receive(db_session, request)

    assert _lots(db_session).list_for_purchase(
        registered.purchase.id
    ) == []


def test_unknown_purchase_item_is_rejected(db_session) -> None:
    registered = _register(db_session)
    _in_transit(db_session, registered)

    with pytest.raises(PurchaseItemNotFoundError):
        _receive(db_session, _request(registered, 9999, 1))


def test_unpaid_purchase_cannot_be_received(db_session) -> None:
    registered = _register(db_session, paid=False)

    with pytest.raises(InvalidPurchaseTransitionError):
        _receive(
            db_session,
            _request(registered, registered.items[0].id, 1),
        )

    assert _lots(db_session).list_for_purchase(
        registered.purchase.id
    ) == []


def test_receipt_before_in_transit_is_rejected(db_session) -> None:
    registered = _register(db_session)

    with pytest.raises(InvalidPurchaseTransitionError):
        _receive(
            db_session,
            _request(registered, registered.items[0].id, 1),
        )


def test_partial_status_tracks_every_item(db_session) -> None:
    first_variant = _variant(db_session, "Phone")
    second_variant = _variant(db_session, "Tablet")
    registered = _register(
        db_session,
        item_specs=(
            (first_variant.id, 10, "5.00"),
            (second_variant.id, 4, "2.00"),
        ),
    )
    _in_transit(db_session, registered)
    first_item, second_item = registered.items
    assert first_item.id is not None
    assert second_item.id is not None

    first = _receive(
        db_session, _request(registered, first_item.id, 10)
    )
    second = _receive(
        db_session, _request(registered, second_item.id, 4)
    )

    assert first.purchase.status is PurchaseStatus.PARTIALLY_RECEIVED
    assert second.purchase.status is PurchaseStatus.RECEIVED


def test_stock_query_returns_zero_and_rejects_invalid_ids(db_session) -> None:
    variant = _variant(db_session)
    service = _stock(db_session)

    assert service.execute(variant.id).quantity == 0
    for variant_id in (0, -1, True, "1"):
        with pytest.raises(InvalidInventoryError):
            service.execute(variant_id)
    with pytest.raises(VariantNotFoundError):
        service.execute(999)
