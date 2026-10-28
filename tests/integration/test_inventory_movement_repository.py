"""Inventory movement repository against a migrated SQLite database."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.domain.entities.currency import Currency
from app.domain.entities.inventory_lot import InventoryLot
from app.domain.entities.inventory_movement import InventoryMovement
from app.domain.entities.product import Product
from app.domain.entities.product_variant import ProductVariant
from app.domain.entities.purchase import Purchase
from app.domain.entities.purchase_item import PurchaseItem
from app.domain.enums.inventory_movement_type import InventoryMovementType
from app.domain.exceptions import (
    InventoryLotNotFoundError,
    InvalidInventoryMovementError,
)
from app.domain.value_objects.money import Money
from app.infrastructure.database.repositories import (
    SqlAlchemyCurrencyRepository,
    SqlAlchemyInventoryLotRepository,
    SqlAlchemyInventoryMovementRepository,
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


def _purchase_item(db_session, variant_id: int) -> PurchaseItem:
    currency = _currency(db_session)
    purchase = SqlAlchemyPurchaseRepository(db_session).add(
        Purchase(currency=currency, purchase_date=NOW)
    )
    return SqlAlchemyPurchaseItemRepository(db_session).add(
        PurchaseItem(
            purchase=purchase,
            variant_id=variant_id,
            quantity=10,
            unit_price=Money("5", currency),
        )
    )


def _lot(db_session, item: PurchaseItem) -> InventoryLot:
    return SqlAlchemyInventoryLotRepository(db_session).add(
        InventoryLot(
            purchase_item=item,
            variant_id=item.variant_id,
            acquired_quantity=10,
            remaining_quantity=10,
            unit_cost=Money("5", item.purchase.currency),
            received_at=NOW,
        )
    )


def _movement(
    variant_id: int,
    *,
    lot_id: int | None = None,
    movement_type: InventoryMovementType = (
        InventoryMovementType.PURCHASE_RECEIVED
    ),
    quantity: int = 5,
    movement_date: datetime = NOW,
) -> InventoryMovement:
    return InventoryMovement(
        variant_id=variant_id,
        movement_type=movement_type,
        quantity=quantity,
        movement_date=movement_date,
        inventory_lot_id=lot_id,
        unit_cost=Money("5", _USD),
        reference_type="PURCHASE",
        reference_id=1,
        notes="Receipt",
    )


_USD = Currency(code="USD", name="US Dollar", decimal_places=2, id=1)


def test_movement_repository_round_trip(db_session) -> None:
    variant = _variant(db_session)
    lot = _lot(db_session, _purchase_item(db_session, variant.id))
    repository = SqlAlchemyInventoryMovementRepository(db_session)

    stored = repository.add(_movement(variant.id, lot_id=lot.id))

    assert stored.id is not None
    assert repository.get_by_id(stored.id) == stored
    assert repository.list_for_lot(lot.id) == [stored]
    assert repository.list_by_variant(variant.id) == [stored]


def test_movements_are_listed_chronologically(db_session) -> None:
    variant = _variant(db_session)
    lot = _lot(db_session, _purchase_item(db_session, variant.id))
    repository = SqlAlchemyInventoryMovementRepository(db_session)
    earlier = repository.add(_movement(variant.id, lot_id=lot.id))
    later = repository.add(
        _movement(variant.id, lot_id=lot.id, movement_date=LATER)
    )

    assert repository.list_by_variant(variant.id) == [earlier, later]
    assert repository.list_for_lot(lot.id) == [earlier, later]


def test_movement_without_lot_or_cost_is_allowed(db_session) -> None:
    variant = _variant(db_session)
    repository = SqlAlchemyInventoryMovementRepository(db_session)

    stored = repository.add(
        InventoryMovement(
            variant_id=variant.id,
            movement_type=InventoryMovementType.SALE,
            quantity=-1,
            movement_date=NOW,
        )
    )

    loaded = repository.get_by_id(stored.id)
    assert loaded is not None
    assert loaded.inventory_lot_id is None
    assert loaded.unit_cost is None


def test_movement_rejects_an_unknown_lot(db_session) -> None:
    variant = _variant(db_session)
    repository = SqlAlchemyInventoryMovementRepository(db_session)

    with pytest.raises(InventoryLotNotFoundError):
        repository.add(_movement(variant.id, lot_id=999))


def test_movement_variant_must_match_its_lot(db_session) -> None:
    first_variant = _variant(db_session, "Phone")
    second_variant = _variant(db_session, "Tablet")
    lot = _lot(db_session, _purchase_item(db_session, second_variant.id))
    repository = SqlAlchemyInventoryMovementRepository(db_session)

    with pytest.raises(InvalidInventoryMovementError):
        repository.add(
            _movement(first_variant.id, lot_id=lot.id)
        )
