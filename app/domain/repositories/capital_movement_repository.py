"""Capital movement repository contract."""

from typing import Protocol

from app.domain.entities.capital_movement import CapitalMovement


class CapitalMovementRepository(Protocol):
    """Append-only persistence boundary for capital history."""

    def add(self, movement: CapitalMovement) -> CapitalMovement:
        """Persist a capital movement."""
        ...

    def get_by_id(self, movement_id: int) -> CapitalMovement | None:
        """Return a capital movement by identifier, if it exists."""
        ...

    def list_for_account(self, account_id: int) -> list[CapitalMovement]:
        """Return an account's capital history, oldest first."""
        ...
