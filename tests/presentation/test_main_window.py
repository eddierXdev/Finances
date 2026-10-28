"""Desktop shell tests (headless)."""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QListWidget, QStackedWidget

from app.infrastructure.config.settings import Settings
from app.presentation.desktop.app import build_main_window
from app.presentation.desktop.navigation import NAVIGATION_ITEMS
from app.presentation.desktop.pages import PlaceholderPage


def _window(base_currency: str = "USD"):
    return build_main_window(Settings(base_currency=base_currency))


def test_navigation_keys_are_unique() -> None:
    keys = [item.key for item in NAVIGATION_ITEMS]
    assert len(keys) == len(set(keys))


def test_shell_lists_every_navigation_item(qapp) -> None:
    window = _window()
    try:
        navigation = window.findChild(QListWidget, "navigation")
        assert navigation is not None
        assert navigation.count() == len(NAVIGATION_ITEMS)
        assert [navigation.item(row).text() for row in range(navigation.count())] == [
            item.title for item in NAVIGATION_ITEMS
        ]
        assert window.current_key() == NAVIGATION_ITEMS[0].key
    finally:
        window.close()


def test_shell_builds_one_screen_per_item(qapp) -> None:
    window = _window()
    try:
        stack = window.findChild(QStackedWidget, "pageStack")
        assert stack is not None
        assert stack.count() == len(NAVIGATION_ITEMS)

        for item in NAVIGATION_ITEMS:
            page = stack.widget(NAVIGATION_ITEMS.index(item))
            assert isinstance(page, PlaceholderPage)
            assert page.objectName() == f"page-{item.key}"

            title = page.findChild(QLabel, "pageTitle")
            assert title is not None
            assert title.text() == item.title
    finally:
        window.close()


def test_selecting_a_row_switches_the_visible_screen(qapp) -> None:
    window = _window()
    try:
        navigation = window.findChild(QListWidget, "navigation")
        stack = window.findChild(QStackedWidget, "pageStack")
        assert navigation is not None
        assert stack is not None

        target_index = NAVIGATION_ITEMS.index(
            next(item for item in NAVIGATION_ITEMS if item.key == "sales")
        )
        navigation.setCurrentRow(target_index)

        assert window.current_key() == "sales"
        assert stack.currentIndex() == target_index
    finally:
        window.close()


def test_select_page_updates_the_sidebar(qapp) -> None:
    window = _window()
    try:
        window.select_page("analytics")

        navigation = window.findChild(QListWidget, "navigation")
        assert navigation is not None
        assert window.current_key() == "analytics"
        assert navigation.currentItem().data(Qt.ItemDataRole.UserRole) == "analytics"
    finally:
        window.close()


def test_unknown_navigation_key_is_rejected(qapp) -> None:
    window = _window()
    try:
        with pytest.raises(KeyError):
            window.select_page("does-not-exist")
    finally:
        window.close()


def test_status_bar_shows_the_reporting_currency(qapp) -> None:
    window = _window(base_currency="EUR")
    try:
        label = window.findChild(QLabel, "baseCurrencyLabel")
        assert label is not None
        assert label.text() == "Base currency: EUR"
    finally:
        window.close()
