"""Translation, theme and Settings selector tests (headless)."""

from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QLabel, QListWidget, QScrollArea

from app.infrastructure.config.settings import Settings
from app.presentation.desktop.app import build_main_window
from app.presentation.desktop.i18n.translator import (
    SUPPORTED_LANGUAGES,
    Translator,
    is_supported_language,
    normalize_language,
)
from app.presentation.desktop.themes.theme_manager import (
    SUPPORTED_THEMES,
    ThemeManager,
    is_supported_theme,
    normalize_theme,
)
from app.presentation.desktop.views.settings import SettingsPage


class FakePreferences:
    def __init__(self) -> None:
        self.languages: list[str] = []
        self.themes: list[str] = []

    def set_language(self, language: str) -> None:
        self.languages.append(language)

    def set_theme(self, theme: str) -> None:
        self.themes.append(theme)


def test_supported_languages_are_en_and_es() -> None:
    assert SUPPORTED_LANGUAGES == ("en", "es")
    assert is_supported_language("en")
    assert is_supported_language("ES")
    assert not is_supported_language("fr")
    assert normalize_language("fr") == "en"
    assert normalize_language("es") == "es"


def test_unsupported_language_does_not_replace_the_current_one() -> None:
    translator = Translator("en")

    assert translator.set_language("fr") is False
    assert translator.language == "en"
    assert translator.set_language("es") is True
    assert translator.language == "es"


def test_missing_translation_key_falls_back_to_the_key() -> None:
    translator = Translator("es")

    assert translator.tr("missing.translation.key") == "missing.translation.key"


def test_supported_themes_are_system_light_and_dark() -> None:
    assert SUPPORTED_THEMES == ("system", "light", "dark")
    assert is_supported_theme("dark")
    assert is_supported_theme("SYSTEM")
    assert not is_supported_theme("sepia")
    assert normalize_theme("sepia") == "system"
    assert normalize_theme("light") == "light"


def test_unsupported_theme_does_not_replace_the_current_one() -> None:
    manager = ThemeManager("light")

    assert manager.set_theme("sepia") is False
    assert manager.theme == "light"
    assert manager.set_theme("dark") is True
    assert manager.theme == "dark"


def test_theme_manager_applies_stylesheets_at_runtime(qapp) -> None:
    manager = ThemeManager("dark")
    try:
        manager.apply(qapp)
        assert "#0f172a" in qapp.styleSheet()

        assert manager.set_theme("light") is True
        assert "#f5f6f8" in qapp.styleSheet()
    finally:
        qapp.setStyleSheet("")


def test_settings_selectors_apply_and_persist_preferences(qapp) -> None:
    preferences = FakePreferences()
    translator = Translator("en")
    theme_manager = ThemeManager("light")
    page = SettingsPage(
        Settings(),
        translator=translator,
        theme_manager=theme_manager,
        preferences=preferences,
    )
    try:
        language = page.findChild(QComboBox, "uiLanguageCombo")
        theme = page.findChild(QComboBox, "uiThemeCombo")
        assert language is not None and theme is not None
        assert language.count() == len(SUPPORTED_LANGUAGES)
        assert theme.count() == len(SUPPORTED_THEMES)
        assert language.accessibleName() == "Interface language"
        assert theme.accessibleDescription()

        language.setCurrentIndex(language.findData("es"))
        assert translator.language == "es"
        assert preferences.languages == ["es"]
        assert page.findChild(QLabel, "pageTitle").text() == "Configuración"
        assert language.accessibleName() == "Idioma de la interfaz"
        enabled = page.findChild(QLabel, "settingsValue_fx_auto_update")
        assert enabled is not None and enabled.text() == "Desactivado"

        theme.setCurrentIndex(theme.findData("dark"))
        assert theme_manager.theme == "dark"
        assert preferences.themes == ["dark"]
        assert theme.itemText(theme.findData("dark")) == "Oscuro"
    finally:
        page.close()
        qapp.setStyleSheet("")


def test_settings_page_uses_a_scroll_area(qapp) -> None:
    page = SettingsPage(Settings())
    try:
        scroll = page.findChild(QScrollArea, "settingsScrollArea")
        assert scroll is not None
        assert scroll.widgetResizable() is True
    finally:
        page.close()


def test_main_window_retranslates_shell_strings(qapp) -> None:
    translator = Translator("en")
    window = build_main_window(
        Settings(base_currency="USD"),
        translator=translator,
    )
    try:
        translator.set_language("es")

        navigation = window.findChild(QListWidget, "navigation")
        assert navigation is not None
        assert navigation.item(0).text() == "Panel"
        currency = window.findChild(QLabel, "baseCurrencyLabel")
        assert currency is not None
        assert currency.text() == "Moneda base: USD"
    finally:
        window.close()
