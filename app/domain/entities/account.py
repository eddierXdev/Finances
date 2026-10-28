"""Account entity."""

from __future__ import annotations

from dataclasses import dataclass, replace

from app.domain.entities.currency import Currency
from app.domain.value_objects.text_rules import optional_text, required_text


@dataclass(frozen=True, slots=True)
class Account:
    """An account with exactly one native currency."""

    name: str
    currency: Currency
    account_type: str | None = None
    is_active: bool = True
    notes: str | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", required_text(self.name, "Account name"))

        if not isinstance(self.currency, Currency):
            raise TypeError("Account currency must be a Currency instance.")

        object.__setattr__(
            self,
            "account_type",
            optional_text(self.account_type, "Account account_type"),
        )
        object.__setattr__(
            self, "notes", optional_text(self.notes, "Account notes")
        )

        if not isinstance(self.is_active, bool):
            raise TypeError("Account is_active must be a boolean.")

        if self.id is not None:
            if (
                isinstance(self.id, bool)
                or not isinstance(self.id, int)
                or self.id <= 0
            ):
                raise ValueError("Account id must be a positive integer.")

    def deactivate(self) -> Account:
        """Return an inactive copy; the account is never deleted."""
        return replace(self, is_active=False)

    def activate(self) -> Account:
        """Return an active copy."""
        return replace(self, is_active=True)
