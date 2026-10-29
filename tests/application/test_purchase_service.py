"""Purchase application-service tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.application.finances.account_service import AccountService
from app.application.finances.create_account import CreateAccountRequest
from app.application.products.catalog import ProductCatalogService
from app.application.products.create_product import (
    CreateProductRequest,
    ProductVariantRequest,
)
from app.application.purchases import (
    PurchaseCostRequest,
    PurchaseItemRequest,
    PurchaseService,
    RegisterPurchasePaymentRequest,
    RegisterPurchaseRequest,
    UpdatePurchaseStatusRequest,
)
from app.application.suppliers.create_supplier import CreateSupplierRequest
from app.domain.enums.allocation_method import AllocationMethod
from app.domain.enums.purchase_cost_type import PurchaseCostType
from app.domain.enums.purchase_status import PurchaseStatus
from app.domain.exceptions import (
    InvalidPurchaseTransitionError,
    PurchaseNotFoundError,
    VariantNotFoundError,
)
from app.domain.value_objects.money import Money
from app.infrastructure.database.session import create_session_factory
from app.infrastructure.database.unit_of_work import (
    SqlAlchemyUnitOfWorkFactory,
)

NOW = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)


@pytest.fixture
def unit_of_work_factory(migrated_engine) -> SqlAlchemyUnitOfWorkFactory:
    return SqlAlchemyUnitOfWorkFactory(
        create_session_factory(migrated_engine)
    )


@pytest.fixture
def service(unit_of_work_factory) -> PurchaseService:
    return PurchaseService(unit_of_work_factory)


@pytest.fixture
def catalog(unit_of_work_factory) -> ProductCatalogService:
    return ProductCatalogService(unit_of_work_factory)


@pytest.fixture
def accounts(unit_of_work_factory) -> AccountService:
    return AccountService(unit_of_work_factory)


def _usd(service: PurchaseService):
    return next(
        currency
        for currency in service.list_enabled_currencies()
        if currency.code == "USD"
    )


def _variant(service: PurchaseService, catalog: ProductCatalogService):
    catalog.create_product(
        CreateProductRequest(
            name="Phone",
            variants=(
                ProductVariantRequest(
                    sku="PHONE-1",
                    variant_name="Black",
                ),
            ),
        )
    )
    return service.list_variant_options()[0]


def _supplier(service: PurchaseService):
    return service.create_supplier(
        CreateSupplierRequest(name="Acme Trading")
    )


def _account(accounts: AccountService, usd):
    return accounts.create_account(
        CreateAccountRequest(name="Cash USD", currency=usd)
    )


def test_purchase_service_lists_creates_pays_and_updates(
    service, catalog, accounts
) -> None:
    usd = _usd(service)
    supplier = _supplier(service)
    variant = _variant(service, catalog)
    account = _account(accounts, usd)

    created = service.create_purchase(
        RegisterPurchaseRequest(
            currency=usd,
            purchase_date=NOW,
            supplier_id=supplier.id,
            items=(
                PurchaseItemRequest(
                    variant_id=variant.variant_id,
                    quantity=2,
                    unit_price=Money("10.00", usd),
                ),
            ),
            costs=(
                PurchaseCostRequest(
                    cost_type=PurchaseCostType.SHIPPING,
                    amount=Money("5.00", usd),
                    allocation_method=AllocationMethod.BY_QUANTITY,
                    description="Courier",
                ),
            ),
            order_number="ORD-1",
            tracking_number="TRACK-1",
            notes="First order",
        )
    )

    rows = service.list_purchases()
    assert len(rows) == 1
    row = rows[0]
    assert row.purchase_id == created.purchase.id
    assert row.supplier_name == "Acme Trading"
    assert row.currency_code == "USD"
    assert row.item_count == 1
    assert row.total == Money("25.00", usd)
    assert row.status is PurchaseStatus.PENDING
    assert row.account_name is None
    assert row.order_number == "ORD-1"
    assert row.tracking_number == "TRACK-1"
    assert row.notes == "First order"
    assert row.allowed_statuses == (PurchaseStatus.CANCELLED,)

    detail = service.get_purchase_detail(row.purchase_id)
    assert detail.purchase.total == Money("25.00", usd)
    assert len(detail.items) == 1
    assert detail.items[0].variant_label == "Phone / Black (PHONE-1)"
    assert detail.items[0].line_total == Money("20.00", usd)
    assert len(detail.costs) == 1
    assert detail.costs[0].cost_type is PurchaseCostType.SHIPPING
    assert detail.costs[0].amount == Money("5.00", usd)
    assert detail.costs[0].normalized_amount == Money("5.00", usd)
    assert detail.costs[0].description == "Courier"

    paid = service.register_payment(
        RegisterPurchasePaymentRequest(
            purchase_id=row.purchase_id,
            account_id=account.id,
            payment_date=NOW,
        )
    )

    assert paid.status is PurchaseStatus.PURCHASED
    row = service.list_purchases()[0]
    assert row.status is PurchaseStatus.PURCHASED
    assert row.account_name == "Cash USD"
    assert row.allowed_statuses == (
        PurchaseStatus.SHIPPED,
        PurchaseStatus.IN_TRANSIT,
    )

    shipped = service.update_status(
        UpdatePurchaseStatusRequest(
            purchase_id=row.purchase_id,
            status=PurchaseStatus.SHIPPED,
        )
    )
    assert shipped.status is PurchaseStatus.SHIPPED
    assert service.list_purchases()[0].status is PurchaseStatus.SHIPPED

    with pytest.raises(InvalidPurchaseTransitionError):
        service.update_status(
            UpdatePurchaseStatusRequest(
                purchase_id=row.purchase_id,
                status=PurchaseStatus.RECEIVED,
            )
        )


def test_reference_data_and_unpaid_purchase(
    service, catalog, accounts
) -> None:
    usd = _usd(service)
    supplier = _supplier(service)
    variant = _variant(service, catalog)
    account = _account(accounts, usd)

    assert service.list_suppliers() == (supplier,)
    assert service.list_accounts() == (account,)
    assert service.list_variant_options() == (variant,)
    assert any(
        currency.code == "USD"
        for currency in service.list_enabled_currencies()
    )

    created = service.create_purchase(
        RegisterPurchaseRequest(
            currency=usd,
            purchase_date=NOW,
            items=(
                PurchaseItemRequest(
                    variant_id=variant.variant_id,
                    quantity=1,
                    unit_price=Money("7.50", usd),
                ),
            ),
        )
    )

    assert created.purchase.account is None
    row = service.list_purchases()[0]
    assert row.status is PurchaseStatus.PENDING
    assert row.account_name is None
    assert row.total == Money("7.50", usd)


def test_failed_purchase_rolls_back_the_application_transaction(
    service,
) -> None:
    usd = _usd(service)

    with pytest.raises(VariantNotFoundError):
        service.create_purchase(
            RegisterPurchaseRequest(
                currency=usd,
                purchase_date=NOW,
                items=(
                    PurchaseItemRequest(
                        variant_id=999,
                        quantity=1,
                        unit_price=Money("1.00", usd),
                    ),
                ),
            )
        )

    assert service.list_purchases() == ()
    with pytest.raises(PurchaseNotFoundError):
        service.get_purchase_detail(999)
