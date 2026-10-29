"""SQLite backup and restore gateway."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import Engine

from app.application.backup.ports import BackupArtifact, BackupValidation
from app.infrastructure.database.session import _sqlite_file_path


class BackupError(RuntimeError):
    """Base error for local backup operations."""


class UnsupportedBackupError(BackupError):
    """Raised when the configured database cannot be backed up this way."""


class InvalidBackupError(BackupError):
    """Raised when a backup is missing, damaged or incompatible."""


class SqliteBackupGateway:
    """Create consistent SQLite copies and restore them in place.

    Restore uses SQLite's online backup API rather than replacing the database
    file. This avoids Windows file-lock problems while keeping the restore
    atomic. The engine is disposed first so no pooled connection can keep stale
    pages or an open transaction.
    """

    def __init__(
        self,
        database_url: str,
        *,
        engine: Engine | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        database_path = _sqlite_file_path(database_url)
        if database_path is None:
            raise UnsupportedBackupError(
                "Local backup is only available for file-based SQLite databases."
            )
        self._database_path = database_path.expanduser().resolve()
        self._engine = engine
        self._clock = clock or (lambda: datetime.now(UTC))

    def ensure_directory(self, directory: str) -> str:
        path = Path(directory).expanduser()
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise BackupError(
                f"The backup directory could not be created: {exc}"
            ) from exc
        if not path.is_dir():
            raise BackupError(f"The backup path is not a directory: {path}")
        return str(path.resolve())

    def create_backup(
        self,
        directory: str,
        *,
        prefix: str = "resale-manager",
    ) -> BackupArtifact:
        if not self._database_path.is_file():
            raise BackupError(
                f"The live database does not exist: {self._database_path}"
            )

        directory_path = Path(self.ensure_directory(directory))
        created_at = self._clock()
        filename = (
            f"{prefix}-{created_at.astimezone(UTC):%Y%m%d-%H%M%S-%f}.db"
        )
        destination = directory_path / filename
        temporary = directory_path / f".{filename}.partial"

        try:
            self._copy_database(self._database_path, temporary)
            validation = self.validate_backup(str(temporary))
            if not validation.valid:
                raise BackupError(
                    "The created backup failed validation: "
                    f"{validation.message}"
                )
            temporary.replace(destination)
        except BackupError:
            raise
        except (OSError, sqlite3.Error) as exc:
            raise BackupError(f"The backup could not be created: {exc}") from exc
        finally:
            temporary.unlink(missing_ok=True)

        return BackupArtifact(
            path=str(destination),
            filename=filename,
            size_bytes=destination.stat().st_size,
            created_at=created_at,
            schema_revision=validation.schema_revision or "",
        )

    def validate_backup(self, path: str) -> BackupValidation:
        candidate = Path(path).expanduser()
        if not candidate.is_file():
            return BackupValidation(
                path=str(candidate),
                valid=False,
                message="The selected backup does not exist.",
            )
        if candidate.resolve() == self._database_path:
            return BackupValidation(
                path=str(candidate.resolve()),
                valid=False,
                message=(
                    "The live database cannot be used as a restore source."
                ),
                size_bytes=candidate.stat().st_size,
            )

        try:
            with closing(
                self._connect(candidate, query_only=True)
            ) as connection:
                integrity = connection.execute("PRAGMA integrity_check").fetchall()
                if not integrity or any(row[0] != "ok" for row in integrity):
                    return BackupValidation(
                        path=str(candidate),
                        valid=False,
                        message="The selected backup failed SQLite integrity checks.",
                        size_bytes=candidate.stat().st_size,
                    )

                violation = connection.execute(
                    "PRAGMA foreign_key_check"
                ).fetchone()
                if violation is not None:
                    return BackupValidation(
                        path=str(candidate),
                        valid=False,
                        message=(
                            "The selected backup has a foreign-key violation "
                            f"in table {violation[0]!r}."
                        ),
                        size_bytes=candidate.stat().st_size,
                    )

                revision = self._read_schema_revision(connection)
                if revision is None:
                    return BackupValidation(
                        path=str(candidate),
                        valid=False,
                        message=(
                            "The selected file is not a Resale Manager backup "
                            "with a recorded schema revision."
                        ),
                        size_bytes=candidate.stat().st_size,
                    )
                backup_tables = self._table_names(connection)
        except sqlite3.Error as exc:
            return BackupValidation(
                path=str(candidate),
                valid=False,
                message=f"The selected file is not a readable SQLite backup: {exc}",
                size_bytes=candidate.stat().st_size,
            )

        current_revision = self._current_schema_revision()
        if current_revision is None:
            return BackupValidation(
                path=str(candidate),
                valid=False,
                message=(
                    "The current database schema could not be read, so the "
                    "backup cannot be checked for compatibility."
                ),
                schema_revision=revision,
                size_bytes=candidate.stat().st_size,
            )
        if revision != current_revision:
            return BackupValidation(
                path=str(candidate),
                valid=False,
                message=(
                    "The selected backup uses schema revision "
                    f"{revision!r}, but this installation uses "
                    f"{current_revision!r}. Backups must match the current "
                    "schema."
                ),
                schema_revision=revision,
                size_bytes=candidate.stat().st_size,
            )

        with closing(
            self._connect(self._database_path, query_only=True)
        ) as live_connection:
            live_tables = self._table_names(live_connection)
        missing = live_tables - backup_tables
        if missing:
            return BackupValidation(
                path=str(candidate),
                valid=False,
                message=(
                    "The selected backup is missing required tables: "
                    + ", ".join(sorted(missing))
                ),
                schema_revision=revision,
                size_bytes=candidate.stat().st_size,
            )

        return BackupValidation(
            path=str(candidate.resolve()),
            valid=True,
            message="The backup is intact and compatible with this installation.",
            schema_revision=revision,
            size_bytes=candidate.stat().st_size,
        )

    def restore_backup(self, path: str) -> None:
        validation = self.validate_backup(path)
        if not validation.valid:
            raise InvalidBackupError(validation.message)

        source_path = Path(path).expanduser().resolve()
        if source_path == self._database_path:
            raise InvalidBackupError(
                "The live database cannot be restored from itself."
            )

        current_revision = self._current_schema_revision()
        if validation.schema_revision != current_revision:
            raise InvalidBackupError(
                "The selected backup uses schema revision "
                f"{validation.schema_revision!r}, but this installation uses "
                f"{current_revision!r}. Backups must match the current schema."
            )

        if self._engine is not None:
            self._engine.dispose()

        try:
            with closing(
                self._connect(source_path, query_only=True)
            ) as source:
                with closing(self._connect(self._database_path)) as target:
                    source.backup(target)
                    target.commit()
        except sqlite3.Error as exc:
            raise BackupError(f"The backup could not be restored: {exc}") from exc

    def _current_schema_revision(self) -> str | None:
        if not self._database_path.is_file():
            return None
        with closing(
            self._connect(self._database_path, query_only=True)
        ) as connection:
            return self._read_schema_revision(connection)

    @staticmethod
    def _connect(path: Path, *, query_only: bool = False) -> sqlite3.Connection:
        connection = sqlite3.connect(str(path))
        if query_only:
            connection.execute("PRAGMA query_only=ON")
        return connection

    @staticmethod
    def _read_schema_revision(
        connection: sqlite3.Connection,
    ) -> str | None:
        try:
            row = connection.execute(
                "SELECT version_num FROM alembic_version"
            ).fetchone()
        except sqlite3.Error:
            return None
        return str(row[0]) if row is not None and row[0] else None

    @staticmethod
    def _table_names(connection: sqlite3.Connection) -> set[str]:
        rows = connection.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        return {str(row[0]) for row in rows}

    @staticmethod
    def _copy_database(source: Path, destination: Path) -> None:
        with closing(sqlite3.connect(str(source))) as source_connection:
            with closing(
                sqlite3.connect(str(destination))
            ) as target_connection:
                source_connection.backup(target_connection)
                target_connection.commit()
