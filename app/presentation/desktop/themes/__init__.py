"""Desktop UI themes."""

from app.presentation.desktop.themes.theme_manager import (
    DEFAULT_THEME,
    SUPPORTED_THEMES,
    ThemeManager,
    is_supported_theme,
    normalize_theme,
)

__all__ = [
    "DEFAULT_THEME",
    "SUPPORTED_THEMES",
    "ThemeManager",
    "is_supported_theme",
    "normalize_theme",
]
