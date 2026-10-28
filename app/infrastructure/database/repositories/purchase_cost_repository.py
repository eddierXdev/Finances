"""SQLAlchemy purchase-cost repository."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.purchase_cost import PurchaseCost
from app.domain.exceptions import (
    CurrencyNotFoundError,
    ExchangeRateNotFoundError,
    PurchaseNotFoundError,
)
from app.infrastructure.database.models import (
    CurrencyModel,
    ExchangeRateModel,
    PurchaseCostModel,
    PurchaseModel,
)
from app.infrastructure.database.repositories.mapping import (
    purchase_cost_to_domain,
)


class SqlAlchemyPurchaseCostRepository:
    """Purchase additional-cost persistence using SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, cost: PurchaseCost) -> PurchaseCost:
        if cost.purchase.id is None:
            raise ValueError(
                "Cannot add a cost to a purchase without an id."
            )

        purchase = self._require_purchase(cost.purchase.id)
        currency = self._require_currency(cost.amount.currency.code)
        exchange_rate = self._resolve_exchange_rate(cost)

        model = PurchaseCostModel(
            purchase=purchase,
            cost_type=cost.cost_type.value,
            amount=cost.amount.amount,
            currency=currency,
            exchange_rate=exchange_rate,
            allocation_method=cost.allocation_method.value,
            description=cost.description,
        )
        self._session.add(model)
        self._session.flush()
        return purchase_cost_to_domain(model)

    def get_by_id(self, cost_id: int) -> PurchaseCost | None:
        model = self._session.get(PurchaseCostModel, cost_id)
        return purchase_cost_to_domain(model) if model is not None else None

    def list_for_purchase(self, purchase_id: int) -> list[PurchaseCost]:
        statement = (
            select(PurchaseCostModel)
            .where(PurchaseCostModel.purchase_id == purchase_id)
            .order_by(PurchaseCostModel.id.asc())
        )
        return [
            purchase_cost_to_domain(model)
            for model in self._session.scalars(statement)
        ]

    def _require_purchase(self, purchase_id: int) -> PurchaseModel:
        model = self._session.get(PurchaseModel, purchase_id)
        if model is None:
            raise PurchaseNotFoundError(
                f"Purchase {purchase_id} does not exist."
            )
        return model

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

    def _resolve_exchange_rate(
        self, cost: PurchaseCost
    ) -> ExchangeRateModel | None:
        if cost.exchange_rate is None:
            return None
        if cost.exchange_rate.id is None:
            raise ValueError(
                "A foreign-currency cost requires a persisted exchange rate."
            )

        model = self._session.get(
            ExchangeRateModel, cost.exchange_rate.id
        )
        if model is None:
            raise ExchangeRateNotFoundError(
                f"Exchange rate {cost.exchange_rate.id} does not exist."
            )
        return model
