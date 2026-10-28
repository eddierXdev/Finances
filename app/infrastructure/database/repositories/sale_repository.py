"""SQLAlchemy sale repository."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.sale import Sale
from app.domain.exceptions import (
    AccountCurrencyMismatchError,
    AccountNotFoundError,
    CurrencyNotFoundError,
    CustomerNotFoundError,
    InactiveAccountError,
    SaleNotFoundError,
)
from app.infrastructure.database.models import (
    AccountModel,
    CurrencyModel,
    CustomerModel,
    SaleModel,
)
from app.infrastructure.database.repositories.mapping import sale_to_domain


class SqlAlchemySaleRepository:
    """Sale header persistence using SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, sale: Sale) -> Sale:
        currency = self._require_currency(sale.currency.code)
        account = self._require_account(
            sale.account.id, sale.currency.code
        )
        self._require_customer(sale.customer_id)

        model = SaleModel(
            customer_id=sale.customer_id,
            account=account,
            currency=currency,
            status=sale.status.value,
            sale_date=sale.sale_date,
            discount_amount=(
                sale.discount_amount.amount
                if sale.discount_amount is not None
                else None
            ),
            notes=sale.notes,
        )
        self._session.add(model)
        self._session.flush()
        return sale_to_domain(model)

    def save(self, sale: Sale) -> Sale:
        if sale.id is None:
            raise ValueError("Cannot save a sale without an id.")

        model = self._session.get(SaleModel, sale.id)
        if model is None:
            raise SaleNotFoundError(f"Sale {sale.id} does not exist.")

        if (
            model.customer_id != sale.customer_id
            or model.account_id != sale.account_id
            or model.currency.code != sale.currency.code
            or model.sale_date != sale.sale_date
            or model.discount_amount
            != (
                sale.discount_amount.amount
                if sale.discount_amount is not None
                else None
            )
            or model.notes != sale.notes
        ):
            raise ValueError(
                "A sale's header data cannot change after creation."
            )

        model.status = sale.status.value
        self._session.flush()
        return sale_to_domain(model)

    def get_by_id(self, sale_id: int) -> Sale | None:
        model = self._session.get(SaleModel, sale_id)
        return sale_to_domain(model) if model is not None else None

    def list_all(self) -> list[Sale]:
        statement = select(SaleModel).order_by(
            SaleModel.sale_date.desc(),
            SaleModel.id.desc(),
        )
        return [
            sale_to_domain(model)
            for model in self._session.scalars(statement)
        ]

    def list_by_customer(self, customer_id: int) -> list[Sale]:
        statement = (
            select(SaleModel)
            .where(SaleModel.customer_id == customer_id)
            .order_by(
                SaleModel.sale_date.desc(),
                SaleModel.id.desc(),
            )
        )
        return [
            sale_to_domain(model)
            for model in self._session.scalars(statement)
        ]

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

    def _require_account(
        self, account_id: int | None, currency_code: str
    ) -> AccountModel:
        if account_id is None:
            raise AccountNotFoundError(
                "A sale requires a persisted account."
            )
        account = self._session.get(AccountModel, account_id)
        if account is None:
            raise AccountNotFoundError(
                f"Account {account_id} does not exist."
            )
        if account.currency.code != currency_code:
            raise AccountCurrencyMismatchError(
                f"Account currency {account.currency.code} does not match "
                f"sale currency {currency_code}."
            )
        if not account.is_active:
            raise InactiveAccountError(
                f"Account {account.id} is inactive."
            )
        return account

    def _require_customer(self, customer_id: int | None) -> None:
        if customer_id is None:
            return
        if self._session.get(CustomerModel, customer_id) is None:
            raise CustomerNotFoundError(
                f"Customer {customer_id} does not exist."
            )
