"""SQLAlchemy capital-movement repository (append-only)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.capital_movement import CapitalMovement
from app.domain.exceptions import AccountNotFoundError
from app.infrastructure.database.models import AccountModel, CapitalMovementModel
from app.infrastructure.database.repositories.mapping import (
    capital_movement_to_domain,
)


class SqlAlchemyCapitalMovementRepository:
    """Capital history persistence using SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, movement: CapitalMovement) -> CapitalMovement:
        if movement.account.id is None:
            raise ValueError(
                "Cannot record capital for an account without an id."
            )

        account = self._session.get(AccountModel, movement.account.id)
        if account is None:
            raise AccountNotFoundError(
                f"Account {movement.account.id} does not exist."
            )

        model = CapitalMovementModel(
            account=account,
            movement_type=movement.movement_type.value,
            amount=movement.amount.amount,
            currency=account.currency,
            movement_date=movement.movement_date,
            notes=movement.notes,
        )
        self._session.add(model)
        self._session.flush()
        return capital_movement_to_domain(model)

    def get_by_id(self, movement_id: int) -> CapitalMovement | None:
        model = self._session.get(CapitalMovementModel, movement_id)
        return capital_movement_to_domain(model) if model is not None else None

    def list_for_account(self, account_id: int) -> list[CapitalMovement]:
        statement = (
            select(CapitalMovementModel)
            .where(CapitalMovementModel.account_id == account_id)
            .order_by(
                CapitalMovementModel.movement_date.asc(),
                CapitalMovementModel.id.asc(),
            )
        )
        return [
            capital_movement_to_domain(model)
            for model in self._session.scalars(statement)
        ]
