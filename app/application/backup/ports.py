"""Backup use-case contracts and result models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class BackupArtifact:
    """A validated backup file created by the backup gateway."""

    path: str
    filename: str
    size_bytes: int
    created_at: datetime
    schema_revision: str


@dataclass(frozen=True, slots=True)
class BackupValidation:
    """Result of validating a candidate backup file."""

    path: str
    valid: bool
    message: str
    schema_revision: str | None = None
    size_bytes: int = 0


@dataclass(frozen=True, slots=True)
class RestoreResult:
    """A completed restore plus the automatic safety backup."""

    restored_backup: BackupValidation
    safety_backup: BackupArtifact


class BackupGateway(Protocol):
    """Filesystem and SQLite operations used by the backup service."""

    def ensure_directory(self, directory: str) -> str:
        """Create a backup directory and return its canonical path."""
        ...

    def create_backup(
        self,
        directory: str,
        *,
        prefix: str = "resale-manager",
    ) -> BackupArtifact:
        """Create a consistent SQLite backup in ``directory``."""
        ...

    def validate_backup(self, path: str) -> BackupValidation:
        """Check that ``path`` is an intact, compatible backup."""
        ...

    def restore_backup(self, path: str) -> None:
        """Replace the live database with a previously validated backup."""
        ...
