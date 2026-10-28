"""Customer return line entity."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.entities.customer_return import CustomerReturn
from app.domain.entities.sale_item import SaleItem
from app.domain.enums.return_condition import ReturnCondition
from app.domain.exceptions import InvalidCustomerReturnError


@dataclass(frozen=True, slots=True)
class CustomerReturnItem:
    """A quantity of one original sale item returned by the customer."""

    customer_return: CustomerReturn
    sale_item: SaleItem
    quantity: int
    condition: ReturnCondition
    id: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.customer_return, CustomerReturn):
            raise TypeError(
                "CustomerReturnItem requires a CustomerReturn."
            )
        if not isinstance(self.sale_item, SaleItem):
            raise TypeError("CustomerReturnItem requires a SaleItem.")

        if self.sale_item.id is None:
            raise InvalidCustomerReturnError(
                "CustomerReturnItem requires a persisted sale item."
            )

        if self.customer_return.sale.id != self.sale_item.sale.id:
            raise InvalidCustomerReturnError(
                "A returned item must belong to the original sale."
            )

        if (
            isinstance(self.quantity, bool)
            or not isinstance(self.quantity, int)
            or self.quantity <= 0
        ):
            raise InvalidCustomerReturnError(
                "CustomerReturnItem quantity must be a positive integer."
            )

        if not isinstance(self.condition, ReturnCondition):
            raise TypeError(
                "CustomerReturnItem condition must be a ReturnCondition."
            )

        if self.id is not None:
            if (
                isinstance(self.id, bool)
                or not isinstance(self.id, int)
                or self.id <= 0
            ):
                raise ValueError(
                    "CustomerReturnItem id must be a positive integer."
                )

    @property
    def customer_return_id(self) -> int | None:
        return self.customer_return.id

    @property
    def sale_item_id(self) -> int | None:
        return self.sale_item.id
