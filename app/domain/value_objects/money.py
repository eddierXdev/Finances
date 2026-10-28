"""Money value object."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from functools import total_ordering

from app.domain.entities.currency import Currency
from app.domain.exceptions import CurrencyMismatchError
from app.domain.value_objects.decimal_rules import quantize_amount, to_decimal


@total_ordering
@dataclass(frozen=True, slots=True, eq=False)
class Money:
    """An immutable monetary amount in a specific currency.

    Amounts are rounded half-up to the currency precision on construction.
    Arithmetic is only allowed between amounts in the same currency.
    """

    amount: Decimal
    currency: Currency

    def __post_init__(self) -> None:
        if not isinstance(self.currency, Currency):
            raise TypeError("Money requires a Currency instance.")

        amount = to_decimal(self.amount)
        object.__setattr__(
            self,
            "amount",
            quantize_amount(amount, self.currency.decimal_places),
        )

    @classmethod
    def zero(cls, currency: Currency) -> Money:
        """Return zero in ``currency``."""
        return cls(Decimal("0"), currency)

    @property
    def currency_code(self) -> str:
        return self.currency.code

    @property
    def is_zero(self) -> bool:
        return self.amount == 0

    @property
    def is_positive(self) -> bool:
        return self.amount > 0

    @property
    def is_negative(self) -> bool:
        return self.amount < 0

    def _require_same_currency(self, other: Money) -> None:
        if self.currency.code != other.currency.code:
            raise CurrencyMismatchError(
                "Cannot combine amounts in different currencies: "
                f"{self.currency.code} and {other.currency.code}."
            )

    def __add__(self, other: object) -> Money:
        if not isinstance(other, Money):
            return NotImplemented
        self._require_same_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: object) -> Money:
        if not isinstance(other, Money):
            return NotImplemented
        self._require_same_currency(other)
        return Money(self.amount - other.amount, self.currency)

    def __mul__(self, factor: Decimal | int | str) -> Money:
        return Money(self.amount * to_decimal(factor), self.currency)

    def __rmul__(self, factor: Decimal | int | str) -> Money:
        return self * factor

    def __truediv__(self, divisor: Decimal | int | str) -> Money:
        divisor_value = to_decimal(divisor)
        if divisor_value == 0:
            raise ZeroDivisionError("Cannot divide money by zero.")
        return Money(self.amount / divisor_value, self.currency)

    def __neg__(self) -> Money:
        return Money(-self.amount, self.currency)

    def __abs__(self) -> Money:
        return Money(abs(self.amount), self.currency)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        return (
            self.currency.code == other.currency.code
            and self.amount == other.amount
        )

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        self._require_same_currency(other)
        return self.amount < other.amount

    def __hash__(self) -> int:
        return hash((self.currency.code, self.amount))

    def __str__(self) -> str:
        return (
            f"{self.amount:.{self.currency.decimal_places}f} "
            f"{self.currency.code}"
        )

    def __repr__(self) -> str:
        return f"Money({self.amount!r}, {self.currency.code!r})"
