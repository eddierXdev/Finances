"""Currency entity."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.domain.value_objects.decimal_rules import MAX_DECIMAL_PLACES

_CURRENCY_CODE_PATTERN = re.compile(r"^[A-Z]{3}$")


@dataclass(frozen=True, slots=True)
class Currency:
    """A currency accepted by the application.

    ``decimal_places`` defines the precision used by :class:`Money` when it
    rounds amounts for this currency.
    """

    code: str
    name: str
    decimal_places: int
    symbol: str | None = None
    is_enabled: bool = True
    id: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.code, str):
            raise TypeError("Currency code must be a string.")

        code = self.code.strip().upper()
        if not _CURRENCY_CODE_PATTERN.fullmatch(code):
            raise ValueError(
                f"Currency code must contain exactly three letters: {self.code!r}."
            )
        object.__setattr__(self, "code", code)

        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Currency name is required.")
        object.__setattr__(self, "name", self.name.strip())

        if isinstance(self.decimal_places, bool) or not isinstance(
            self.decimal_places, int
        ):
            raise TypeError("Currency decimal_places must be an integer.")
        if not 0 <= self.decimal_places <= MAX_DECIMAL_PLACES:
            raise ValueError(
                "Currency decimal_places must be between "
                f"0 and {MAX_DECIMAL_PLACES}."
            )

        if self.symbol is not None:
            if not isinstance(self.symbol, str):
                raise TypeError("Currency symbol must be a string or None.")
            object.__setattr__(self, "symbol", self.symbol.strip() or None)

    def __str__(self) -> str:
        return self.code
