"""ZIP-of-CSV export gateway."""

from __future__ import annotations

import csv
import io
import os
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from app.application.exports.ports import ExportArtifact, ExportTable


class ExportError(RuntimeError):
    """Raised when an export archive cannot be written."""


class ZipCsvExportGateway:
    """Write one UTF-8 CSV file per table inside a ZIP archive."""

    def __init__(
        self,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._clock = clock or (lambda: datetime.now(UTC))

    def write_archive(
        self,
        destination: str,
        tables: tuple[ExportTable, ...],
    ) -> ExportArtifact:
        if not tables:
            raise ValueError("At least one export table is required.")

        path = Path(destination).expanduser()
        if path.suffix.lower() != ".zip":
            path = path.with_suffix(".zip")
        path = path.resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.partial")

        try:
            with ZipFile(temporary, "w", compression=ZIP_DEFLATED) as archive:
                for table in tables:
                    archive.writestr(
                        f"{table.name}.csv",
                        self._csv_bytes(table),
                    )
            os.replace(temporary, path)
        except (OSError, ValueError) as exc:
            raise ExportError(f"The export could not be written: {exc}") from exc
        finally:
            temporary.unlink(missing_ok=True)

        return ExportArtifact(
            path=str(path),
            size_bytes=path.stat().st_size,
            generated_at=self._clock(),
        )

    @staticmethod
    def _csv_bytes(table: ExportTable) -> bytes:
        stream = io.StringIO(newline="")
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(table.headers)
        for row in table.rows:
            if len(row) != len(table.headers):
                raise ValueError(
                    f"Table {table.name!r} has a row with the wrong column count."
                )
            writer.writerow(row)
        return stream.getvalue().encode("utf-8-sig")
