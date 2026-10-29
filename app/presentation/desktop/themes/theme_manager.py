"""Application theme selection and stylesheet application."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

from app.presentation.desktop.themes.chart_palette import (
    ChartPalette,
    chart_palette as palette_for,
)

DEFAULT_THEME = "system"
SUPPORTED_THEMES: tuple[str, ...] = ("system", "light", "dark")


def normalize_theme(theme: str | None) -> str:
    """Return a supported theme name, falling back to System."""
    if isinstance(theme, str):
        candidate = theme.strip().lower()
        if candidate in SUPPORTED_THEMES:
            return candidate
    return DEFAULT_THEME


def is_supported_theme(theme: str | None) -> bool:
    """Return whether ``theme`` is one of the supported theme names."""
    return (
        isinstance(theme, str)
        and theme.strip().lower() in SUPPORTED_THEMES
    )


class ThemeManager(QObject):
    """Apply Light, Dark or System appearance to the whole Qt application."""

    theme_changed = Signal(str)

    def __init__(
        self,
        theme: str | None = DEFAULT_THEME,
        *,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._theme = normalize_theme(theme)
        self._stylesheets = _load_stylesheets()
        self._application: QApplication | None = None
        self._system_signal_connected = False

    @property
    def theme(self) -> str:
        """Return the selected theme name."""
        return self._theme

    @property
    def available_themes(self) -> tuple[str, ...]:
        """Return supported theme names in display order."""
        return SUPPORTED_THEMES

    @property
    def effective_theme(self) -> str:
        """Return the concrete theme currently used for rendering."""
        if self._theme != "system":
            return self._theme
        hints = QGuiApplication.styleHints()
        if hints.colorScheme() == Qt.ColorScheme.Dark:
            return "dark"
        return "light"

    @property
    def chart_palette(self) -> ChartPalette:
        """Return the semantic colors used by native painted charts."""
        return palette_for(self.effective_theme)

    def apply(self, application: QApplication | None = None) -> None:
        """Apply the selected theme to the Qt application."""
        if application is None:
            instance = QApplication.instance()
            if not isinstance(instance, QApplication):
                return
            application = instance

        self._application = application
        self._connect_system_changes()
        application.setStyleSheet(self._stylesheets[self.effective_theme])

    def set_theme(self, theme: str) -> bool:
        """Select a theme; unsupported values leave the current one intact."""
        if not is_supported_theme(theme):
            return False

        normalized = normalize_theme(theme)
        if normalized == self._theme:
            return True

        self._theme = normalized
        if self._application is not None:
            self._application.setStyleSheet(
                self._stylesheets[self.effective_theme]
            )
        self.theme_changed.emit(normalized)
        return True

    def _connect_system_changes(self) -> None:
        if self._system_signal_connected:
            return
        QGuiApplication.styleHints().colorSchemeChanged.connect(
            self._on_system_color_scheme_changed
        )
        self._system_signal_connected = True

    def _on_system_color_scheme_changed(self, *_args) -> None:
        if self._application is None or self._theme != "system":
            return
        self._application.setStyleSheet(
            self._stylesheets[self.effective_theme]
        )
        self.theme_changed.emit(self._theme)


def _load_stylesheets() -> dict[str, str]:
    return {
        "light": _read_stylesheet("light"),
        "dark": _read_stylesheet("dark"),
    }


def _read_stylesheet(name: str) -> str:
    directory = Path(__file__).resolve().parent
    candidates = [directory / f"{name}.qss"]

    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        candidates.append(
            Path(bundle_root)
            / "app"
            / "presentation"
            / "desktop"
            / "themes"
            / f"{name}.qss"
        )

    for path in candidates:
        if path.is_file():
            try:
                return path.read_text(encoding="utf-8")
            except OSError as exc:
                raise RuntimeError(
                    f"Theme stylesheet could not be read: {path}"
                ) from exc
    raise RuntimeError(
        f"Theme stylesheet not found: {name}.qss "
        f"(looked in {', '.join(str(path) for path in candidates)})"
    )
