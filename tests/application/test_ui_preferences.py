"""UI preference persistence tests."""

from __future__ import annotations

from sqlalchemy import Engine

from app.application.preferences.service import (
    UI_LANGUAGE_KEY,
    UI_THEME_KEY,
    UiPreferencesService,
)
from app.infrastructure.database.session import create_session_factory
from app.infrastructure.database.unit_of_work import (
    SqlAlchemyUnitOfWorkFactory,
)


def _service(engine: Engine) -> UiPreferencesService:
    return UiPreferencesService(
        SqlAlchemyUnitOfWorkFactory(create_session_factory(engine))
    )


def test_language_setting_is_persisted(migrated_engine: Engine) -> None:
    _service(migrated_engine).set_language("es")

    assert _service(migrated_engine).load().language == "es"

    with SqlAlchemyUnitOfWorkFactory(
        create_session_factory(migrated_engine)
    ).unit_of_work() as uow:
        assert uow.settings.get(UI_LANGUAGE_KEY) == "es"


def test_theme_setting_is_persisted(migrated_engine: Engine) -> None:
    _service(migrated_engine).set_theme("dark")

    assert _service(migrated_engine).load().theme == "dark"

    with SqlAlchemyUnitOfWorkFactory(
        create_session_factory(migrated_engine)
    ).unit_of_work() as uow:
        assert uow.settings.get(UI_THEME_KEY) == "dark"
