"""Export use-case contracts and table models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ExportTable:
    """One CSV table ready for the export gateway."""

    name: str
    headers: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]


@dataclass(frozen=True, slots=True)
class ExportArtifact:
    """A written export archive."""

    path: str
    size_bytes: int
    generated_at: datetime


class ExportGateway(Protocol):
    """Filesystem writer for business-data exports."""

    def write_archive(
        self,
        destination: str,
        tables: tuple[ExportTable, ...],
    ) -> ExportArtifact:
        """Write all tables to a single archive and return its details."""
        ...
