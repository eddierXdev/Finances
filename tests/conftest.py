"""Shared pytest fixtures."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.infrastructure.config.settings import Settings
from app.infrastructure.database.session import (
    create_database_engine,
    create_session_factory,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _build_alembic_config(database_url: str) -> Config:
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


@pytest.fixture
def sqlite_settings(tmp_path: Path) -> Settings:
    database_path = tmp_path / "resale_manager.db"
    return Settings(database_url=f"sqlite:///{database_path.as_posix()}")


@pytest.fixture
def engine(sqlite_settings: Settings) -> Iterator[Engine]:
    database_engine = create_database_engine(sqlite_settings)
    try:
        yield database_engine
    finally:
        database_engine.dispose()


@pytest.fixture
def migrated_engine(sqlite_settings: Settings) -> Iterator[Engine]:
    command.upgrade(_build_alembic_config(sqlite_settings.database_url), "head")
    database_engine = create_database_engine(sqlite_settings)
    try:
        yield database_engine
    finally:
        database_engine.dispose()


@pytest.fixture
def db_session(migrated_engine: Engine) -> Iterator[Session]:
    session = create_session_factory(migrated_engine)()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
