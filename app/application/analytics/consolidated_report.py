"""Base-currency consolidated reporting use case."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal

from app.application.analytics.account_balances import GetAccountBalances
from app.application.analytics.business_summary import GetBusinessSummary
from app.application.analytics.calculations import add_money, percentage
from app.application.analytics.conversion import BaseCurrencyConverter
from app.application.analytics.inventory_value import GetInventoryValue
from app.application.analytics.models import (
    AnalyticsFilters,
    AnalyticsPeriod,
    ConsolidatedReport,
)
from app.domain.exceptions import CurrencyNotFoundError
from app.domain.repositories.capital_movement_repository import (
    CapitalMovementRepository,
)
from app.domain.repositories.currency_repository import CurrencyRepository
from app.domain.repositories.exchange_rate_repository import (
    ExchangeRateRepository,
)
from app.domain.value_objects.money import Money

_ROI_QUANTUM = Decimal("0.0001")


class GetConsolidatedReport:
    """Convert native analytics into the configured reporting currency."""

    def __init__(
        self,
        summary: GetBusinessSummary,
        inventory: GetInventoryValue,
        accounts: GetAccountBalances,
        currencies: CurrencyRepository,
        exchange_rates: ExchangeRateRepository,
        capital_movements: CapitalMovementRepository,
        *,
        base_currency: str = "USD",
        clock=None,
    ) -> None:
        self._summary = summary
        self._inventory = inventory
        self._accounts = accounts
        self._currencies = currencies
        self._exchange_rates = exchange_rates
        self._capital_movements = capital_movements
        self._base_currency_code = base_currency.strip().upper()
        self._clock = clock or (lambda: datetime.now(UTC))

    def execute(
        self,
        period: AnalyticsPeriod,
        filters: AnalyticsFilters | None = None,
    ) -> ConsolidatedReport:
        filters = filters or AnalyticsFilters()
        base_currency = self._currencies.get_by_code(
            self._base_currency_code
        )
        if base_currency is None:
            raise CurrencyNotFoundError(
                f"Base currency {self._base_currency_code} is not registered."
            )

        as_of = period.end_or(self._clock())
        converter = BaseCurrencyConverter(
            self._exchange_rates, base_currency, as_of
        )

        native_summary = self._summary.execute(period, filters)
        native_inventory = self._inventory.execute(as_of, filters)
        native_accounts = self._accounts.execute(as_of, filters)

        revenue = converter.total(native_summary.revenue)
        cogs = converter.total(native_summary.cogs)
        expenses = converter.total(native_summary.expenses)
        gross_profit = revenue - cogs
        net_profit = gross_profit - expenses
        inventory_value = converter.total(
            native_inventory.inventory_value
        )
        available_capital = converter.total(native_accounts.totals)

        opening_cutoff, closing_cutoff = self._capital_cutoffs(
            period, as_of, native_accounts
        )
        opening_capital = self._net_capital_at(
            native_accounts, opening_cutoff, converter
        )
        closing_capital = self._net_capital_at(
            native_accounts, closing_cutoff, converter
        )

        roi: Decimal | None = None
        average_capital: Money | None = None
        if opening_capital is not None and closing_capital is not None:
            average_capital = (opening_capital + closing_capital) / 2
            if average_capital.amount > 0 and converter.is_complete:
                roi = (
                    net_profit.amount
                    / average_capital.amount
                    * Decimal("100")
                ).quantize(_ROI_QUANTUM, rounding=ROUND_HALF_UP)

        return ConsolidatedReport(
            period=period,
            base_currency=base_currency,
            as_of=as_of,
            revenue=revenue,
            cogs=cogs,
            gross_profit=gross_profit,
            expenses=expenses,
            net_profit=net_profit,
            inventory_value=inventory_value,
            available_capital=available_capital,
            invested_capital=inventory_value,
            gross_margin=percentage(gross_profit, revenue),
            net_margin=percentage(net_profit, revenue),
            roi=roi,
            roi_opening_capital=opening_capital,
            roi_closing_capital=closing_capital,
            roi_average_capital=average_capital,
            missing_rates=converter.missing_rates,
            is_complete=converter.is_complete,
            native_summary=native_summary,
            native_inventory=native_inventory,
            native_accounts=native_accounts,
        )

    def _capital_cutoffs(
        self,
        period: AnalyticsPeriod,
        as_of: datetime,
        native_accounts,
    ) -> tuple[datetime, datetime]:
        if period.start is not None:
            return period.start, as_of

        earliest: datetime | None = None
        for account in native_accounts.accounts:
            for movement in self._capital_movements.list_for_account(
                account.account_id
            ):
                if earliest is None or movement.movement_date < earliest:
                    earliest = movement.movement_date
        if earliest is None or earliest > as_of:
            earliest = as_of
        return earliest, as_of

    def _net_capital_at(
        self,
        native_accounts,
        cutoff: datetime,
        converter: BaseCurrencyConverter,
    ) -> Money | None:
        totals: dict[str, Money] = {}
        for account in native_accounts.accounts:
            for movement in self._capital_movements.list_for_account(
                account.account_id
            ):
                if movement.movement_date <= cutoff:
                    add_money(totals, movement.signed_amount)

        if not totals:
            return Money.zero(converter.base_currency)

        total = Money.zero(converter.base_currency)
        for amount in totals.values():
            converted = converter.convert(amount)
            if converted is None:
                return None
            total = total + converted
        return total
