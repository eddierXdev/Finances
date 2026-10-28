"""Purchase item entity."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.domain.entities.purchase import Purchase
from app.domain.exceptions import PurchaseCurrencyMismatchError
from app.domain.value_objects.decimal_rules import quantize_amount, to_decimal
from app.domain.value_objects.money import Money

_WEIGHT_DECIMAL_PLACES = 6


@dataclass(frozen=True, slots=True)
class PurchaseItem:
    """An ordered quantity of one product variant."""

    purchase: Purchase
    variant_id: int
    quantity: int
    unit_price: Money
    weight: Decimal | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.purchase, Purchase):
            raise TypeError("PurchaseItem requires a Purchase.")

        if (
            isinstance(self.variant_id, bool)
            or not isinstance(self.variant_id, int)
            or self.variant_id <= 0
        ):
            raise ValueError(
                "PurchaseItem variant_id must be a positive integer."
            )

        if (
            isinstance(self.quantity, bool)
            or not isinstance(self.quantity, int)
            or self.quantity <= 0
        ):
            raise ValueError(
                "PurchaseItem quantity must be a positive integer."
            )

        if not isinstance(self.unit_price, Money):
            raise TypeError("PurchaseItem unit_price must be Money.")
        if self.unit_price.is_negative:
            raise ValueError(
                "PurchaseItem unit_price cannot be negative."
            )
        if self.unit_price.currency.code != self.purchase.currency.code:
            raise PurchaseCurrencyMismatchError(
                f"Unit price currency {self.unit_price.currency.code} does "
                f"not match purchase currency "
                f"{self.purchase.currency.code}."
            )

        if self.weight is not None:
            weight = to_decimal(self.weight)
            if weight <= 0:
                raise ValueError(
                    "PurchaseItem weight must be greater than zero when "
                    "present."
                )
            object.__setattr__(
                self,
                "weight",
                quantize_amount(weight, _WEIGHT_DECIMAL_PLACES),
            )

        if self.id is not None:
            if (
                isinstance(self.id, bool)
                or not isinstance(self.id, int)
                or self.id <= 0
            ):
                raise ValueError(
                    "PurchaseItem id must be a positive integer."
                )

    @property
    def purchase_id(self) -> int | None:
        return self.purchase.id

    @property
    def line_total(self) -> Money:
        return self.unit_price * self.quantity
