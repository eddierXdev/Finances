"""Account transfer entity, including explicit currency exchange."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.domain.entities.account import Account
from app.domain.entities.exchange_rate import ExchangeRate
from app.domain.exceptions import (
    AccountCurrencyMismatchError,
    InvalidTransferError,
)
from app.domain.value_objects.money import Money
from app.domain.value_objects.text_rules import optional_text


@dataclass(frozen=True, slots=True)
class AccountTransfer:
    """A movement between two accounts.

    Same-currency transfers keep identical amounts. Cross-currency transfers
    require a historical exchange rate and preserve both native amounts.
    """

    source_account: Account
    destination_account: Account
    source_amount: Money
    destination_amount: Money
    transfer_date: datetime
    exchange_rate: ExchangeRate | None = None
    notes: str | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.source_account, Account) or not isinstance(
            self.destination_account, Account
        ):
            raise TypeError("AccountTransfer requires Account instances.")

        if (
            self.source_account.id is None
            or self.destination_account.id is None
        ):
            raise InvalidTransferError(
                "AccountTransfer requires persisted accounts."
            )
        if self.source_account.id == self.destination_account.id:
            raise InvalidTransferError(
                "Source and destination accounts must be different."
            )

        if not isinstance(self.source_amount, Money) or not isinstance(
            self.destination_amount, Money
        ):
            raise TypeError("AccountTransfer amounts must be Money.")

        if (
            self.source_amount.currency.code
            != self.source_account.currency.code
        ):
            raise AccountCurrencyMismatchError(
                f"Source amount {self.source_amount.currency.code} does not "
                f"match source account currency "
                f"{self.source_account.currency.code}."
            )
        if (
            self.destination_amount.currency.code
            != self.destination_account.currency.code
        ):
            raise AccountCurrencyMismatchError(
                f"Destination amount "
                f"{self.destination_amount.currency.code} does not match "
                f"destination account currency "
                f"{self.destination_account.currency.code}."
            )

        if not self.source_amount.is_positive:
            raise InvalidTransferError(
                "Source amount must be greater than zero."
            )
        if not self.destination_amount.is_positive:
            raise InvalidTransferError(
                "Destination amount must be greater than zero."
            )

        if not isinstance(self.transfer_date, datetime):
            raise TypeError("AccountTransfer date must be a datetime.")
        if (
            self.transfer_date.tzinfo is None
            or self.transfer_date.utcoffset() is None
        ):
            raise InvalidTransferError(
                "AccountTransfer date must be timezone-aware."
            )
        object.__setattr__(
            self, "transfer_date", self.transfer_date.astimezone(UTC)
        )

        same_currency = (
            self.source_account.currency.code
            == self.destination_account.currency.code
        )

        if same_currency:
            if self.exchange_rate is not None:
                raise InvalidTransferError(
                    "Same-currency transfers must not use an exchange rate."
                )
            if self.source_amount != self.destination_amount:
                raise InvalidTransferError(
                    "Same-currency transfers must preserve the amount."
                )
        else:
            if not isinstance(self.exchange_rate, ExchangeRate):
                raise InvalidTransferError(
                    "Cross-currency transfers require a historical exchange "
                    "rate."
                )
            if (
                self.exchange_rate.base_currency.code
                != self.source_account.currency.code
                or self.exchange_rate.quote_currency.code
                != self.destination_account.currency.code
            ):
                raise InvalidTransferError(
                    "Exchange rate currencies must match the source and "
                    "destination accounts."
                )
            expected_destination = self.exchange_rate.convert(
                self.source_amount
            )
            if expected_destination != self.destination_amount:
                raise InvalidTransferError(
                    "Destination amount does not match the historical "
                    "exchange rate."
                )

        object.__setattr__(
            self, "notes", optional_text(self.notes, "AccountTransfer notes")
        )

        if self.id is not None:
            if (
                isinstance(self.id, bool)
                or not isinstance(self.id, int)
                or self.id <= 0
            ):
                raise ValueError(
                    "AccountTransfer id must be a positive integer."
                )

    @property
    def is_cross_currency(self) -> bool:
        return (
            self.source_account.currency.code
            != self.destination_account.currency.code
        )
