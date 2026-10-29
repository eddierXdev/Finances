"""Desktop application bootstrap."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from datetime import timedelta

from PySide6.QtWidgets import QApplication
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.application.analytics.service import AnalyticsService
from app.application.backup.service import BackupService
from app.application.exchange_rates.service import ExchangeRateService
from app.application.exports.service import ExportService
from app.application.finances.account_service import AccountService
from app.application.finances.operations_service import (
    FinanceOperationsService,
)
from app.application.inventory.service import InventoryService
from app.application.preferences.service import UiPreferencesService
from app.application.products.catalog import ProductCatalogService
from app.application.purchases.service import PurchaseService
from app.application.receiving.service import ReceivingService
from app.application.returns.service import ReturnsService
from app.application.sales.service import SalesService
from app.infrastructure.backup.sqlite_backup import SqliteBackupGateway
from app.infrastructure.config.settings import Settings
from app.infrastructure.database.unit_of_work import (
    SqlAlchemyUnitOfWorkFactory,
)
from app.infrastructure.exports.zip_csv_export import ZipCsvExportGateway
from app.presentation.desktop.i18n.translator import Translator
from app.presentation.desktop.main_window import MainWindow
from app.presentation.desktop.navigation import NAVIGATION_ITEMS
from app.presentation.desktop.pages import build_pages
from app.presentation.desktop.themes.theme_manager import ThemeManager
from app.presentation.desktop.views.accounts import AccountsPage
from app.presentation.desktop.views.analytics import AnalyticsPage
from app.presentation.desktop.views.currency_rates import CurrencyRatesPage
from app.presentation.desktop.views.dashboard import DashboardPage
from app.presentation.desktop.views.finances import FinancesPage
from app.presentation.desktop.views.inventory import InventoryPage
from app.presentation.desktop.views.products import ProductsPage
from app.presentation.desktop.views.purchases import PurchasesPage
from app.presentation.desktop.views.receiving import ReceivingPage
from app.presentation.desktop.views.returns import ReturnsPage
from app.presentation.desktop.views.sales import SalesPage
from app.presentation.desktop.views.settings import SettingsPage


def create_application(argv: Sequence[str] | None = None) -> QApplication:
    """Return the process-wide Qt application instance."""
    existing = QApplication.instance()
    if isinstance(existing, QApplication):
        return existing

    app = QApplication(list(argv) if argv is not None else sys.argv)
    app.setApplicationName("Resale Manager")
    app.setApplicationDisplayName("Resale Manager")
    app.setOrganizationName("Resale Manager")
    return app


def build_main_window(
    settings: Settings,
    catalog: ProductCatalogService | None = None,
    accounts: AccountService | None = None,
    purchases: PurchaseService | None = None,
    receiving: ReceivingService | None = None,
    inventory: InventoryService | None = None,
    sales: SalesService | None = None,
    returns: ReturnsService | None = None,
    finance: FinanceOperationsService | None = None,
    exchange_rates: ExchangeRateService | None = None,
    analytics: AnalyticsService | None = None,
    backup: BackupService | None = None,
    exports: ExportService | None = None,
    translator: Translator | None = None,
    theme_manager: ThemeManager | None = None,
    preferences: UiPreferencesService | None = None,
) -> MainWindow:
    """Compose the shell with every supplied application screen."""
    translator = translator or Translator()
    overrides = {}
    if catalog is not None:
        overrides["products"] = ProductsPage(
            catalog,
            base_currency=settings.base_currency,
        )
    if accounts is not None:
        overrides["accounts"] = AccountsPage(
            accounts,
            base_currency=settings.base_currency,
        )
    if purchases is not None:
        overrides["purchases"] = PurchasesPage(
            purchases,
            base_currency=settings.base_currency,
        )
    if receiving is not None:
        overrides["receiving"] = ReceivingPage(
            receiving,
            base_currency=settings.base_currency,
        )
    if inventory is not None:
        overrides["inventory"] = InventoryPage(
            inventory,
            base_currency=settings.base_currency,
        )
    if sales is not None:
        overrides["sales"] = SalesPage(
            sales,
            base_currency=settings.base_currency,
        )
    if returns is not None:
        overrides["returns"] = ReturnsPage(
            returns,
            base_currency=settings.base_currency,
        )
    if finance is not None:
        overrides["expenses"] = FinancesPage(
            finance,
            base_currency=settings.base_currency,
        )
    if exchange_rates is not None:
        overrides["currency"] = CurrencyRatesPage(
            exchange_rates,
            base_currency=settings.base_currency,
        )
    if analytics is not None:
        overrides["dashboard"] = DashboardPage(
            analytics,
            base_currency=settings.base_currency,
            translator=translator,
            theme_manager=theme_manager,
        )
        overrides["analytics"] = AnalyticsPage(
            analytics,
            base_currency=settings.base_currency,
        )
    overrides["settings"] = SettingsPage(
        settings,
        backup=backup,
        exports=exports,
        translator=translator,
        theme_manager=theme_manager,
        preferences=preferences,
    )

    return MainWindow(
        NAVIGATION_ITEMS,
        build_pages(
            NAVIGATION_ITEMS,
            overrides=overrides,
            translator=translator,
        ),
        base_currency=settings.base_currency,
        translator=translator,
    )


def run_desktop(
    settings: Settings,
    session_factory: sessionmaker[Session],
    engine: Engine | None = None,
) -> int:
    """Start the Qt event loop and return its exit code."""
    database_engine = engine or session_factory.kw.get("bind")
    if database_engine is None:
        raise ValueError(
            "The database engine is required for backup and restore support."
        )

    unit_of_work = SqlAlchemyUnitOfWorkFactory(session_factory)
    catalog = ProductCatalogService(unit_of_work)
    accounts = AccountService(unit_of_work)
    purchases = PurchaseService(unit_of_work)
    receiving = ReceivingService(unit_of_work)
    inventory = InventoryService(unit_of_work)
    sales = SalesService(unit_of_work)
    returns = ReturnsService(unit_of_work)
    finance = FinanceOperationsService(unit_of_work)
    exchange_rates = ExchangeRateService(
        unit_of_work,
        freshness=timedelta(hours=settings.fx_freshness_hours),
    )
    analytics = AnalyticsService(
        unit_of_work,
        base_currency=settings.base_currency,
        slow_moving_days=settings.analytics_slow_moving_days,
    )
    backup = BackupService(
        unit_of_work,
        SqliteBackupGateway(
            settings.database_url,
            engine=database_engine,
        ),
        default_directory=settings.backup_directory,
    )
    exports = ExportService(
        accounts,
        inventory,
        purchases,
        sales,
        returns,
        ZipCsvExportGateway(),
    )
    preferences = UiPreferencesService(unit_of_work)
    stored = preferences.load()
    translator = Translator(stored.language)
    theme_manager = ThemeManager(stored.theme)

    app = create_application()
    theme_manager.apply(app)
    window = build_main_window(
        settings,
        catalog,
        accounts,
        purchases,
        receiving,
        inventory,
        sales,
        returns,
        finance,
        exchange_rates,
        analytics,
        backup=backup,
        exports=exports,
        translator=translator,
        theme_manager=theme_manager,
        preferences=preferences,
    )
    window.show()
    return app.exec()
