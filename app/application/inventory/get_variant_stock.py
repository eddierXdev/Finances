"""Current sellable stock queries."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.exceptions import InvalidInventoryError, VariantNotFoundError
from app.domain.repositories.inventory_lot_repository import (
    InventoryLotRepository,
)
from app.domain.repositories.product_variant_repository import (
    ProductVariantRepository,
)


@dataclass(frozen=True, slots=True)
class VariantStock:
    """Current sellable stock for one product variant."""

    variant_id: int
    quantity: int


class GetVariantStock:
    """Return a variant's current stock derived from lot remainders."""

    def __init__(
        self,
        variants: ProductVariantRepository,
        lots: InventoryLotRepository,
    ) -> None:
        self._variants = variants
        self._lots = lots

    def execute(self, variant_id: int) -> VariantStock:
        if (
            isinstance(variant_id, bool)
            or not isinstance(variant_id, int)
            or variant_id <= 0
        ):
            raise InvalidInventoryError(
                "variant_id must be a positive integer."
            )
        if self._variants.get_by_id(variant_id) is None:
            raise VariantNotFoundError(
                f"Product variant {variant_id} does not exist."
            )
        return VariantStock(
            variant_id=variant_id,
            quantity=self._lots.total_remaining_by_variant(variant_id),
        )
