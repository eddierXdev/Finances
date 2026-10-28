"""SQLAlchemy purchase repository."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.purchase import Purchase
from app.domain.exceptions import (
    AccountCurrencyMismatchError,
    AccountNotFoundError,
    CurrencyNotFoundError,
    InactiveAccountError,
    PurchaseNotFoundError,
    SupplierNotFoundError,
)
from app.infrastructure.database.models import (
    AccountModel,
    CurrencyModel,
    PurchaseModel,
    SupplierModel,
)
from app.infrastructure.database.repositories.mapping import purchase_to_domain


class SqlAlchemyPurchaseRepository:
    """Purchase persistence using SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, purchase: Purchase) -> Purchase:
        currency = self._require_currency(purchase.currency.code)
        self._require_supplier(purchase.supplier_id)
        account = self._resolve_account(purchase, require_active=True)

        model = PurchaseModel(
            supplier_id=purchase.supplier_id,
            account=account,
            status=purchase.status.value,
            currency=currency,
            purchase_date=purchase.purchase_date,
            order_number=purchase.order_number,
            tracking_number=purchase.tracking_number,
            notes=purchase.notes,
        )
        self._session.add(model)
        self._session.flush()
        return purchase_to_domain(model)

    def save(self, purchase: Purchase) -> Purchase:
        if purchase.id is None:
            raise ValueError("Cannot save a purchase without an id.")

        model = self._session.get(PurchaseModel, purchase.id)
        if model is None:
            raise PurchaseNotFoundError(
                f"Purchase {purchase.id} does not exist."
            )

        if model.currency.code != purchase.currency.code:
            raise ValueError(
                "A purchase currency cannot be changed after creation."
            )

        self._require_supplier(purchase.supplier_id)
        account = self._resolve_account(purchase, require_active=False)

        model.supplier_id = purchase.supplier_id
        model.account = account
        model.status = purchase.status.value
        model.purchase_date = purchase.purchase_date
        model.order_number = purchase.order_number
        model.tracking_number = purchase.tracking_number
        model.notes = purchase.notes
        self._session.flush()
        return purchase_to_domain(model)

    def get_by_id(self, purchase_id: int) -> Purchase | None:
        model = self._session.get(PurchaseModel, purchase_id)
        return purchase_to_domain(model) if model is not None else None

    def list_all(self) -> list[Purchase]:
        statement = select(PurchaseModel).order_by(
            PurchaseModel.purchase_date.desc(),
            PurchaseModel.id.desc(),
        )
        return [
            purchase_to_domain(model)
            for model in self._session.scalars(statement)
        ]

    def list_by_supplier(self, supplier_id: int) -> list[Purchase]:
        statement = (
            select(PurchaseModel)
            .where(PurchaseModel.supplier_id == supplier_id)
            .order_by(
                PurchaseModel.purchase_date.desc(),
                PurchaseModel.id.desc(),
            )
        )
        return [
            purchase_to_domain(model)
            for model in self._session.scalars(statement)
        ]

    def _require_supplier(self, supplier_id: int | None) -> None:
        if supplier_id is None:
            return
        if self._session.get(SupplierModel, supplier_id) is None:
            raise SupplierNotFoundError(
                f"Supplier {supplier_id} does not exist."
            )

    def _require_currency(self, code: str) -> CurrencyModel:
        normalized_code = code.strip().upper()
        model = self._session.scalar(
            select(CurrencyModel).where(
                CurrencyModel.code == normalized_code
            )
        )
        if model is None:
            raise CurrencyNotFoundError(
                f"Currency {normalized_code} is not registered."
            )
        return model

    def _resolve_account(
        self, purchase: Purchase, *, require_active: bool
    ) -> AccountModel | None:
        if purchase.account is None:
            return None
        if purchase.account.id is None:
            raise ValueError(
                "Cannot use an account without an id for a purchase."
            )

        account = self._session.get(AccountModel, purchase.account.id)
        if account is None:
            raise AccountNotFoundError(
                f"Account {purchase.account.id} does not exist."
            )
        if account.currency.code != purchase.currency.code:
            raise AccountCurrencyMismatchError(
                f"Account currency {account.currency.code} does not match "
                f"purchase currency {purchase.currency.code}."
            )
        if require_active and not account.is_active:
            raise InactiveAccountError(
                f"Account {account.id} is inactive."
            )
        return account
