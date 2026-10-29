"""Database schema bootstrap used by the application entry point."""

from __future__ import annotations

import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine

from app.infrastructure.config.settings import Settings
from app.infrastructure.database.session import create_database_engine


class DatabaseMigrationError(RuntimeError):
    """Raised when the local database cannot be upgraded to the latest schema."""


def migrations_directory() -> Path:
    """Return the Alembic scripts directory for source and frozen builds."""
    if getattr(sys, "frozen", False):
        bundle_root = Path(
            getattr(sys, "_MEIPASS", Path(sys.executable).parent)
        )
        return bundle_root / "migrations"
    return Path(__file__).resolve().parents[3] / "migrations"


def _alembic_config(
    database_url: str,
    *,
    script_location: Path | None = None,
) -> Config:
    directory = script_location or migrations_directory()
    if not (directory / "env.py").is_file():
        raise DatabaseMigrationError(
            f"Database migration scripts were not found at {directory}."
        )

    config = Config()
    # Alembic passes these values through ConfigParser, where a raw percent
    # sign starts an interpolation expression.
    config.set_main_option(
        "script_location",
        str(directory).replace("%", "%%"),
    )
    config.set_main_option(
        "sqlalchemy.url",
        database_url.replace("%", "%%"),
    )
    config.attributes["configure_logger"] = False
    return config


def upgrade_database(
    database_url: str,
    *,
    script_location: Path | None = None,
) -> str:
    """Apply all pending migrations and return the resulting revision."""
    try:
        config = _alembic_config(
            database_url,
            script_location=script_location,
        )

        # Ensure the SQLite parent directory exists before Alembic connects.
        engine = create_database_engine(
            Settings(database_url=database_url, _env_file=None)
        )
        engine.dispose()

        command.upgrade(config, "head")
        revision = current_revision(database_url)
    except DatabaseMigrationError:
        raise
    except Exception as exc:
        raise DatabaseMigrationError(
            f"The database schema could not be upgraded: {exc}"
        ) from exc

    if revision is None:
        raise DatabaseMigrationError(
            "The database schema was upgraded but no revision was recorded."
        )
    return revision


def current_revision(database_url: str) -> str | None:
    """Return the database's Alembic revision, or ``None`` when uninitialized."""
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            context = MigrationContext.configure(connection)
            return context.get_current_revision()
    finally:
        engine.dispose()


def head_revision(*, script_location: Path | None = None) -> str:
    """Return the latest revision available in the migration scripts."""
    config = _alembic_config(
        "sqlite:///:memory:",
        script_location=script_location,
    )
    head = ScriptDirectory.from_config(config).get_current_head()
    if head is None:
        raise DatabaseMigrationError("No database migration head was found.")
    return head
