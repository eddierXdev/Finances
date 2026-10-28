"""Main desktop window: sidebar navigation plus a stacked content area."""

from __future__ import annotations

from collections.abc import Mapping

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.presentation.desktop.navigation import NavigationItem
from app.presentation.desktop.styles import APP_STYLESHEET


class MainWindow(QMainWindow):
    """Application shell.

    The window only arranges screens and navigation. It must never calculate
    balances, FIFO, COGS or profit; screens call application use cases instead.
    """

    def __init__(
        self,
        items: tuple[NavigationItem, ...],
        pages: Mapping[str, QWidget],
        *,
        app_name: str = "Resale Manager",
        base_currency: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        if not items:
            raise ValueError("At least one navigation item is required.")

        missing = [item.key for item in items if item.key not in pages]
        if missing:
            raise ValueError(
                "No screen registered for navigation keys: "
                + ", ".join(missing)
            )

        self._items = items
        self._pages = dict(pages)
        self._keys = [item.key for item in items]
        self._selecting = False

        self.setWindowTitle(app_name)
        self.setMinimumSize(960, 600)
        self.resize(1180, 720)
        self.setStyleSheet(APP_STYLESHEET)

        self._build_menu(app_name)
        self._build_status_bar(base_currency)
        self._build_ui(app_name)
        self.select_page(self._keys[0])

    def _build_ui(self, app_name: str) -> None:
        central = QWidget(self)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        sidebar = QFrame(central)
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(240)

        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        brand = QLabel(app_name, sidebar)
        brand.setObjectName("brand")
        sidebar_layout.addWidget(brand)

        brand_subtitle = QLabel("Resale operations", sidebar)
        brand_subtitle.setObjectName("brandSubtitle")
        sidebar_layout.addWidget(brand_subtitle)

        self._navigation = QListWidget(sidebar)
        self._navigation.setObjectName("navigation")
        self._navigation.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._navigation.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        for item in self._items:
            row = QListWidgetItem(item.title)
            row.setData(Qt.ItemDataRole.UserRole, item.key)
            self._navigation.addItem(row)
        self._navigation.currentRowChanged.connect(self._on_row_changed)
        sidebar_layout.addWidget(self._navigation, 1)

        content = QWidget(central)
        content.setObjectName("content")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self._stack = QStackedWidget(content)
        self._stack.setObjectName("pageStack")
        for item in self._items:
            self._stack.addWidget(self._pages[item.key])
        content_layout.addWidget(self._stack)

        layout.addWidget(sidebar)
        layout.addWidget(content, 1)
        self.setCentralWidget(central)

    def _build_menu(self, app_name: str) -> None:
        file_menu = self.menuBar().addMenu("&File")

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        help_menu = self.menuBar().addMenu("&Help")

        about_action = QAction(f"&About {app_name}", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _build_status_bar(self, base_currency: str | None) -> None:
        status = self.statusBar()
        status.showMessage("Ready")

        offline = QLabel("Offline-first", self)
        status.addPermanentWidget(offline)

        if base_currency:
            currency = QLabel(f"Base currency: {base_currency}", self)
            currency.setObjectName("baseCurrencyLabel")
            status.addPermanentWidget(currency)

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            f"About {self.windowTitle()}",
            "Offline-first resale management.\n\n"
            "Business calculations live in the application and domain layers; "
            "the UI only presents their results.",
        )

    def _on_row_changed(self, row: int) -> None:
        if self._selecting or row < 0:
            return
        key = self._navigation.item(row).data(Qt.ItemDataRole.UserRole)
        self._show_page(key)

    def _show_page(self, key: str) -> None:
        self._stack.setCurrentWidget(self._pages[key])

    def current_key(self) -> str:
        """Return the navigation key of the visible screen."""
        return self._keys[self._stack.currentIndex()]

    def select_page(self, key: str) -> None:
        """Show the screen registered under ``key``."""
        if key not in self._pages:
            raise KeyError(f"Unknown navigation key: {key}")

        self._selecting = True
        try:
            self._navigation.setCurrentRow(self._keys.index(key))
        finally:
            self._selecting = False
        self._show_page(key)
