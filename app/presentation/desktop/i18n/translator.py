"""Small presentation-layer translator with JSON catalogs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Signal

DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES: tuple[str, ...] = ("en", "es")


def normalize_language(language: str | None) -> str:
    """Return a supported language code, falling back to English."""
    if isinstance(language, str):
        candidate = language.strip().lower()
        if candidate in SUPPORTED_LANGUAGES:
            return candidate
    return DEFAULT_LANGUAGE


def is_supported_language(language: str | None) -> bool:
    """Return whether ``language`` is one of the supported UI languages."""
    return (
        isinstance(language, str)
        and language.strip().lower() in SUPPORTED_LANGUAGES
    )


class Translator(QObject):
    """Translate presentation strings and notify widgets on language changes."""

    language_changed = Signal(str)

    def __init__(
        self,
        language: str | None = DEFAULT_LANGUAGE,
        *,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._catalogs = _load_catalogs()
        self._language = normalize_language(language)

    @property
    def language(self) -> str:
        """Return the active language code."""
        return self._language

    @property
    def available_languages(self) -> tuple[str, ...]:
        """Return the supported language codes in display order."""
        return SUPPORTED_LANGUAGES

    def set_language(self, language: str) -> bool:
        """Select a language; unsupported values leave the current one intact."""
        if not is_supported_language(language):
            return False

        normalized = normalize_language(language)
        if normalized == self._language:
            return True

        self._language = normalized
        self.language_changed.emit(normalized)
        return True

    def tr(
        self,
        key: str,
        default: str | None = None,
        **kwargs: Any,
    ) -> str:
        """Return a translated string.

        Lookup order is active language, English, ``default``, then the key.
        Missing format arguments fall back to the unformatted template so a
        broken placeholder never prevents the UI from rendering.
        """
        template = self._lookup(key)
        if template is None:
            template = default if default is not None else key

        if not kwargs:
            return template
        try:
            return template.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            return template

    def _lookup(self, key: str) -> str | None:
        for language in (self._language, DEFAULT_LANGUAGE):
            catalog = self._catalogs.get(language, {})
            value = catalog.get(key)
            if isinstance(value, str):
                return value
        return None


def _load_catalogs() -> dict[str, dict[str, str]]:
    catalogs: dict[str, dict[str, str]] = {}
    directory = Path(__file__).resolve().parent
    for language in SUPPORTED_LANGUAGES:
        path = directory / f"{language}.json"
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise RuntimeError(
                f"Translation catalog could not be read: {path}"
            ) from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"Translation catalog is not valid JSON: {path}"
            ) from exc
        if not isinstance(raw, dict) or any(
            not isinstance(key, str) or not isinstance(value, str)
            for key, value in raw.items()
        ):
            raise RuntimeError(
                f"Translation catalog must contain string values: {path}"
            )
        catalogs[language] = raw
    return catalogs
