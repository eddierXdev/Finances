"""Currency compatibility rules for direct financial operations."""

from app.domain.entities.currency import Currency
from app.domain.exceptions import AccountCurrencyMismatchError


def ensure_account_currency_matches(
    account_currency: Currency,
    operation_currency: Currency,
) -> None:
    """Require an account's native currency to equal the operation currency.

    V1 never converts currencies implicitly. Moving funds between currencies
    requires an explicit exchange operation.
    """
    if account_currency.code != operation_currency.code:
        raise AccountCurrencyMismatchError(
            f"Account currency {account_currency.code} does not match "
            f"operation currency {operation_currency.code}."
        )
