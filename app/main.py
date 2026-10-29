"""Application entry point."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.infrastructure.config.settings import get_settings
from app.infrastructure.database.migrations import (
    DatabaseMigrationError,
    upgrade_database,
)
from app.infrastructure.database.session import (
    create_database_engine,
    create_session_factory,
)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="resale-manager")
    parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "prepare and verify the database, then exit without opening the UI"
        ),
    )
    return parser.parse_args(argv)


def _prepare_runtime() -> None:
    """Keep portable data next to a frozen executable."""
    if getattr(sys, "frozen", False):
        os.chdir(Path(sys.executable).resolve().parent)


def _write_frozen_report(filename: str, lines: Sequence[str]) -> None:
    """Write a diagnostics report beside a frozen executable."""
    if not getattr(sys, "frozen", False):
        return

    try:
        report_path = Path(sys.executable).resolve().parent / filename
        report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except OSError:
        pass


def _report_startup_failure(
    message: str,
    *,
    show_dialog: bool = True,
) -> None:
    print(message, file=sys.stderr)
    if not getattr(sys, "frozen", False):
        return

    _write_frozen_report("startup-error.log", [message])

    if not show_dialog:
        return

    try:
        from PySide6.QtWidgets import QApplication, QMessageBox

        application = QApplication.instance()
        owns_application = application is None
        if owns_application:
            application = QApplication([])
        QMessageBox.critical(None, "Resale Manager", message)
        if owns_application:
            application.quit()
    except Exception:
        # The process still exits with a failure code if Qt cannot start.
        pass


def main(argv: Sequence[str] | None = None) -> int:
    """Open the desktop application, or run a diagnostics check."""
    args = _parse_args(argv)
    _prepare_runtime()

    try:
        settings = get_settings()
    except Exception as exc:
        _report_startup_failure(
            f"Invalid application configuration: {exc}",
            show_dialog=not args.check,
        )
        return 1

    try:
        engine = create_database_engine(settings)
    except Exception as exc:
        _report_startup_failure(
            f"Invalid database configuration: {exc}",
            show_dialog=not args.check,
        )
        return 1

    try:
        revision = upgrade_database(settings.database_url)
    except DatabaseMigrationError as exc:
        engine.dispose()
        _report_startup_failure(str(exc), show_dialog=not args.check)
        return 1

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        engine.dispose()
        _report_startup_failure(
            f"Database connection failed: {exc}",
            show_dialog=not args.check,
        )
        return 1

    if args.check:
        engine.dispose()
        lines = [
            f"Resale Manager ready (env={settings.app_env}).",
            f"Database connection OK: {settings.database_url}",
            f"Schema revision OK: {revision} (head)",
        ]
        for line in lines:
            print(line)
        _write_frozen_report("diagnostics.txt", lines)
        return 0

    from app.presentation.desktop.app import run_desktop

    try:
        return run_desktop(
            settings,
            create_session_factory(engine),
            engine,
        )
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
