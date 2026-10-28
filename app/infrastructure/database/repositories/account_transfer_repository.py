"""SQLAlchemy account-transfer repository (append-only)."""

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.domain.entities.account_transfer import AccountTransfer
from app.domain.exceptions import (
    AccountNotFoundError,
    ExchangeRateNotFoundError,
)
from app.infrastructure.database.models import (
    AccountModel,
    AccountTransferModel,
    ExchangeRateModel,
)
from app.infrastructure.database.repositories.mapping import (
    account_transfer_to_domain,
)


class SqlAlchemyAccountTransferRepository:
    """Transfer persistence using SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, transfer: AccountTransfer) -> AccountTransfer:
        if (
            transfer.source_account.id is None
            or transfer.destination_account.id is None
        ):
            raise ValueError(
                "Cannot record a transfer between accounts without ids."
            )

        source = self._require_account(
            transfer.source_account.id, "Source account"
        )
        destination = self._require_account(
            transfer.destination_account.id, "Destination account"
        )
        exchange_rate = self._resolve_exchange_rate(transfer)

        model = AccountTransferModel(
            source_account=source,
            destination_account=destination,
            source_amount=transfer.source_amount.amount,
            destination_amount=transfer.destination_amount.amount,
            exchange_rate=exchange_rate,
            transfer_date=transfer.transfer_date,
            notes=transfer.notes,
        )
        self._session.add(model)
        self._session.flush()
        return account_transfer_to_domain(model)

    def get_by_id(self, transfer_id: int) -> AccountTransfer | None:
        model = self._session.get(AccountTransferModel, transfer_id)
        return account_transfer_to_domain(model) if model is not None else None

    def list_for_account(self, account_id: int) -> list[AccountTransfer]:
        statement = (
            select(AccountTransferModel)
            .where(
                or_(
                    AccountTransferModel.source_account_id == account_id,
                    AccountTransferModel.destination_account_id == account_id,
                )
            )
            .order_by(
                AccountTransferModel.transfer_date.desc(),
                AccountTransferModel.id.desc(),
            )
        )
        return [
            account_transfer_to_domain(model)
            for model in self._session.scalars(statement)
        ]

    def _require_account(
        self, account_id: int, label: str
    ) -> AccountModel:
        model = self._session.get(AccountModel, account_id)
        if model is None:
            raise AccountNotFoundError(
                f"{label} {account_id} does not exist."
            )
        return model

    def _resolve_exchange_rate(
        self, transfer: AccountTransfer
    ) -> ExchangeRateModel | None:
        if transfer.exchange_rate is None:
            return None
        if transfer.exchange_rate.id is None:
            raise ValueError(
                "Cross-currency transfers require a persisted exchange rate."
            )

        model = self._session.get(
            ExchangeRateModel, transfer.exchange_rate.id
        )
        if model is None:
            raise ExchangeRateNotFoundError(
                f"Exchange rate {transfer.exchange_rate.id} does not exist."
            )
        return model
