"""Main desktop window: sidebar navigation plus a stacked content area."""

from __future__ import annotations

from collections.abc import Mapping

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.presentation.desktop.i18n.translator import Translator
from app.presentation.desktop.navigation import NavigationItem
from app.presentation.desktop.navigation.sidebar import Sidebar


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
        translator: Translator | None = None,
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
        self._app_name = app_name
        self._base_currency = base_currency
        self._translator = translator or Translator()

        self.setWindowTitle(app_name)
        self.setMinimumSize(960, 600)
        self.resize(1180, 720)

        self._build_menu()
        self._build_status_bar()
        self._build_ui()
        self._translator.language_changed.connect(self.retranslate)
        self.retranslate()
        self.select_page(self._keys[0])

    def _build_ui(self) -> None:
        central = QWidget(self)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._sidebar = Sidebar(
            self._items,
            app_name=self._app_name,
            base_currency=self._base_currency,
            translator=self._translator,
            parent=central,
        )
        self._navigation = self._sidebar.navigation
        self._navigation.currentRowChanged.connect(self._on_row_changed)

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

        layout.addWidget(self._sidebar)
        layout.addWidget(content, 1)
        self.setCentralWidget(central)

    def _build_menu(self) -> None:
        self._file_menu = self.menuBar().addMenu("")
        self._exit_action = QAction(self)
        self._exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        self._exit_action.triggered.connect(self.close)
        self._file_menu.addAction(self._exit_action)

        self._help_menu = self.menuBar().addMenu("")
        self._about_action = QAction(self)
        self._about_action.triggered.connect(self._show_about)
        self._help_menu.addAction(self._about_action)

    def _build_status_bar(self) -> None:
        self._status_bar = self.statusBar()
        self._offline_label = QLabel(self)
        self._offline_label.setObjectName("statusBadge")
        self._offline_label.setProperty("tone", "success")
        self._status_bar.addPermanentWidget(self._offline_label)

        self._currency_label: QLabel | None = None
        if self._base_currency:
            self._currency_label = QLabel(self)
            self._currency_label.setObjectName("baseCurrencyLabel")
            self._status_bar.addPermanentWidget(self._currency_label)

    def retranslate(self) -> None:
        """Refresh shell strings after a language change."""
        t = self._translator.tr
        self._file_menu.setTitle(t("app.menu.file"))
        self._exit_action.setText(t("app.menu.exit"))
        self._help_menu.setTitle(t("app.menu.help"))
        self._about_action.setText(
            t("app.menu.about", app_name=self._app_name)
        )
        self._sidebar.retranslate()
        self._status_bar.showMessage(t("app.status.ready"))
        self._offline_label.setText(t("app.status.offline"))
        if self._currency_label is not None:
            self._currency_label.setText(
                t(
                    "app.status.base_currency",
                    currency=self._base_currency,
                )
            )

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            self._translator.tr(
                "app.about.title",
                app_name=self._app_name,
            ),
            self._translator.tr(
                "app.about.text",
            ),
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
