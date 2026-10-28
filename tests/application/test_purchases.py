"""Purchase application use cases against a migrated SQLite database."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.application.finances import GetAccountBalance
from app.application.purchases import (
    PurchaseCostRequest,
    PurchaseItemRequest,
    RegisterPurchase,
    RegisterPurchasePayment,
    RegisterPurchasePaymentRequest,
    RegisterPurchaseRequest,
    UpdatePurchaseStatus,
    UpdatePurchaseStatusRequest,
)
from app.application.suppliers import CreateSupplier, CreateSupplierRequest
from app.domain.entities.account import Account
from app.domain.entities.currency import Currency
from app.domain.entities.exchange_rate import ExchangeRate
from app.domain.entities.product import Product
from app.domain.entities.product_variant import ProductVariant
from app.domain.enums.allocation_method import AllocationMethod
from app.domain.enums.exchange_rate_source import ExchangeRateSource
from app.domain.enums.financial_transaction_type import (
    FinancialTransactionType,
)
from app.domain.enums.purchase_cost_type import PurchaseCostType
from app.domain.enums.purchase_status import PurchaseStatus
from app.domain.exceptions import (
    AccountCurrencyMismatchError,
    InactiveAccountError,
    InvalidCostAllocationError,
    InvalidPurchaseTransitionError,
    PurchaseCurrencyMismatchError,
    PurchasePaymentError,
    SupplierNotFoundError,
    VariantNotFoundError,
)
from app.domain.value_objects.money import Money
from app.infrastructure.database.repositories import (
    SqlAlchemyAccountRepository,
    SqlAlchemyCurrencyRepository,
    SqlAlchemyExchangeRateRepository,
    SqlAlchemyFinancialTransactionRepository,
    SqlAlchemyProductRepository,
    SqlAlchemyProductVariantRepository,
    SqlAlchemyPurchaseCostAllocationRepository,
    SqlAlchemyPurchaseCostRepository,
    SqlAlchemyPurchaseItemRepository,
    SqlAlchemyPurchaseRepository,
    SqlAlchemySupplierRepository,
)

NOW = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)
EARLIER = datetime(2026, 10, 26, 12, 0, tzinfo=UTC)


def _currency(db_session, code: str = "USD") -> Currency:
    currency = SqlAlchemyCurrencyRepository(db_session).get_by_code(code)
    assert currency is not None
    return currency


def _account(db_session, name: str, code: str = "USD") -> Account:
    return SqlAlchemyAccountRepository(db_session).add(
        Account(name=name, currency=_currency(db_session, code))
    )


def _variant(db_session, name: str, sku: str | None = None):
    product = SqlAlchemyProductRepository(db_session).add(
        Product(name=name)
    )
    return SqlAlchemyProductVariantRepository(db_session).add(
        ProductVariant(
            product_id=product.id,
            sku=sku,
            variant_name=name,
        )
    )


def _supplier(db_session, name: str = "Acme"):
    return CreateSupplier(
        SqlAlchemySupplierRepository(db_session)
    ).execute(CreateSupplierRequest(name=name))


def _rate(
    db_session,
    base: str,
    quote: str,
    value: str,
):
    return SqlAlchemyExchangeRateRepository(db_session).add(
        ExchangeRate(
            base_currency=_currency(db_session, base),
            quote_currency=_currency(db_session, quote),
            rate=Decimal(value),
            source=ExchangeRateSource.MANUAL,
            rate_timestamp=NOW,
        )
    )


def _repositories(db_session):
    return {
        "accounts": SqlAlchemyAccountRepository(db_session),
        "suppliers": SqlAlchemySupplierRepository(db_session),
        "purchases": SqlAlchemyPurchaseRepository(db_session),
        "items": SqlAlchemyPurchaseItemRepository(db_session),
        "costs": SqlAlchemyPurchaseCostRepository(db_session),
        "allocations": SqlAlchemyPurchaseCostAllocationRepository(
            db_session
        ),
        "rates": SqlAlchemyExchangeRateRepository(db_session),
        "transactions": SqlAlchemyFinancialTransactionRepository(
            db_session
        ),
    }


def _register_service(db_session):
    repositories = _repositories(db_session)
    service = RegisterPurchase(
        accounts=repositories["accounts"],
        purchases=repositories["purchases"],
        items=repositories["items"],
        costs=repositories["costs"],
        allocations=repositories["allocations"],
        exchange_rates=repositories["rates"],
        transactions=repositories["transactions"],
    )
    return service, repositories


def _payment_service(db_session):
    repositories = _repositories(db_session)
    service = RegisterPurchasePayment(
        accounts=repositories["accounts"],
        purchases=repositories["purchases"],
        items=repositories["items"],
        costs=repositories["costs"],
        transactions=repositories["transactions"],
    )
    return service, repositories


def _status_service(db_session):
    repositories = _repositories(db_session)
    return UpdatePurchaseStatus(repositories["purchases"]), repositories


def _basic_request(
    db_session,
    *,
    variant,
    currency: Currency | None = None,
    quantity: int = 2,
    price: str = "10.00",
    supplier_id: int | None = None,
    account_id: int | None = None,
    costs: tuple[PurchaseCostRequest, ...] = (),
    purchase_date: datetime = NOW,
) -> RegisterPurchaseRequest:
    currency = currency or _currency(db_session)
    return RegisterPurchaseRequest(
        currency=currency,
        purchase_date=purchase_date,
        supplier_id=supplier_id,
        account_id=account_id,
        items=(
            PurchaseItemRequest(
                variant_id=variant.id,
                quantity=quantity,
                unit_price=Money(price, currency),
            ),
        ),
        costs=costs,
    )


def test_create_supplier_and_list_purchase_history(db_session) -> None:
    first = _supplier(db_session, "First Supplier")
    second = _supplier(db_session, "Second Supplier")
    variant = _variant(db_session, "Phone")
    service, repositories = _register_service(db_session)

    older = service.execute(
        _basic_request(
            db_session,
            variant=variant,
            supplier_id=first.id,
            purchase_date=EARLIER,
        )
    )
    newer = service.execute(
        _basic_request(
            db_session,
            variant=variant,
            supplier_id=first.id,
            purchase_date=NOW,
        )
    )
    service.execute(
        _basic_request(
            db_session,
            variant=variant,
            supplier_id=second.id,
            purchase_date=EARLIER,
        )
    )

    history = repositories["purchases"].list_by_supplier(first.id)

    assert [purchase.id for purchase in history] == [
        newer.purchase.id,
        older.purchase.id,
    ]
    assert repositories["purchases"].list_all()[0].id == newer.purchase.id
    assert repositories["suppliers"].get_by_id(first.id) == first


def test_supplier_deactivation_is_non_destructive(db_session) -> None:
    supplier = _supplier(db_session)
    repository = SqlAlchemySupplierRepository(db_session)

    inactive = repository.save(supplier.deactivate())

    assert inactive.is_active is False
    assert repository.list_all() == []
    assert repository.list_all(include_inactive=True) == [inactive]


def test_register_unpaid_purchase_with_costs_and_exact_allocations(
    db_session,
) -> None:
    usd = _currency(db_session)
    supplier = _supplier(db_session)
    first = _variant(db_session, "Phone 128GB", "PHONE-128")
    second = _variant(db_session, "Phone 256GB", "PHONE-256")
    service, repositories = _register_service(db_session)

    result = service.execute(
        RegisterPurchaseRequest(
            currency=usd,
            purchase_date=NOW,
            supplier_id=supplier.id,
            items=(
                PurchaseItemRequest(
                    variant_id=first.id,
                    quantity=2,
                    unit_price=Money("10.00", usd),
                    weight=Decimal("1.5"),
                ),
                PurchaseItemRequest(
                    variant_id=second.id,
                    quantity=1,
                    unit_price=Money("20.00", usd),
                    weight=Decimal("0.5"),
                ),
            ),
            costs=(
                PurchaseCostRequest(
                    cost_type=PurchaseCostType.SHIPPING,
                    amount=Money("12.00", usd),
                    allocation_method=AllocationMethod.BY_QUANTITY,
                ),
                PurchaseCostRequest(
                    cost_type=PurchaseCostType.TAX,
                    amount=Money("6.00", usd),
                    allocation_method=AllocationMethod.BY_VALUE,
                ),
            ),
        )
    )

    assert result.purchase.id is not None
    assert result.purchase.status is PurchaseStatus.PENDING
    assert result.purchase.account is None
    assert result.total == Money("58.00", usd)
    assert [item.line_total for item in result.items] == [
        Money("20.00", usd),
        Money("20.00", usd),
    ]
    assert [
        cost.normalized_amount for cost in result.costs
    ] == [Money("12.00", usd), Money("6.00", usd)]
    assert len(result.allocations) == 4

    for cost in result.costs:
        allocations = [
            allocation
            for allocation in result.allocations
            if allocation.purchase_cost.id == cost.id
        ]
        assert (
            sum(
                (
                    allocation.allocated_original_amount
                    for allocation in allocations
                ),
                Money.zero(cost.amount.currency),
            )
            == cost.amount
        )
        assert (
            sum(
                (
                    allocation.allocated_purchase_currency_amount
                    for allocation in allocations
                ),
                Money.zero(usd),
            )
            == cost.normalized_amount
        )

    assert repositories["purchases"].get_by_id(
        result.purchase.id
    ) == result.purchase
    assert repositories["items"].list_for_purchase(
        result.purchase.id
    ) == list(result.items)
    assert repositories["costs"].list_for_purchase(
        result.purchase.id
    ) == list(result.costs)
    assert repositories["transactions"].list_for_account(
        _account(db_session, "Unrelated").id
    ) == []


def test_register_paid_purchase_creates_negative_purchase_entry(
    db_session,
) -> None:
    usd = _currency(db_session)
    account = _account(db_session, "Cash USD")
    variant = _variant(db_session, "Phone")
    service, repositories = _register_service(db_session)

    result = service.execute(
        _basic_request(
            db_session,
            variant=variant,
            account_id=account.id,
            costs=(
                PurchaseCostRequest(
                    cost_type=PurchaseCostType.SHIPPING,
                    amount=Money("5.00", usd),
                    allocation_method=AllocationMethod.BY_QUANTITY,
                ),
            ),
        )
    )

    entries = repositories["transactions"].list_for_account(account.id)
    balance = GetAccountBalance(
        repositories["accounts"], repositories["transactions"]
    ).execute(account.id)

    assert result.purchase.status is PurchaseStatus.PURCHASED
    assert result.purchase.account_id == account.id
    assert result.total == Money("25.00", usd)
    assert len(entries) == 1
    assert entries[0].transaction_type is FinancialTransactionType.PURCHASE
    assert entries[0].amount == Money("-25.00", usd)
    assert entries[0].purchase_id == result.purchase.id
    assert balance == Money("-25.00", usd)


def test_foreign_cost_keeps_original_and_normalized_values(
    db_session,
) -> None:
    eur = _currency(db_session, "EUR")
    usd = _currency(db_session)
    rate = _rate(db_session, "EUR", "USD", "1.10")
    variant = _variant(db_session, "Imported Phone")
    account = _account(db_session, "Cash USD")
    service, repositories = _register_service(db_session)

    result = service.execute(
        RegisterPurchaseRequest(
            currency=usd,
            purchase_date=NOW,
            account_id=account.id,
            items=(
                PurchaseItemRequest(
                    variant_id=variant.id,
                    quantity=1,
                    unit_price=Money("10.00", usd),
                ),
            ),
            costs=(
                PurchaseCostRequest(
                    cost_type=PurchaseCostType.CUSTOMS,
                    amount=Money("10.00", eur),
                    allocation_method=AllocationMethod.BY_QUANTITY,
                    exchange_rate_id=rate.id,
                ),
            ),
        )
    )

    cost = result.costs[0]
    allocation = result.allocations[0]
    entries = repositories["transactions"].list_for_account(account.id)

    assert cost.amount == Money("10.00", eur)
    assert cost.normalized_amount == Money("11.00", usd)
    assert allocation.allocated_original_amount == Money("10.00", eur)
    assert allocation.allocated_purchase_currency_amount == Money(
        "11.00", usd
    )
    assert result.total == Money("21.00", usd)
    assert entries[0].amount == Money("-21.00", usd)


def test_manual_cost_allocation_uses_item_positions(db_session) -> None:
    usd = _currency(db_session)
    first = _variant(db_session, "First")
    second = _variant(db_session, "Second")
    service, _ = _register_service(db_session)

    result = service.execute(
        RegisterPurchaseRequest(
            currency=usd,
            purchase_date=NOW,
            items=(
                PurchaseItemRequest(
                    variant_id=first.id,
                    quantity=1,
                    unit_price=Money("10.00", usd),
                ),
                PurchaseItemRequest(
                    variant_id=second.id,
                    quantity=1,
                    unit_price=Money("10.00", usd),
                ),
            ),
            costs=(
                PurchaseCostRequest(
                    cost_type=PurchaseCostType.OTHER,
                    amount=Money("10.00", usd),
                    allocation_method=AllocationMethod.MANUAL,
                    manual_allocations={
                        0: Money("3.00", usd),
                        1: Money("7.00", usd),
                    },
                ),
            ),
        )
    )

    assert [
        allocation.allocated_purchase_currency_amount
        for allocation in result.allocations
    ] == [Money("3.00", usd), Money("7.00", usd)]
    assert result.total == Money("30.00", usd)


def test_payment_can_be_registered_later_only_once(db_session) -> None:
    account = _account(db_session, "Cash USD")
    variant = _variant(db_session, "Phone")
    register, repositories = _register_service(db_session)
    pay, _ = _payment_service(db_session)

    pending = register.execute(
        _basic_request(db_session, variant=variant)
    )
    assert pending.purchase.status is PurchaseStatus.PENDING

    paid = pay.execute(
        RegisterPurchasePaymentRequest(
            purchase_id=pending.purchase.id,
            account_id=account.id,
            payment_date=NOW,
        )
    )

    entries = repositories["transactions"].list_for_account(account.id)
    assert paid.status is PurchaseStatus.PURCHASED
    assert paid.account_id == account.id
    assert len(entries) == 1
    assert entries[0].amount == Money("-20.00", _currency(db_session))

    with pytest.raises(PurchasePaymentError):
        pay.execute(
            RegisterPurchasePaymentRequest(
                purchase_id=pending.purchase.id,
                account_id=account.id,
            )
        )
    assert len(repositories["transactions"].list_for_account(account.id)) == 1


def test_payment_requires_an_active_account_in_purchase_currency(
    db_session,
) -> None:
    usd = _currency(db_session)
    eur_account = _account(db_session, "Cash EUR", "EUR")
    inactive = _account(db_session, "Old USD")
    inactive = SqlAlchemyAccountRepository(db_session).save(
        inactive.deactivate()
    )
    variant = _variant(db_session, "Phone")
    register, repositories = _register_service(db_session)
    pay, _ = _payment_service(db_session)

    pending = register.execute(
        _basic_request(db_session, variant=variant)
    )

    with pytest.raises(AccountCurrencyMismatchError):
        pay.execute(
            RegisterPurchasePaymentRequest(
                purchase_id=pending.purchase.id,
                account_id=eur_account.id,
            )
        )
    with pytest.raises(InactiveAccountError):
        pay.execute(
            RegisterPurchasePaymentRequest(
                purchase_id=pending.purchase.id,
                account_id=inactive.id,
            )
        )

    assert repositories["transactions"].list_for_account(
        eur_account.id
    ) == []
    assert repositories["transactions"].list_for_account(inactive.id) == []
    assert repositories["purchases"].get_by_id(
        pending.purchase.id
    ).status is PurchaseStatus.PENDING


def test_purchase_status_transitions_are_guarded(db_session) -> None:
    account = _account(db_session, "Cash USD")
    variant = _variant(db_session, "Phone")
    register, repositories = _register_service(db_session)
    update, _ = _status_service(db_session)

    paid = register.execute(
        _basic_request(
            db_session, variant=variant, account_id=account.id
        )
    )
    shipped = update.execute(
        UpdatePurchaseStatusRequest(
            purchase_id=paid.purchase.id,
            status=PurchaseStatus.SHIPPED,
        )
    )
    in_transit = update.execute(
        UpdatePurchaseStatusRequest(
            purchase_id=paid.purchase.id,
            status=PurchaseStatus.IN_TRANSIT,
        )
    )

    with pytest.raises(InvalidPurchaseTransitionError):
        update.execute(
            UpdatePurchaseStatusRequest(
                purchase_id=paid.purchase.id,
                status=PurchaseStatus.RECEIVED,
            )
        )

    assert shipped.status is PurchaseStatus.SHIPPED
    assert in_transit.status is PurchaseStatus.IN_TRANSIT
    assert repositories["purchases"].get_by_id(
        paid.purchase.id
    ).status is PurchaseStatus.IN_TRANSIT

    pending = register.execute(
        _basic_request(db_session, variant=variant)
    )
    cancelled = update.execute(
        UpdatePurchaseStatusRequest(
            purchase_id=pending.purchase.id,
            status=PurchaseStatus.CANCELLED,
        )
    )
    assert cancelled.status is PurchaseStatus.CANCELLED

    with pytest.raises(InvalidPurchaseTransitionError):
        update.execute(
            UpdatePurchaseStatusRequest(
                purchase_id=paid.purchase.id,
                status=PurchaseStatus.CANCELLED,
            )
        )


def test_purchase_registration_validates_references_and_currency(
    db_session,
) -> None:
    eur = _currency(db_session, "EUR")
    variant = _variant(db_session, "Phone")
    service, _ = _register_service(db_session)

    with pytest.raises(SupplierNotFoundError):
        service.execute(
            _basic_request(
                db_session, variant=variant, supplier_id=999
            )
        )

    with pytest.raises(VariantNotFoundError):
        service.execute(
            RegisterPurchaseRequest(
                currency=_currency(db_session),
                purchase_date=NOW,
                items=(
                    PurchaseItemRequest(
                        variant_id=999,
                        quantity=1,
                        unit_price=Money("1.00", _currency(db_session)),
                    ),
                ),
            )
        )

    with pytest.raises(PurchaseCurrencyMismatchError):
        service.execute(
            RegisterPurchaseRequest(
                currency=_currency(db_session),
                purchase_date=NOW,
                items=(
                    PurchaseItemRequest(
                        variant_id=variant.id,
                        quantity=1,
                        unit_price=Money("1.00", eur),
                    ),
                ),
            )
        )


def test_weight_allocation_requires_weights(db_session) -> None:
    variant = _variant(db_session, "Phone")
    service, _ = _register_service(db_session)

    with pytest.raises(InvalidCostAllocationError):
        service.execute(
            _basic_request(
                db_session,
                variant=variant,
                costs=(
                    PurchaseCostRequest(
                        cost_type=PurchaseCostType.SHIPPING,
                        amount=Money("5.00", _currency(db_session)),
                        allocation_method=AllocationMethod.BY_WEIGHT,
                    ),
                ),
            )
        )
