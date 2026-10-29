"""Backup, restore and export application-service tests."""

from __future__ import annotations

import csv
import io
import shutil
import sqlite3
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace
from zipfile import ZipFile

import pytest
from sqlalchemy import Engine

from app.application.backup.service import BackupService
from app.application.exports.service import ExportSection, ExportService
from app.domain.entities.category import Category
from app.domain.entities.currency import Currency
from app.domain.value_objects.money import Money
from app.infrastructure.backup.sqlite_backup import (
    BackupError,
    SqliteBackupGateway,
)
from app.infrastructure.config.settings import Settings
from app.infrastructure.database.session import create_session_factory
from app.infrastructure.database.unit_of_work import (
    SqlAlchemyUnitOfWorkFactory,
)
from app.infrastructure.exports.zip_csv_export import ZipCsvExportGateway

USD = Currency("USD", "US Dollar", 2)


@pytest.fixture
def unit_of_work_factory(migrated_engine: Engine) -> SqlAlchemyUnitOfWorkFactory:
    return SqlAlchemyUnitOfWorkFactory(
        create_session_factory(migrated_engine)
    )


@pytest.fixture
def backup_service(
    migrated_engine: Engine,
    sqlite_settings: Settings,
    unit_of_work_factory: SqlAlchemyUnitOfWorkFactory,
    tmp_path: Path,
) -> BackupService:
    return BackupService(
        unit_of_work_factory,
        SqliteBackupGateway(
            sqlite_settings.database_url,
            engine=migrated_engine,
        ),
        default_directory=str(tmp_path / "backups"),
    )


def _add_category(
    unit_of_work_factory: SqlAlchemyUnitOfWorkFactory, name: str
) -> None:
    with unit_of_work_factory.unit_of_work() as uow:
        uow.categories.add(Category(name=name))
        uow.commit()


def _category_names(
    unit_of_work_factory: SqlAlchemyUnitOfWorkFactory,
) -> list[str]:
    with unit_of_work_factory.unit_of_work() as uow:
        return [category.name for category in uow.categories.list_all()]


def test_backup_and_restore_round_trip(
    backup_service: BackupService,
    unit_of_work_factory: SqlAlchemyUnitOfWorkFactory,
    tmp_path: Path,
) -> None:
    _add_category(unit_of_work_factory, "Before backup")

    artifact = backup_service.create_backup()
    backup_path = Path(artifact.path)

    assert backup_path.is_file()
    assert artifact.size_bytes > 0
    assert artifact.schema_revision == "0012_query_indexes"
    assert backup_path.parent == (tmp_path / "backups").resolve()

    validation = backup_service.validate_backup(artifact.path)
    assert validation.valid is True
    assert validation.schema_revision == "0012_query_indexes"

    _add_category(unit_of_work_factory, "Created after backup")
    assert set(_category_names(unit_of_work_factory)) == {
        "Before backup",
        "Created after backup",
    }

    result = backup_service.restore_backup(artifact.path)

    assert Path(result.safety_backup.path).is_file()
    assert result.restored_backup.valid is True
    assert _category_names(unit_of_work_factory) == ["Before backup"]


def test_backup_directory_setting_is_persisted(
    backup_service: BackupService,
    tmp_path: Path,
) -> None:
    custom = tmp_path / "custom-backups"

    saved = backup_service.set_backup_directory(str(custom))

    assert saved == str(custom.resolve())
    assert custom.is_dir()
    assert backup_service.get_backup_directory() == saved


def test_invalid_backup_is_rejected(
    backup_service: BackupService,
    tmp_path: Path,
) -> None:
    invalid = tmp_path / "not-a-backup.db"
    invalid.write_text("not a sqlite database", encoding="utf-8")

    validation = backup_service.validate_backup(str(invalid))

    assert validation.valid is False
    assert "SQLite" in validation.message


