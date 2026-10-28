"""Update purchase logistics status use case."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.entities.purchase import Purchase
from app.domain.enums.purchase_status import PurchaseStatus
from app.domain.exceptions import (
    InvalidPurchaseTransitionError,
    PurchaseNotFoundError,
)
from app.domain.repositories.purchase_repository import PurchaseRepository

_NON_LOGISTICS_TARGETS = frozenset(
    {
        PurchaseStatus.PURCHASED,
        PurchaseStatus.PARTIALLY_RECEIVED,
        PurchaseStatus.RECEIVED,
    }
)


@dataclass(frozen=True, slots=True)
class UpdatePurchaseStatusRequest:
    """Input for a purchase logistics status transition."""

    purchase_id: int
    status: PurchaseStatus


class UpdatePurchaseStatus:
    """Apply a non-financial logistics status transition.

    Payment and receipt statuses have dedicated use cases and cannot be set
    through this operation.
    """

    def __init__(self, purchases: PurchaseRepository) -> None:
        self._purchases = purchases

    def execute(self, request: UpdatePurchaseStatusRequest) -> Purchase:
        if request.status in _NON_LOGISTICS_TARGETS:
            raise InvalidPurchaseTransitionError(
                f"Status {request.status.value} must be set through its "
                "financial or receiving use case."
            )

        purchase = self._purchases.get_by_id(request.purchase_id)
        if purchase is None:
            raise PurchaseNotFoundError(
                f"Purchase {request.purchase_id} does not exist."
            )

        updated = purchase.transition_to(request.status)
        return self._purchases.save(updated)
