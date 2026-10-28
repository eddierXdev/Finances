"""Application service for the Purchases screen."""

from __future__ import annotations

from app.application.purchases.list_purchases import (
    GetPurchaseDetail,
    ListPurchases,
    ListVariantOptions,
    PurchaseDetail,
    PurchaseListItem,
    VariantOption,
)
from app.application.purchases.register_purchase import (
    RegisteredPurchase,
    RegisterPurchase,
    RegisterPurchaseRequest,
)
from app.application.purchases.register_purchase_payment import (
    RegisterPurchasePayment,
    RegisterPurchasePaymentRequest,
)
from app.application.purchases.update_purchase_status import (
    UpdatePurchaseStatus,
    UpdatePurchaseStatusRequest,
)
from app.application.suppliers.create_supplier import (
    CreateSupplier,
    CreateSupplierRequest,
)
from app.application.unit_of_work import UnitOfWorkFactory
from app.domain.entities.account import Account
from app.domain.entities.currency import Currency
from app.domain.entities.purchase import Purchase
from app.domain.entities.supplier import Supplier


class PurchaseService:
    """Read and write purchases with explicit transaction boundaries."""

    def __init__(self, unit_of_work: UnitOfWorkFactory) -> None:
        self._unit_of_work = unit_of_work

    def list_purchases(self) -> tuple[PurchaseListItem, ...]:
        with self._unit_of_work.unit_of_work() as uow:
            return ListPurchases(
                uow.purchases,
                uow.purchase_items,
                uow.purchase_costs,
                uow.suppliers,
            ).execute()

    def get_purchase_detail(self, purchase_id: int) -> PurchaseDetail:
        with self._unit_of_work.unit_of_work() as uow:
            return GetPurchaseDetail(
                uow.purchases,
                uow.purchase_items,
                uow.purchase_costs,
                uow.suppliers,
                uow.products,
                uow.variants,
            ).execute(purchase_id)

    def list_suppliers(
        self, *, include_inactive: bool = False
    ) -> tuple[Supplier, ...]:
        with self._unit_of_work.unit_of_work() as uow:
            return tuple(
                uow.suppliers.list_all(include_inactive=include_inactive)
            )

    def create_supplier(self, request: CreateSupplierRequest) -> Supplier:
        with self._unit_of_work.unit_of_work() as uow:
            supplier = CreateSupplier(uow.suppliers).execute(request)
            uow.commit()
            return supplier

    def list_accounts(
        self, *, include_inactive: bool = False
    ) -> tuple[Account, ...]:
        with self._unit_of_work.unit_of_work() as uow:
            return tuple(
                uow.accounts.list_all(include_inactive=include_inactive)
            )

    def list_enabled_currencies(self) -> tuple[Currency, ...]:
        with self._unit_of_work.unit_of_work() as uow:
            return tuple(uow.currencies.list_all(enabled_only=True))

    def list_variant_options(self) -> tuple[VariantOption, ...]:
        with self._unit_of_work.unit_of_work() as uow:
            return ListVariantOptions(
                uow.products,
                uow.variants,
            ).execute()

    def create_purchase(
        self, request: RegisterPurchaseRequest
    ) -> RegisteredPurchase:
        with self._unit_of_work.unit_of_work() as uow:
            purchase = RegisterPurchase(
                accounts=uow.accounts,
                purchases=uow.purchases,
                items=uow.purchase_items,
                costs=uow.purchase_costs,
                allocations=uow.purchase_allocations,
                exchange_rates=uow.exchange_rates,
                transactions=uow.transactions,
            ).execute(request)
            uow.commit()
            return purchase

    def register_payment(
        self, request: RegisterPurchasePaymentRequest
    ) -> Purchase:
        with self._unit_of_work.unit_of_work() as uow:
            purchase = RegisterPurchasePayment(
                accounts=uow.accounts,
                purchases=uow.purchases,
                items=uow.purchase_items,
                costs=uow.purchase_costs,
                transactions=uow.transactions,
            ).execute(request)
            uow.commit()
            return purchase

    def update_status(
        self, request: UpdatePurchaseStatusRequest
    ) -> Purchase:
        with self._unit_of_work.unit_of_work() as uow:
            purchase = UpdatePurchaseStatus(uow.purchases).execute(request)
            uow.commit()
            return purchase
