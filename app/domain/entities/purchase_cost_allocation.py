"""Purchase cost allocation entity."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.entities.purchase_cost import PurchaseCost
from app.domain.entities.purchase_item import PurchaseItem
from app.domain.exceptions import (
    InvalidCostAllocationError,
    PurchaseCurrencyMismatchError,
)
from app.domain.value_objects.money import Money


@dataclass(frozen=True, slots=True)
class PurchaseCostAllocation:
    """The portion of one purchase cost assigned to one purchase item."""

    purchase_cost: PurchaseCost
    purchase_item: PurchaseItem
    allocated_original_amount: Money
    allocated_purchase_currency_amount: Money
    id: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.purchase_cost, PurchaseCost) or not isinstance(
            self.purchase_item, PurchaseItem
        ):
            raise TypeError(
                "PurchaseCostAllocation requires PurchaseCost and "
                "PurchaseItem instances."
            )

        if (
            self.purchase_cost.id is None
            or self.purchase_item.id is None
        ):
            raise InvalidCostAllocationError(
                "PurchaseCostAllocation requires persisted cost and item."
            )
        if (
            self.purchase_cost.purchase.id is None
            or self.purchase_item.purchase.id is None
            or self.purchase_cost.purchase.id
            != self.purchase_item.purchase.id
        ):
            raise InvalidCostAllocationError(
                "Cost and item must belong to the same purchase."
            )

        if not isinstance(
            self.allocated_original_amount, Money
        ) or not isinstance(self.allocated_purchase_currency_amount, Money):
            raise TypeError(
                "PurchaseCostAllocation amounts must be Money."
            )

        if self.allocated_original_amount.is_negative:
            raise InvalidCostAllocationError(
                "Allocated original amount cannot be negative."
            )
        if self.allocated_purchase_currency_amount.is_negative:
            raise InvalidCostAllocationError(
                "Allocated purchase-currency amount cannot be negative."
            )

        if (
            self.allocated_original_amount.currency.code
            != self.purchase_cost.amount.currency.code
        ):
            raise PurchaseCurrencyMismatchError(
                "Allocated original amount currency must match the cost "
                "currency."
            )
        if (
            self.allocated_purchase_currency_amount.currency.code
            != self.purchase_cost.purchase.currency.code
        ):
            raise PurchaseCurrencyMismatchError(
                "Allocated normalized amount currency must match the "
                "purchase currency."
            )

        if self.id is not None:
            if (
                isinstance(self.id, bool)
                or not isinstance(self.id, int)
                or self.id <= 0
            ):
                raise ValueError(
                    "PurchaseCostAllocation id must be a positive integer."
                )
