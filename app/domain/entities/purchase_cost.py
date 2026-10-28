"""Purchase additional-cost entity."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.entities.exchange_rate import ExchangeRate
from app.domain.entities.purchase import Purchase
from app.domain.enums.allocation_method import AllocationMethod
from app.domain.enums.purchase_cost_type import PurchaseCostType
from app.domain.exceptions import InvalidPurchaseError
from app.domain.value_objects.money import Money
from app.domain.value_objects.text_rules import optional_text


@dataclass(frozen=True, slots=True)
class PurchaseCost:
    """An acquisition cost with its original and normalized currency data."""

    purchase: Purchase
    cost_type: PurchaseCostType
    amount: Money
    allocation_method: AllocationMethod
    exchange_rate: ExchangeRate | None = None
    description: str | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.purchase, Purchase):
            raise TypeError("PurchaseCost requires a Purchase.")
        if not isinstance(self.amount, Money):
            raise TypeError("PurchaseCost amount must be Money.")
        if not self.amount.is_positive:
            raise InvalidPurchaseError(
                "PurchaseCost amount must be greater than zero."
            )
        if not isinstance(self.cost_type, PurchaseCostType):
            raise TypeError(
                "PurchaseCost cost_type must be a PurchaseCostType."
            )
        if not isinstance(self.allocation_method, AllocationMethod):
            raise TypeError(
                "PurchaseCost allocation_method must be an AllocationMethod."
            )

        same_currency = (
            self.amount.currency.code == self.purchase.currency.code
        )
        if same_currency:
            if self.exchange_rate is not None:
                raise InvalidPurchaseError(
                    "A same-currency purchase cost must not use an exchange "
                    "rate."
                )
        else:
            if not isinstance(self.exchange_rate, ExchangeRate):
                raise InvalidPurchaseError(
                    "A foreign-currency purchase cost requires a historical "
                    "exchange rate."
                )
            if (
                self.exchange_rate.base_currency.code
                != self.amount.currency.code
                or self.exchange_rate.quote_currency.code
                != self.purchase.currency.code
            ):
                raise InvalidPurchaseError(
                    "The purchase-cost exchange rate must convert the cost "
                    "currency into the purchase currency."
                )

        object.__setattr__(
            self,
            "description",
            optional_text(self.description, "PurchaseCost description"),
        )

        if self.id is not None:
            if (
                isinstance(self.id, bool)
                or not isinstance(self.id, int)
                or self.id <= 0
            ):
                raise ValueError(
                    "PurchaseCost id must be a positive integer."
                )

    @property
    def normalized_amount(self) -> Money:
        """Return the amount in the purchase currency."""
        if self.amount.currency.code == self.purchase.currency.code:
            return self.amount
        if self.exchange_rate is None:
            raise InvalidPurchaseError(
                "A foreign-currency cost has no exchange rate."
            )
        return self.exchange_rate.convert(self.amount)
