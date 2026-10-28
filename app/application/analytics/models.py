"""Read models for the analytics application layer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from app.domain.entities.currency import Currency
from app.domain.enums.expense_type import ExpenseType
from app.domain.value_objects.money import Money


def _require_aware(value: datetime, label: str) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"{label} must be a datetime.")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware.")
    return value.astimezone(UTC)


def _optional_positive_id(value: int | None, label: str) -> None:
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label} must be a positive integer or None.")


@dataclass(frozen=True, slots=True)
class AnalyticsPeriod:
    """An inclusive reporting period with optional boundaries."""

    start: datetime | None = None
    end: datetime | None = None

    def __post_init__(self) -> None:
        if self.start is not None:
            object.__setattr__(
                self, "start", _require_aware(self.start, "Period start")
            )
        if self.end is not None:
            object.__setattr__(
                self, "end", _require_aware(self.end, "Period end")
            )
        if (
            self.start is not None
            and self.end is not None
            and self.end < self.start
        ):
            raise ValueError("Period end must not be before period start.")

    def end_or(self, fallback: datetime) -> datetime:
        """Return the end boundary, or a supplied fallback instant."""
        if self.end is not None:
            return self.end
        return _require_aware(fallback, "Fallback instant")

    def opening_instant(self, fallback: datetime) -> datetime:
        """Return the start boundary, or a supplied fallback instant."""
        if self.start is not None:
            return self.start
        return _require_aware(fallback, "Fallback instant")


@dataclass(frozen=True, slots=True)
class AnalyticsFilters:
    """Optional dimensions shared by analytics queries."""

    currency_code: str | None = None
    account_id: int | None = None
    customer_id: int | None = None
    supplier_id: int | None = None
    product_id: int | None = None
    category_id: int | None = None

    def __post_init__(self) -> None:
        if self.currency_code is not None:
            if not isinstance(self.currency_code, str):
                raise TypeError("Currency filter must be a string or None.")
            normalized = self.currency_code.strip().upper()
            if not normalized:
                raise ValueError("Currency filter cannot be blank.")
            object.__setattr__(self, "currency_code", normalized)

        _optional_positive_id(self.account_id, "Account filter")
        _optional_positive_id(self.customer_id, "Customer filter")
        _optional_positive_id(self.supplier_id, "Supplier filter")
        _optional_positive_id(self.product_id, "Product filter")
        _optional_positive_id(self.category_id, "Category filter")


@dataclass(frozen=True, slots=True)
class SaleAllocationRecord:
    """One FIFO allocation of a sale item with its reporting dimensions."""

    sale_id: int
    sale_date: datetime
    sale_currency: Currency
    sale_account_id: int
    customer_id: int | None
    sale_discount_amount: Decimal
    sale_total_line_total: Decimal
    sale_item_id: int
    variant_id: int
    variant_name: str | None
    sku: str | None
    product_id: int
    product_name: str
    category_id: int | None
    item_quantity: int
    item_unit_price: Decimal
    item_discount_amount: Decimal
    allocation_id: int
    allocation_quantity: int
    allocation_unit_cost: Decimal
    cost_currency: Currency
    inventory_lot_id: int
    supplier_id: int | None
    supplier_name: str | None


@dataclass(frozen=True, slots=True)
class CustomerReturnAllocationRecord:
    """One historical allocation reversed by a customer return."""

    customer_return_id: int
    return_date: datetime
    sale_id: int
    sale_currency: Currency
    sale_account_id: int
    refund_account_id: int | None
    customer_id: int | None
    sale_discount_amount: Decimal
    sale_total_line_total: Decimal
    sale_is_same_currency: bool
    sale_item_id: int
    variant_id: int
    variant_name: str | None
    sku: str | None
    product_id: int
    product_name: str
    category_id: int | None
    item_quantity: int
    item_unit_price: Decimal
    item_discount_amount: Decimal
    return_item_id: int
    return_item_quantity: int
    return_condition: str
    return_allocation_id: int
    return_allocation_quantity: int
    return_unit_cost: Decimal
    cost_currency: Currency
    supplier_id: int | None
    supplier_name: str | None
    refund_amount: Decimal
    refund_currency: Currency | None


@dataclass(frozen=True, slots=True)
class SupplierReturnItemRecord:
    """One supplier return line with its original purchase dimensions."""

    supplier_return_id: int
    return_date: datetime
    purchase_id: int
    supplier_id: int | None
    supplier_name: str | None
    purchase_item_id: int
    variant_id: int
    variant_name: str | None
    sku: str | None
    product_id: int
    product_name: str
    category_id: int | None
    quantity: int
    unit_cost: Decimal
    cost_currency: Currency
    refund_amount: Decimal
    refund_currency: Currency | None
    account_id: int | None


@dataclass(frozen=True, slots=True)
class ExpenseRecord:
    """One operating expense in its native account currency."""

    expense_id: int
    expense_date: datetime
    account_id: int
    expense_type: ExpenseType
    amount: Decimal
    currency: Currency


@dataclass(frozen=True, slots=True)
class InventoryLotRecord:
    """Current remaining stock for one inventory lot."""

    lot_id: int
    variant_id: int
    variant_name: str | None
    sku: str | None
    product_id: int
    product_name: str
    category_id: int | None
    remaining_quantity: int
    unit_cost: Decimal
    currency: Currency
    received_at: datetime
    supplier_id: int | None
    supplier_name: str | None


@dataclass(frozen=True, slots=True)
class LastSaleRecord:
    """The latest non-cancelled sale date for one variant."""

    product_id: int
    variant_id: int
    last_sale_date: datetime


@dataclass(frozen=True, slots=True)
class CurrencyMargin:
    """Margins for one native currency."""

    currency: Currency
    gross_margin: Decimal | None
    net_margin: Decimal | None


@dataclass(frozen=True, slots=True)
class BusinessSummary:
    """Native-currency profit and loss for a period."""

    period: AnalyticsPeriod
    revenue: tuple[Money, ...]
    cogs: tuple[Money, ...]
    gross_profit: tuple[Money, ...]
    expenses: tuple[Money, ...]
    net_profit: tuple[Money, ...]
    customer_refunds: tuple[Money, ...]
    supplier_refunds: tuple[Money, ...]
    supplier_return_cost: tuple[Money, ...]
    margins: tuple[CurrencyMargin, ...]
    units_sold: int
    sale_count: int
    return_count: int
    cross_currency_sale_count: int


@dataclass(frozen=True, slots=True)
class ProductPerformance:
    """Net sales volume and revenue for one product."""

    product_id: int
    product_name: str
    category_id: int | None
    net_quantity: int
    revenue: tuple[Money, ...]


@dataclass(frozen=True, slots=True)
class ProductProfitability:
    """Net profit for one product in one native currency."""

    product_id: int
    product_name: str
    category_id: int | None
    currency: Currency
    net_quantity: int
    revenue: Money
    cogs: Money
    gross_profit: Money
    gross_margin: Decimal | None


@dataclass(frozen=True, slots=True)
class SlowMovingProduct:
    """A product with stock and no recent sale."""

    product_id: int
    product_name: str
    category_id: int | None
    remaining_quantity: int
    inventory_value: tuple[Money, ...]
    last_sale_date: datetime | None
    days_since_last_sale: int | None


@dataclass(frozen=True, slots=True)
class ProductPerformanceReport:
    """Best-selling, most profitable and slow-moving products."""

    period: AnalyticsPeriod
    best_sellers: tuple[ProductPerformance, ...]
    most_profitable: tuple[ProductProfitability, ...]
    slow_moving: tuple[SlowMovingProduct, ...]
    cross_currency_sale_count: int


@dataclass(frozen=True, slots=True)
class SupplierProfitability:
    """Native profit contribution and refunds for one supplier."""

    supplier_id: int | None
    supplier_name: str | None
    net_quantity: int
    revenue: tuple[Money, ...]
    cogs: tuple[Money, ...]
    gross_profit: tuple[Money, ...]
    customer_return_revenue: tuple[Money, ...]
    customer_return_cogs: tuple[Money, ...]
    supplier_refunds: tuple[Money, ...]
    supplier_return_cost: tuple[Money, ...]
    cross_currency_sale_count: int


@dataclass(frozen=True, slots=True)
class SupplierProfitabilityReport:
    """Supplier profitability for a period."""

    period: AnalyticsPeriod
    suppliers: tuple[SupplierProfitability, ...]


@dataclass(frozen=True, slots=True)
class InventoryValueReport:
    """Current inventory value grouped by native cost currency."""

    as_of: datetime
    inventory_value: tuple[Money, ...]
    total_units: int


@dataclass(frozen=True, slots=True)
class AccountBalance:
    """One account's native balance at a point in time."""

    account_id: int
    account_name: str
    currency: Currency
    balance: Money
    is_active: bool


@dataclass(frozen=True, slots=True)
class AccountBalancesReport:
    """Native account balances and their per-currency totals."""

    as_of: datetime
    accounts: tuple[AccountBalance, ...]
    totals: tuple[Money, ...]


@dataclass(frozen=True, slots=True)
class MissingExchangeRate:
    """A required direct rate that was not stored at the report cutoff."""

    base_code: str
    quote_code: str
    as_of: datetime


@dataclass(frozen=True, slots=True)
class ConsolidatedReport:
    """Base-currency report with native values preserved alongside it."""

    period: AnalyticsPeriod
    base_currency: Currency
    as_of: datetime
    revenue: Money
    cogs: Money
    gross_profit: Money
    expenses: Money
    net_profit: Money
    inventory_value: Money
    available_capital: Money
    invested_capital: Money
    gross_margin: Decimal | None
    net_margin: Decimal | None
    roi: Decimal | None
    roi_opening_capital: Money | None
    roi_closing_capital: Money | None
    roi_average_capital: Money | None
    missing_rates: tuple[MissingExchangeRate, ...]
    is_complete: bool
    native_summary: BusinessSummary
    native_inventory: InventoryValueReport
    native_accounts: AccountBalancesReport
