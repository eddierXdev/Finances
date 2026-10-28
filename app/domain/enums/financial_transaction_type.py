"""Financial ledger transaction types."""

from enum import StrEnum


class FinancialTransactionType(StrEnum):
    """Traceable financial movements."""

    CAPITAL_CONTRIBUTION = "CAPITAL_CONTRIBUTION"
    CAPITAL_WITHDRAWAL = "CAPITAL_WITHDRAWAL"
    PURCHASE = "PURCHASE"
    SALE = "SALE"
    EXPENSE = "EXPENSE"
    CUSTOMER_REFUND = "CUSTOMER_REFUND"
    SUPPLIER_REFUND = "SUPPLIER_REFUND"
    TRANSFER = "TRANSFER"
    CURRENCY_EXCHANGE = "CURRENCY_EXCHANGE"
    ADJUSTMENT = "ADJUSTMENT"
