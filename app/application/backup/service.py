"""Application service for local backups and restores."""

from __future__ import annotations

from app.application.backup.ports import (
    BackupArtifact,
    BackupGateway,
    BackupValidation,
    RestoreResult,
)
from app.application.unit_of_work import UnitOfWorkFactory

BACKUP_DIRECTORY_KEY = "backup_directory"


class BackupService:
    """Coordinate backup settings, file creation, validation and restore."""

    def __init__(
        self,
        unit_of_work: UnitOfWorkFactory,
        gateway: BackupGateway,
        *,
        default_directory: str,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._gateway = gateway
        self._default_directory = default_directory

    def get_backup_directory(self) -> str:
        """Return the configured backup directory, falling back to the default."""
        with self._unit_of_work.unit_of_work() as uow:
            stored = uow.settings.get(BACKUP_DIRECTORY_KEY)
        return stored or self._default_directory

    def set_backup_directory(self, directory: str) -> str:
        """Persist a new backup directory and return its canonical path."""
        cleaned = directory.strip()
        if not cleaned:
            raise ValueError("The backup directory cannot be empty.")

        canonical = self._gateway.ensure_directory(cleaned)
        with self._unit_of_work.unit_of_work() as uow:
            uow.settings.set(BACKUP_DIRECTORY_KEY, canonical)
            uow.commit()
        return canonical

    def create_backup(self) -> BackupArtifact:
        """Create a validated backup in the configured directory."""
        return self._gateway.create_backup(self.get_backup_directory())

    def validate_backup(self, path: str) -> BackupValidation:
        """Validate a backup without modifying the live database."""
        return self._gateway.validate_backup(path)

    def restore_backup(self, path: str) -> RestoreResult:
        """Restore a compatible backup after creating a safety copy."""
        validation = self._gateway.validate_backup(path)
        if not validation.valid:
            raise ValueError(validation.message)

        safety = self._gateway.create_backup(
            self.get_backup_directory(),
            prefix="pre-restore",
        )
        self._gateway.restore_backup(path)
        return RestoreResult(
            restored_backup=validation,
            safety_backup=safety,
        )
