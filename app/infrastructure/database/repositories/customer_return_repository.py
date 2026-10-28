"""SQLAlchemy customer return repository."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.customer_return import CustomerReturn
from app.domain.exceptions import (
    AccountCurrencyMismatchError,
    AccountNotFoundError,
    InactiveAccountError,
    SaleNotFoundError,
)
from app.infrastructure.database.models import (
    AccountModel,
    CustomerReturnModel,
    SaleModel,
)
from app.infrastructure.database.repositories.mapping import (
    customer_return_to_domain,
)


class SqlAlchemyCustomerReturnRepository:
    """Customer return header persistence using SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, customer_return: CustomerReturn) -> CustomerReturn:
        if customer_return.sale.id is None:
            raise ValueError(
                "Cannot persist a return without a persisted sale."
            )

        sale = self._require_sale(customer_return.sale.id)
        account = None
        refund_currency = None
        if customer_return.refund_amount is not None:
            if customer_return.account is None:
                raise ValueError(
                    "A customer refund requires a persisted account."
                )
            account = self._require_account(
                customer_return.account.id, sale.currency.code
            )
            refund_currency = sale.currency

        model = CustomerReturnModel(
            sale=sale,
            account=account,
            refund_amount=(
                customer_return.refund_amount.amount
                if customer_return.refund_amount is not None
                else None
            ),
            refund_currency=refund_currency,
            return_date=customer_return.return_date,
            notes=customer_return.notes,
        )
        self._session.add(model)
        self._session.flush()
        return customer_return_to_domain(model)

    def get_by_id(self, return_id: int) -> CustomerReturn | None:
        model = self._session.get(CustomerReturnModel, return_id)
        return (
            customer_return_to_domain(model)
            if model is not None
            else None
        )

    def list_all(self) -> list[CustomerReturn]:
        statement = select(CustomerReturnModel).order_by(
            CustomerReturnModel.return_date.desc(),
            CustomerReturnModel.id.desc(),
        )
        return [
            customer_return_to_domain(model)
            for model in self._session.scalars(statement)
        ]

    def list_for_sale(self, sale_id: int) -> list[CustomerReturn]:
        statement = (
            select(CustomerReturnModel)
            .where(CustomerReturnModel.sale_id == sale_id)
            .order_by(
                CustomerReturnModel.return_date.asc(),
                CustomerReturnModel.id.asc(),
            )
        )
        return [
            customer_return_to_domain(model)
            for model in self._session.scalars(statement)
        ]

    def _require_sale(self, sale_id: int) -> SaleModel:
        model = self._session.get(SaleModel, sale_id)
        if model is None:
            raise SaleNotFoundError(f"Sale {sale_id} does not exist.")
        return model

    def _require_account(
        self, account_id: int | None, currency_code: str
    ) -> AccountModel:
        if account_id is None:
            raise AccountNotFoundError(
                "A customer refund requires a persisted account."
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