def test_backup_rejects_a_different_schema_revision(
    backup_service: BackupService,
) -> None:
    artifact = backup_service.create_backup()

    with closing(sqlite3.connect(artifact.path)) as connection:
        connection.execute(
            "UPDATE alembic_version SET version_num = '0001_baseline'"
        )
        connection.commit()

    with pytest.raises(ValueError, match="schema revision"):
        backup_service.restore_backup(artifact.path)


def test_backup_with_a_missing_required_table_is_rejected(
    backup_service: BackupService,
    tmp_path: Path,
) -> None:
    artifact = backup_service.create_backup()
    incomplete = tmp_path / "incomplete.db"
    shutil.copy2(artifact.path, incomplete)

    with closing(sqlite3.connect(incomplete)) as connection:
        connection.execute("DROP TABLE settings")
        connection.commit()

    validation = backup_service.validate_backup(str(incomplete))

    assert validation.valid is False
    assert "missing required tables" in validation.message
    assert "settings" in validation.message


def test_live_database_cannot_be_selected_as_a_restore_source(
    backup_service: BackupService,
    sqlite_settings: Settings,
) -> None:
    database_path = sqlite_settings.database_url.removeprefix("sqlite:///")

    validation = backup_service.validate_backup(database_path)

    assert validation.valid is False
    assert "restore source" in validation.message


def test_backup_directory_must_not_be_a_file(
    backup_service: BackupService,
    tmp_path: Path,
) -> None:
    not_a_directory = tmp_path / "backup-file"
    not_a_directory.write_text("not a directory", encoding="utf-8")

    with pytest.raises(BackupError, match="could not be created"):
        backup_service.set_backup_directory(str(not_a_directory))


def _fake_services():
    account = SimpleNamespace(
        account_id=1,
        name="Cash",
        account_type="CASH",
        currency_code="USD",
        balance=Money("12.50", USD),
        is_active=True,
        notes="Main wallet",
    )
    empty_returns = SimpleNamespace(
        list_customer_returns=lambda: (),
        list_supplier_returns=lambda: (),
    )
    return SimpleNamespace(
        accounts=SimpleNamespace(
            list_accounts=lambda **kwargs: (account,)
        ),
        inventory=SimpleNamespace(list_stock=lambda: ()),
        purchases=SimpleNamespace(list_purchases=lambda: ()),
        sales=SimpleNamespace(list_sales=lambda: ()),
        returns=empty_returns,
    )


def _export_service() -> ExportService:
    services = _fake_services()
    return ExportService(
        services.accounts,
        services.inventory,
        services.purchases,
        services.sales,
        services.returns,
        ZipCsvExportGateway(),
    )


def test_export_writes_selected_sections_to_zip(tmp_path: Path) -> None:
    export = _export_service()
    destination = tmp_path / "selected.zip"

    result = export.export(
        str(destination),
        (ExportSection.ACCOUNTS, ExportSection.INVENTORY),
    )

    assert Path(result.path) == destination.resolve()
    assert result.table_names == ("accounts", "inventory")
    assert result.row_count == 1
    assert destination.is_file()

    with ZipFile(destination) as archive:
        assert archive.namelist() == ["accounts.csv", "inventory.csv"]
        content = archive.read("accounts.csv").decode("utf-8-sig")
        rows = list(csv.reader(io.StringIO(content)))

    assert rows[0][0] == "Account ID"
    assert rows[1] == [
        "1",
        "Cash",
        "CASH",
        "USD",
        "12.50 USD",
        "Yes",
        "Main wallet",
    ]


def test_export_all_sections_includes_return_tables(tmp_path: Path) -> None:
    export = _export_service()

    result = export.export(str(tmp_path / "all.zip"))

    assert result.table_names == (
        "accounts",
        "inventory",
        "purchases",
        "sales",
        "customer_returns",
        "supplier_returns",
    )


def test_export_requires_at_least_one_section(tmp_path: Path) -> None:
    export = _export_service()

    with pytest.raises(ValueError, match="at least one"):
        export.export(str(tmp_path / "empty.zip"), ())
