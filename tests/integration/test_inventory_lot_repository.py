"""Inventory lot repository against a migrated SQLite database."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from app.domain.entities.currency import Currency
from app.domain.entities.inventory_lot import InventoryLot
from app.domain.entities.product import Product
from app.domain.entities.product_variant import ProductVariant
from app.domain.entities.purchase import Purchase
from app.domain.entities.purchase_item import PurchaseItem
from app.domain.exceptions import (
    InventoryLotNotFoundError,
    PurchaseItemNotFoundError,
)
from app.domain.value_objects.money import Money
from app.infrastructure.database.repositories import (
    SqlAlchemyCurrencyRepository,
    SqlAlchemyInventoryLotRepository,
    SqlAlchemyProductRepository,
    SqlAlchemyProductVariantRepository,
    SqlAlchemyPurchaseItemRepository,
    SqlAlchemyPurchaseRepository,
)

NOW = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)
LATER = NOW + timedelta(hours=1)


def _currency(db_session, code: str = "USD") -> Currency:
    currency = SqlAlchemyCurrencyRepository(db_session).get_by_code(code)
    assert currency is not None
    return currency


def _variant(db_session, name: str = "Phone") -> ProductVariant:
    product = SqlAlchemyProductRepository(db_session).add(
        Product(name=name)
    )
    return SqlAlchemyProductVariantRepository(db_session).add(
        ProductVariant(product_id=product.id, variant_name=name)
    )


def _purchase_item(
    db_session,
    *,
    variant_id: int | None = None,
    quantity: int = 10,
    price: str = "5.00",
) -> PurchaseItem:
    currency = _currency(db_session)
    purchase = SqlAlchemyPurchaseRepository(db_session).add(
        Purchase(currency=currency, purchase_date=NOW)
    )
    return SqlAlchemyPurchaseItemRepository(db_session).add(
        PurchaseItem(
            purchase=purchase,
            variant_id=(
                variant_id
                if variant_id is not None
                else _variant(db_session).id
            ),
            quantity=quantity,
            unit_price=Money(price, currency),
        )
    )


def _lot(
    item: PurchaseItem,
    *,
    quantity: int = 10,
    received_at: datetime = NOW,
) -> InventoryLot:
    return InventoryLot(
        purchase_item=item,
        variant_id=item.variant_id,
        acquired_quantity=quantity,
        remaining_quantity=quantity,
        unit_cost=Money("5", item.purchase.currency),
        received_at=received_at,
    )


def test_lot_repository_round_trip(db_session) -> None:
    item = _purchase_item(db_session)
    repository = SqlAlchemyInventoryLotRepository(db_session)

    stored = repository.add(_lot(item))

    assert stored.id is not None
    loaded = repository.get_by_id(stored.id)
    assert loaded == stored
    assert loaded is not None
    assert loaded.purchase_item_id == item.id
    assert loaded.remaining_quantity == 10


def test_save_only_updates_remaining_quantity(db_session) -> None:
    item = _purchase_item(db_session)
    repository = SqlAlchemyInventoryLotRepository(db_session)
    stored = repository.add(_lot(item))

    consumed = repository.save(stored.consume(3))

    assert consumed.remaining_quantity == 7
    with pytest.raises(ValueError):
        repository.save(replace(stored, acquired_quantity=11))
    with pytest.raises(InventoryLotNotFoundError):
        repository.save(replace(stored, id=999))


def test_lots_are_listed_in_fifo_order_and_available_lots_exclude_empty(
    db_session,
) -> None:
    item = _purchase_item(db_session)
    repository = SqlAlchemyInventoryLotRepository(db_session)
    older = repository.add(_lot(item, received_at=NOW))
    newer = repository.add(_lot(item, quantity=5, received_at=LATER))

    assert repository.list_by_variant(item.variant_id) == [older, newer]

    repository.save(older.consume(older.remaining_quantity))

    assert repository.list_available_by_variant(item.variant_id) == [newer]
    assert repository.total_remaining_by_variant(item.variant_id) == 5

    for_purchase_item = repository.list_for_purchase_item(item.id)
    for_purchase = repository.list_for_purchase(item.purchase.id)
    assert [lot.remaining_quantity for lot in for_purchase_item] == [0, 5]
    assert [lot.remaining_quantity for lot in for_purchase] == [0, 5]


def test_stock_is_zero_when_the_variant_has_no_lots(db_session) -> None:
    variant = _variant(db_session)

    repository = SqlAlchemyInventoryLotRepository(db_session)

    assert repository.list_by_variant(variant.id) == []
    assert repository.list_available_by_variant(variant.id) == []
    assert repository.total_remaining_by_variant(variant.id) == 0


def test_add_rejects_an_unknown_purchase_item(db_session) -> None:
    item = _purchase_item(db_session)
    repository = SqlAlchemyInventoryLotRepository(db_session)

    with pytest.raises(PurchaseItemNotFoundError):
        repository.add(_lot(replace(item, id=999)))
