"""Human-readable labels for domain enumerations."""

from __future__ import annotations

from app.domain.enums.allocation_method import AllocationMethod
from app.domain.enums.purchase_cost_type import PurchaseCostType
from app.domain.enums.purchase_status import PurchaseStatus


def purchase_status_label(status: PurchaseStatus) -> str:
    """Return a display label for a purchase status."""
    return status.value.replace("_", " ").title()


def purchase_cost_type_label(cost_type: PurchaseCostType) -> str:
    """Return a display label for an acquisition-cost type."""
    return cost_type.value.replace("_", " ").title()


def allocation_method_label(method: AllocationMethod) -> str:
    """Return a display label for an allocation method."""
    return method.value.replace("_", " ").capitalize()
