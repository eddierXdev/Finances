"""Application use case for persisted UI preferences."""

from __future__ import annotations

from dataclasses import dataclass

from app.application.unit_of_work import UnitOfWorkFactory

UI_LANGUAGE_KEY = "ui.language"
UI_THEME_KEY = "ui.theme"


@dataclass(frozen=True, slots=True)
class UiPreferences:
    """Raw persisted UI preferences.

    The presentation layer validates and normalizes these values because the
    supported languages and themes are UI concerns.
    """

    language: str | None = None
    theme: str | None = None


class UiPreferencesService:
    """Read and write UI preferences through the settings repository."""

    def __init__(self, unit_of_work_factory: UnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    def load(self) -> UiPreferences:
        """Return the stored preferences without modifying them."""
        with self._unit_of_work_factory.unit_of_work() as uow:
            return UiPreferences(
                language=uow.settings.get(UI_LANGUAGE_KEY),
                theme=uow.settings.get(UI_THEME_KEY),
            )

    def set_language(self, language: str) -> None:
        """Persist the selected UI language."""
        with self._unit_of_work_factory.unit_of_work() as uow:
            uow.settings.set(UI_LANGUAGE_KEY, language)
            uow.commit()

    def set_theme(self, theme: str) -> None:
        """Persist the selected UI theme."""
        with self._unit_of_work_factory.unit_of_work() as uow:
            uow.settings.set(UI_THEME_KEY, theme)
            uow.commit()
