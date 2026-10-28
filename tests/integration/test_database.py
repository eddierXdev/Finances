"""Database bootstrap tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError

from app.infrastructure.config.settings import Settings
from app.infrastructure.database.session import create_session_factory, session_scope


def test_sqlite_database_file_is_created(engine, sqlite_settings: Settings) -> None:
    with engine.connect() as connection:
        assert connection.execute(text("SELECT 1")).scalar_one() == 1

    database_path = Path(make_url(sqlite_settings.database_url).database)
    assert database_path.is_file()


def test_foreign_keys_are_enabled_and_enforced(engine) -> None:
    with engine.connect() as connection:
        assert connection.execute(text("PRAGMA foreign_keys")).scalar_one() == 1

    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE parent (id INTEGER PRIMARY KEY)"))
        connection.execute(
            text(
                "CREATE TABLE child ("
                "id INTEGER PRIMARY KEY, "
                "parent_id INTEGER NOT NULL REFERENCES parent(id)"
                ")"
            )
        )

    with engine.connect() as connection:
        with pytest.raises(IntegrityError):
            connection.execute(text("INSERT INTO child (id, parent_id) VALUES (1, 99)"))


def test_session_scope_commits_on_success(engine) -> None:
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT NOT NULL)"))

    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        session.execute(text("INSERT INTO items (id, name) VALUES (1, 'sample')"))

    with engine.connect() as connection:
        assert connection.execute(text("SELECT name FROM items")).scalar_one() == "sample"


def test_session_scope_rolls_back_on_failure(engine) -> None:
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT NOT NULL)"))

    session_factory = create_session_factory(engine)

    with pytest.raises(RuntimeError):
        with session_scope(session_factory) as session:
            session.execute(text("INSERT INTO items (id, name) VALUES (1, 'sample')"))
            raise RuntimeError("simulated failure")

    with engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM items")).scalar_one() == 0
