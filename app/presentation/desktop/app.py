"""Desktop application bootstrap."""

from __future__ import annotations

import sys
from collections.abc import Sequence

from PySide6.QtWidgets import QApplication
from sqlalchemy.orm import Session, sessionmaker

from app.application.finances.account_service import AccountService
from app.application.products.catalog import ProductCatalogService
from app.application.purchases.service import PurchaseService
from app.infrastructure.config.settings import Settings
from app.infrastructure.database.unit_of_work import (
    SqlAlchemyUnitOfWorkFactory,
)
from app.presentation.desktop.main_window import MainWindow
from app.presentation.desktop.navigation import NAVIGATION_ITEMS
from app.presentation.desktop.pages import build_pages
from app.presentation.desktop.views.accounts import AccountsPage
from app.presentation.desktop.views.products import ProductsPage
from app.presentation.desktop.views.purchases import PurchasesPage


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
) -> MainWindow:
    """Compose the shell with the screens currently available."""
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

    return MainWindow(
        NAVIGATION_ITEMS,
        build_pages(NAVIGATION_ITEMS, overrides=overrides),
        base_currency=settings.base_currency,
    )


def run_desktop(
    settings: Settings,
    session_factory: sessionmaker[Session],
) -> int:
    """Start the Qt event loop and return its exit code."""
    unit_of_work = SqlAlchemyUnitOfWorkFactory(session_factory)
    catalog = ProductCatalogService(unit_of_work)
    accounts = AccountService(unit_of_work)
    purchases = PurchaseService(unit_of_work)
    app = create_application()
    window = build_main_window(
        settings, catalog, accounts, purchases
    )
    window.show()
    return app.exec()
