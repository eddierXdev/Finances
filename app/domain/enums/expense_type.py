"""Expense categories."""

from enum import StrEnum


class ExpenseType(StrEnum):
    """Supported operating-expense categories."""

    ADVERTISING = "ADVERTISING"
    TRANSPORTATION = "TRANSPORTATION"
    PACKAGING = "PACKAGING"
    INTERNET = "INTERNET"
    DELIVERY = "DELIVERY"
    COMMISSION = "COMMISSION"
    OTHER = "OTHER"
