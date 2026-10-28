"""Application entry point."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.infrastructure.config.settings import get_settings
from app.infrastructure.database.session import (
    create_database_engine,
    create_session_factory,
)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="resale-manager")
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the database connection and exit without opening the UI",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Open the desktop application, or run a diagnostics check."""
    args = _parse_args(argv)
    settings = get_settings()
    engine = create_database_engine(settings)

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        engine.dispose()
        print(f"Database connection failed: {exc}", file=sys.stderr)
        return 1

    if args.check:
        engine.dispose()
        print(f"Resale Manager ready (env={settings.app_env}).")
        print(f"Database connection OK: {settings.database_url}")
        print("Apply schema migrations with: alembic upgrade head")
        return 0

    from app.presentation.desktop.app import run_desktop

    try:
        return run_desktop(settings, create_session_factory(engine))
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
