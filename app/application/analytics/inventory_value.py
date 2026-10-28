"""Current inventory valuation use case."""

from __future__ import annotations

from datetime import UTC, datetime

from app.application.analytics.calculations import (
    add_money,
    money,
    totals_tuple,
)
from app.application.analytics.models import (
    AnalyticsFilters,
    InventoryValueReport,
)
from app.application.analytics.ports import AnalyticsRepository
from app.domain.value_objects.money import Money


class GetInventoryValue:
    """Sum remaining lots at their historical acquisition cost."""

    def __init__(
        self,
        analytics: AnalyticsRepository,
        *,
        clock=None,
    ) -> None:
        self._analytics = analytics
        self._clock = clock or (lambda: datetime.now(UTC))

    def execute(
        self,
        as_of: datetime | None = None,
        filters: AnalyticsFilters | None = None,
    ) -> InventoryValueReport:
        filters = filters or AnalyticsFilters()
        cutoff = as_of or self._clock()
        if cutoff.tzinfo is None or cutoff.utcoffset() is None:
            raise ValueError("Inventory as_of must be timezone-aware.")
        cutoff = cutoff.astimezone(UTC)

        records = self._analytics.list_inventory_lots(cutoff, filters)
        totals: dict[str, Money] = {}
        total_units = 0
        for record in records:
            total_units += record.remaining_quantity
            add_money(
                totals,
                money(
                    record.unit_cost * record.remaining_quantity,
                    record.currency,
                ),
            )

        return InventoryValueReport(
            as_of=cutoff,
            inventory_value=totals_tuple(totals),
            total_units=total_units,
        )
