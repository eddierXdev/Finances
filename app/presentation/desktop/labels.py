"""Human-readable labels for domain enumerations."""

from __future__ import annotations

from app.domain.enums.allocation_method import AllocationMethod
from app.domain.enums.capital_movement_type import CapitalMovementType
from app.domain.enums.exchange_rate_source import ExchangeRateSource
from app.domain.enums.expense_type import ExpenseType
from app.domain.enums.inventory_movement_type import InventoryMovementType
from app.domain.enums.purchase_cost_type import PurchaseCostType
from app.domain.enums.purchase_status import PurchaseStatus
from app.domain.enums.return_condition import ReturnCondition
from app.domain.enums.sale_status import SaleStatus


def purchase_status_label(status: PurchaseStatus) -> str:
    """Return a display label for a purchase status."""
    return status.value.replace("_", " ").title()


def sale_status_label(status: SaleStatus) -> str:
    """Return a display label for a sale status."""
    return status.value.replace("_", " ").title()


def inventory_movement_label(movement_type: InventoryMovementType) -> str:
    """Return a display label for an inventory movement type."""
    return movement_type.value.replace("_", " ").title()


def expense_type_label(expense_type: ExpenseType) -> str:
    """Return a display label for an expense type."""
    return expense_type.value.replace("_", " ").title()


def capital_movement_label(
    movement_type: CapitalMovementType,
) -> str:
    """Return a display label for a capital movement type."""
    return movement_type.value.replace("_", " ").title()


def return_condition_label(condition: ReturnCondition) -> str:
    """Return a display label for a return condition."""
    return condition.value.replace("_", " ").title()


def exchange_rate_source_label(source: ExchangeRateSource) -> str:
    """Return a display label for an exchange-rate source."""
    return source.value.replace("_", " ").title()


def purchase_cost_type_label(cost_type: PurchaseCostType) -> str:
    """Return a display label for an acquisition-cost type."""
    return cost_type.value.replace("_", " ").title()


def allocation_method_label(method: AllocationMethod) -> str:
    """Return a display label for an allocation method."""
    return method.value.replace("_", " ").capitalize()
