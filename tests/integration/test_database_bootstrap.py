"""Database bootstrap and schema hardening tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from app.infrastructure.database.migrations import (
    DatabaseMigrationError,
    current_revision,
    head_revision,
    migrations_directory,
    upgrade_database,
)


def _database_url(tmp_path: Path) -> str:
    return f"sqlite:///{(tmp_path / 'bootstrap.db').as_posix()}"


def test_fresh_database_is_created_at_the_current_head(tmp_path: Path) -> None:
    database_url = _database_url(tmp_path)
    head = head_revision()

    revision = upgrade_database(database_url)

    assert revision == head
    assert current_revision(database_url) == head
    assert (tmp_path / "bootstrap.db").is_file()
    assert (
        migrations_directory()
        .joinpath("versions", "0012_query_indexes.py")
        .is_file()
    )


def test_upgrade_database_is_idempotent(tmp_path: Path) -> None:
    database_url = _database_url(tmp_path)

    first = upgrade_database(database_url)
    second = upgrade_database(database_url)

    assert first == second


def test_corrupt_database_is_reported_as_a_migration_error(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "corrupt.db"
    database_path.write_text("this is not a sqlite database", encoding="utf-8")

    with pytest.raises(DatabaseMigrationError, match="could not be upgraded"):
        upgrade_database(f"sqlite:///{database_path.as_posix()}")


def test_missing_migration_scripts_are_reported(tmp_path: Path) -> None:
    with pytest.raises(DatabaseMigrationError, match="not found"):
        upgrade_database(
            _database_url(tmp_path),
            script_location=tmp_path / "missing-migrations",
        )


def test_database_path_with_percent_sign_is_supported(tmp_path: Path) -> None:
    folder = tmp_path / "percent%path"
    folder.mkdir()
    database_url = f"sqlite:///{(folder / 'bootstrap.db').as_posix()}"

    revision = upgrade_database(database_url)

    assert revision == head_revision()
    assert current_revision(database_url) == revision
    assert (folder / "bootstrap.db").is_file()


def test_existing_database_is_upgraded_from_the_previous_revision(
    tmp_path: Path,
) -> None:
    database_url = _database_url(tmp_path)
    config = Config()
    config.set_main_option(
        "script_location",
        str(migrations_directory()),
    )
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "0011_settings")

    assert current_revision(database_url) == "0011_settings"

    revision = upgrade_database(database_url)

    assert revision == head_revision()
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            indexes = set(
                connection.execute(
                    text(
                        "SELECT name FROM sqlite_master "
                        "WHERE type = 'index'"
                    )
                ).scalars()
            )
    finally:
        engine.dispose()

    assert "ix_inventory_lots_purchase_item_id_received_at" in indexes
    assert "ix_inventory_movements_variant_id_movement_date" in indexes
    assert (
        "ix_inventory_movements_inventory_lot_id_movement_date" in indexes
    )
