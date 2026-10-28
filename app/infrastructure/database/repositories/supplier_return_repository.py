"""SQLAlchemy supplier return repository."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.supplier_return import SupplierReturn
from app.domain.exceptions import (
    AccountCurrencyMismatchError,
    AccountNotFoundError,
    InactiveAccountError,
    InvalidSupplierReturnError,
    PurchaseNotFoundError,
    SupplierNotFoundError,
)
from app.infrastructure.database.models import (
    AccountModel,
    PurchaseModel,
    SupplierModel,
    SupplierReturnModel,
)
from app.infrastructure.database.repositories.mapping import (
    supplier_return_to_domain,
)


class SqlAlchemySupplierReturnRepository:
    """Supplier return header persistence using SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, supplier_return: SupplierReturn) -> SupplierReturn:
        if supplier_return.purchase.id is None:
            raise ValueError(
                "Cannot persist a supplier return without a purchase."
            )

        purchase = self._require_purchase(supplier_return.purchase.id)
        supplier = None
        if supplier_return.supplier_id is not None:
            supplier = self._require_supplier(
                supplier_return.supplier_id
            )
            if purchase.supplier_id != supplier.id:
                raise InvalidSupplierReturnError(
                    "A supplier return must reference the original "
                    "purchase supplier."
                )

        account = None
        refund_currency = None
        if supplier_return.refund_amount is not None:
            if supplier_return.account is None:
                raise ValueError(
                    "A supplier refund requires a persisted account."
                )
            account = self._require_account(
                supplier_return.account.id, purchase.currency.code
            )
            refund_currency = purchase.currency

        model = SupplierReturnModel(
            purchase=purchase,
            supplier=supplier,
            account=account,
            refund_amount=(
                supplier_return.refund_amount.amount
                if supplier_return.refund_amount is not None
                else None
            ),
            refund_currency=refund_currency,
            return_date=supplier_return.return_date,
            notes=supplier_return.notes,
        )
        self._session.add(model)
        self._session.flush()
        return supplier_return_to_domain(model)

    def get_by_id(self, return_id: int) -> SupplierReturn | None:
        model = self._session.get(SupplierReturnModel, return_id)
        return (
            supplier_return_to_domain(model)
            if model is not None
            else None
        )

    def list_all(self) -> list[SupplierReturn]:
        statement = select(SupplierReturnModel).order_by(
            SupplierReturnModel.return_date.desc(),
            SupplierReturnModel.id.desc(),
        )
        return [
            supplier_return_to_domain(model)
            for model in self._session.scalars(statement)
        ]

    def list_for_purchase(
        self, purchase_id: int
    ) -> list[SupplierReturn]:
        statement = (
            select(SupplierReturnModel)
            .where(SupplierReturnModel.purchase_id == purchase_id)
            .order_by(
                SupplierReturnModel.return_date.asc(),
                SupplierReturnModel.id.asc(),
            )
        )
        return [
            supplier_return_to_domain(model)
            for model in self._session.scalars(statement)
        ]

    def _require_purchase(self, purchase_id: int) -> PurchaseModel:
        model = self._session.get(PurchaseModel, purchase_id)
        if model is None:
            raise PurchaseNotFoundError(
                f"Purchase {purchase_id} does not exist."
            )
        return model

    def _require_supplier(self, supplier_id: int) -> SupplierModel:
        model = self._session.get(SupplierModel, supplier_id)
        if model is None:
            raise SupplierNotFoundError(
                f"Supplier {supplier_id} does not exist."
            )
        return model

    def _require_account(
        self, account_id: int | None, currency_code: str
    ) -> AccountModel:
        if account_id is None:
            raise AccountNotFoundError(
                "A supplier refund requires a persisted account."
            )
        account = self._session.get(AccountModel, account_id)
        if account is None:
            raise AccountNotFoundError(
                f"Account {account_id} does not exist."
            )
        if account.currency.code != currency_code:
            raise AccountCurrencyMismatchError(
                f"Account currency {account.currency.code} does not match "
                f"refund currency {currency_code}."
            )
        if not account.is_active:
            raise InactiveAccountError(
                f"Account {account.id} is inactive."
            )
        return account
