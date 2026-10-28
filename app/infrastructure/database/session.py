"""SQLite engine and session management."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.config.settings import Settings, get_settings


def _sqlite_file_path(database_url: str) -> Path | None:
    """Return the on-disk SQLite path, or ``None`` for other backends/memory."""
    url = make_url(database_url)
    if url.get_backend_name() != "sqlite":
        return None
    if not url.database or url.database == ":memory:" or url.database.startswith("file:"):
        return None
    return Path(url.database)


def _enable_sqlite_foreign_keys(dbapi_connection: Any, _connection_record: Any) -> None:
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
    finally:
        cursor.close()


def create_database_engine(settings: Settings | None = None) -> Engine:
    """Create an engine, ensuring the SQLite directory and FK enforcement exist."""
    settings = settings or get_settings()

    database_path = _sqlite_file_path(settings.database_url)
    if database_path is not None:
        database_path.parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(settings.database_url)

    if engine.dialect.name == "sqlite":
        event.listen(engine, "connect", _enable_sqlite_foreign_keys)

    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create a session factory bound to ``engine``."""
    return sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def session_scope(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    """Provide a transactional session that commits or rolls back as a unit."""
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
