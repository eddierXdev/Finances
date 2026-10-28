"""Currency repository contract."""

from typing import Protocol

from app.domain.entities.currency import Currency


class CurrencyRepository(Protocol):
    """Persistence boundary for currencies."""

    def add(self, currency: Currency) -> Currency:
        """Persist a currency and return it with its assigned identifier."""
        ...

    def get_by_code(self, code: str) -> Currency | None:
        """Return a currency by its code, if it exists."""
        ...

    def list_all(self, *, enabled_only: bool = False) -> list[Currency]:
        """Return all currencies, optionally filtering disabled ones out."""
        ...
