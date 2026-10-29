"""Desktop navigation definition.

The shell owns navigation; screens are added incrementally around completed
use cases. Keys are stable identifiers used by tests and by the screen factory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NavigationItem:
    """One entry in the main navigation sidebar."""

    key: str
    title: str
    description: str


NAVIGATION_ITEMS: tuple[NavigationItem, ...] = (
    NavigationItem(
        key="dashboard",
        title="Dashboard",
        description="Business overview, capital and profit at a glance.",
    ),
    NavigationItem(
        key="products",
        title="Products",
        description="Categories, products, variants and attributes.",
    ),
    NavigationItem(
        key="accounts",
        title="Accounts",
        description="Cash, bank and wallet accounts with their balances.",
    ),
    NavigationItem(
        key="purchases",
        title="Purchases",
        description="Supplier purchases, acquisition costs and payments.",
    ),
    NavigationItem(
        key="receiving",
        title="Receiving",
        description="Partial and complete purchase receipts into inventory lots.",
    ),
    NavigationItem(
        key="inventory",
        title="Inventory",
        description="Current stock, lots and movement history.",
    ),
    NavigationItem(
        key="sales",
        title="Sales",
        description="Fully paid sales with FIFO allocation and COGS.",
    ),
    NavigationItem(
        key="returns",
        title="Returns",
        description="Customer and supplier returns with refunds.",
    ),
    NavigationItem(
        key="expenses",
        title="Expenses & Capital",
        description="Operating expenses, contributions and withdrawals.",
    ),
    NavigationItem(
        key="currency",
        title="Currency Rates",
        description="Manual rates, stored observations and freshness.",
    ),
    NavigationItem(
        key="analytics",
        title="Analytics",
        description="Revenue, profit, inventory value and product performance.",
    ),
    NavigationItem(
        key="settings",
        title="Settings",
        description="Application preferences, backup and restore.",
    ),
)
