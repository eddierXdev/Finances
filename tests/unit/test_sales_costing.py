"""Revenue, COGS and gross-profit rules."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.domain.entities.account import Account
from app.domain.entities.currency import Currency
from app.domain.entities.inventory_lot import InventoryLot
from app.domain.entities.purchase import Purchase
from app.domain.entities.purchase_item import PurchaseItem
from app.domain.entities.sale import Sale
from app.domain.entities.sale_item import SaleItem
from app.domain.entities.sale_item_lot_allocation import (
    SaleItemLotAllocation,
)
from app.domain.exceptions import (
    CurrencyMismatchError,
    InvalidSaleError,
)
from app.domain.sales_costing import (
    sale_cogs,
    sale_cogs_by_currency,
    sale_gross_profit,
    sale_revenue,
)
from app.domain.value_objects.money import Money

USD = Currency(code="USD", name="US Dollar", decimal_places=2, id=1)
EUR = Currency(code="EUR", name="Euro", decimal_places=2, id=2)
NOW = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)

SALE = Sale(
    account=Account(name="Cash USD", currency=USD, id=1),
    currency=USD,
    sale_date=NOW,
    id=1,
)
OTHER_SALE = Sale(
    account=Account(name="Cash USD", currency=USD, id=1),
    currency=USD,
    sale_date=NOW,
    id=2,
)
ITEM = SaleItem(
    sale=SALE,
    variant_id=7,
    quantity=2,
    unit_price=Money("10", USD),
    discount_amount=Money("1", USD),
    id=20,
)
OTHER_ITEM = SaleItem(
    sale=OTHER_SALE,
    variant_id=8,
    quantity=1,
    unit_price=Money("5", USD),
    id=21,
)
PURCHASE = Purchase(currency=USD, purchase_date=NOW, id=10)
PURCHASE_ITEM = PurchaseItem(
    purchase=PURCHASE,
    variant_id=7,
    quantity=10,
    unit_price=Money("5", USD),
    id=30,
)
LOT = InventoryLot(
    purchase_item=PURCHASE_ITEM,
    variant_id=7,
    acquired_quantity=10,
    remaining_quantity=8,
    unit_cost=Money("5", USD),
    received_at=NOW,
    id=40,
)
ALLOCATION = SaleItemLotAllocation(
    sale_item=ITEM,
    inventory_lot=LOT,
    quantity=2,
    unit_cost_snapshot=Money("5", USD),
    id=50,
)


def test_revenue_subtracts_item_and_sale_discounts() -> None:
    assert sale_revenue(SALE, [ITEM]) == Money("19", USD)

    discounted_sale = Sale(
        account=Account(name="Cash USD", currency=USD, id=1),
        currency=USD,
        sale_date=NOW,
        discount_amount=Money("4", USD),
        id=3,
    )
    discounted_item = SaleItem(
        sale=discounted_sale,
        variant_id=7,
        quantity=2,
        unit_price=Money("10", USD),
        id=22,
    )

    assert sale_revenue(discounted_sale, [discounted_item]) == Money(
        "16", USD
    )


def test_sale_discount_cannot_exceed_the_item_subtotal() -> None:
    sale = Sale(
        account=Account(name="Cash USD", currency=USD, id=1),
        currency=USD,
        sale_date=NOW,
        discount_amount=Money("25", USD),
        id=4,
    )
    item = SaleItem(
        sale=sale,
        variant_id=7,
        quantity=2,
        unit_price=Money("10", USD),
        id=23,
    )

    with pytest.raises(InvalidSaleError):
        sale_revenue(sale, [item])


def test_all_items_must_belong_to_the_sale_being_costed() -> None:
    with pytest.raises(InvalidSaleError):
        sale_revenue(SALE, [OTHER_ITEM])


def test_cogs_sums_historical_allocations() -> None:
    second_lot = InventoryLot(
        purchase_item=PURCHASE_ITEM,
        variant_id=7,
        acquired_quantity=5,
        remaining_quantity=3,
        unit_cost=Money("7", USD),
        received_at=NOW,
        id=41,
    )
    second_allocation = SaleItemLotAllocation(
        sale_item=ITEM,
        inventory_lot=second_lot,
        quantity=1,
        unit_cost_snapshot=Money("7", USD),
        id=51,
    )

    assert sale_cogs([ALLOCATION, second_allocation]) == Money("17", USD)


def test_gross_profit_is_revenue_minus_cogs() -> None:
    assert sale_gross_profit(SALE, [ITEM], [ALLOCATION]) == Money("9", USD)


def test_cogs_requires_at_least_one_allocation() -> None:
    with pytest.raises(InvalidSaleError):
        sale_cogs([])


def test_cross_currency_cogs_and_profit_require_explicit_conversion() -> None:
    eur_purchase = Purchase(currency=EUR, purchase_date=NOW, id=11)
    eur_item = PurchaseItem(
        purchase=eur_purchase,
        variant_id=7,
        quantity=2,
        unit_price=Money("4", EUR),
        id=31,
    )
    eur_lot = InventoryLot(
        purchase_item=eur_item,
        variant_id=7,
        acquired_quantity=2,
        remaining_quantity=2,
        unit_cost=Money("4", EUR),
        received_at=NOW,
        id=42,
    )
    eur_allocation = SaleItemLotAllocation(
        sale_item=ITEM,
        inventory_lot=eur_lot,
        quantity=2,
        unit_cost_snapshot=Money("4", EUR),
        id=52,
    )

    assert sale_cogs([eur_allocation]) == Money("8", EUR)
    assert sale_cogs_by_currency([ALLOCATION, eur_allocation]) == (
        Money("8", EUR),
        Money("10", USD),
    )
    with pytest.raises(CurrencyMismatchError):
        sale_cogs([ALLOCATION, eur_allocation])
    with pytest.raises(CurrencyMismatchError):
        sale_gross_profit(SALE, [ITEM], [eur_allocation])
