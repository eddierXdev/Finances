"""Customer repository contract.

Customer CRUD belongs to a later phase; sales only need existence checks so
an optional customer reference can be validated before writing.
"""

from typing import Protocol


class CustomerRepository(Protocol):
    """Persistence boundary for customer references."""

    def exists(self, customer_id: int) -> bool:
        """Return whether a customer exists."""
        ...
