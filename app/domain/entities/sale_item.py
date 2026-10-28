"""Sale item entity."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.entities.sale import Sale
from app.domain.exceptions import (
    InvalidSaleError,
    SaleCurrencyMismatchError,
)
from app.domain.value_objects.money import Money


@dataclass(frozen=True, slots=True)
class SaleItem:
    """A quantity of one variant sold at a unit price."""

    sale: Sale
    variant_id: int
    quantity: int
    unit_price: Money
    discount_amount: Money | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.sale, Sale):
            raise TypeError("SaleItem requires a Sale.")

        if (
            isinstance(self.variant_id, bool)
            or not isinstance(self.variant_id, int)
            or self.variant_id <= 0
        ):
            raise InvalidSaleError(
                "SaleItem variant_id must be a positive integer."
            )

        if (
            isinstance(self.quantity, bool)
            or not isinstance(self.quantity, int)
            or self.quantity <= 0
        ):
            raise InvalidSaleError(
                "SaleItem quantity must be a positive integer."
            )

        if not isinstance(self.unit_price, Money):
            raise TypeError("SaleItem unit_price must be Money.")
        if self.unit_price.is_negative:
            raise InvalidSaleError(
                "SaleItem unit_price cannot be negative."
            )
        if self.unit_price.currency.code != self.sale.currency.code:
            raise SaleCurrencyMismatchError(
                f"Unit price currency {self.unit_price.currency.code} does "
                f"not match sale currency {self.sale.currency.code}."
            )

        subtotal = self.unit_price * self.quantity
        if self.discount_amount is not None:
            if not isinstance(self.discount_amount, Money):
                raise TypeError("SaleItem discount_amount must be Money.")
            if self.discount_amount.is_negative:
                raise InvalidSaleError(
                    "SaleItem discount_amount cannot be negative."
                )
            if (
                self.discount_amount.currency.code
                != self.sale.currency.code
            ):
                raise SaleCurrencyMismatchError(
                    f"Discount currency "
                    f"{self.discount_amount.currency.code} does not match "
                    f"sale currency {self.sale.currency.code}."
                )
            if self.discount_amount > subtotal:
                raise InvalidSaleError(
                    "SaleItem discount_amount cannot exceed the line "
                    "subtotal."
                )

        if self.id is not None:
            if (
                isinstance(self.id, bool)
                or not isinstance(self.id, int)
                or self.id <= 0
            ):
                raise ValueError("SaleItem id must be a positive integer.")

    @property
    def sale_id(self) -> int | None:
        return self.sale.id

    @property
    def subtotal(self) -> Money:
        return self.unit_price * self.quantity

    @property
    def line_total(self) -> Money:
        discount = (
            self.discount_amount
            if self.discount_amount is not None
            else Money.zero(self.sale.currency)
        )
        return self.subtotal - discount
