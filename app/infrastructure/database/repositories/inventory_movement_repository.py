"""SQLAlchemy inventory-movement repository."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.inventory_movement import InventoryMovement
from app.domain.exceptions import (
    CurrencyNotFoundError,
    InventoryLotNotFoundError,
    InvalidInventoryMovementError,
    VariantNotFoundError,
)
from app.infrastructure.database.models import (
    CurrencyModel,
    InventoryLotModel,
    InventoryMovementModel,
    ProductVariantModel,
)
from app.infrastructure.database.repositories.mapping import (
    inventory_movement_to_domain,
)


class SqlAlchemyInventoryMovementRepository:
    """Inventory movement persistence using SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, movement: InventoryMovement) -> InventoryMovement:
        self._require_variant(movement.variant_id)

        lot = None
        if movement.inventory_lot_id is not None:
            lot = self._session.get(
                InventoryLotModel, movement.inventory_lot_id
            )
            if lot is None:
                raise InventoryLotNotFoundError(
                    f"Inventory lot {movement.inventory_lot_id} does not "
                    "exist."
                )
            if lot.variant_id != movement.variant_id:
                raise InvalidInventoryMovementError(
                    "A movement's variant must match its inventory lot."
                )

        currency = None
        if movement.unit_cost is not None:
            currency = self._require_currency(
                movement.unit_cost.currency.code
            )

        model = InventoryMovementModel(
            variant_id=movement.variant_id,
            inventory_lot=lot,
            movement_type=movement.movement_type.value,
            quantity=movement.quantity,
            unit_cost=(
                movement.unit_cost.amount
                if movement.unit_cost is not None
                else None
            ),
            currency=currency,
            reference_type=movement.reference_type,
            reference_id=movement.reference_id,
            movement_date=movement.movement_date,
            notes=movement.notes,
        )
        self._session.add(model)
        self._session.flush()
        return inventory_movement_to_domain(model)

    def get_by_id(self, movement_id: int) -> InventoryMovement | None:
        model = self._session.get(InventoryMovementModel, movement_id)
        return (
            inventory_movement_to_domain(model)
            if model is not None
            else None
        )

    def list_by_variant(self, variant_id: int) -> list[InventoryMovement]:
        statement = (
            select(InventoryMovementModel)
            .where(InventoryMovementModel.variant_id == variant_id)
            .order_by(
                InventoryMovementModel.movement_date.asc(),
                InventoryMovementModel.id.asc(),
            )
        )
        return [
            inventory_movement_to_domain(model)
            for model in self._session.scalars(statement)
        ]

    def list_for_lot(self, lot_id: int) -> list[InventoryMovement]:
        statement = (
            select(InventoryMovementModel)
            .where(InventoryMovementModel.inventory_lot_id == lot_id)
            .order_by(
                InventoryMovementModel.movement_date.asc(),
                InventoryMovementModel.id.asc(),
            )
        )
        return [
            inventory_movement_to_domain(model)
            for model in self._session.scalars(statement)
        ]

    def _require_variant(self, variant_id: int) -> None:
        if self._session.get(ProductVariantModel, variant_id) is None:
            raise VariantNotFoundError(
                f"Product variant {variant_id} does not exist."
            )

    def _require_currency(self, code: str) -> CurrencyModel:
        normalized_code = code.strip().upper()
        model = self._session.scalar(
            select(CurrencyModel).where(
                CurrencyModel.code == normalized_code
            )
        )
        if model is None:
            raise CurrencyNotFoundError(
                f"Currency {normalized_code} is not registered."
            )
        return model
