"""Entry-point hardening tests."""

from __future__ import annotations

from pathlib import Path

from app.infrastructure.config.settings import Settings
from app.infrastructure.database.migrations import (
    current_revision,
    head_revision,
)
from app.main import main


def _install_settings(monkeypatch, database_url: str) -> None:
    monkeypatch.setattr(
        "app.main.get_settings",
        lambda: Settings(database_url=database_url, _env_file=None),
    )


def test_check_prepares_a_fresh_database(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    database_url = f"sqlite:///{(tmp_path / 'fresh.db').as_posix()}"
    _install_settings(monkeypatch, database_url)

    exit_code = main(["--check"])

    output = capsys.readouterr()
    assert exit_code == 0
    assert "Schema revision OK" in output.out
    assert current_revision(database_url) == head_revision()


def test_check_reports_a_corrupt_database(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    database_path = tmp_path / "corrupt.db"
    database_path.write_text("not sqlite", encoding="utf-8")
    _install_settings(
        monkeypatch,
        f"sqlite:///{database_path.as_posix()}",
    )

    exit_code = main(["--check"])

    output = capsys.readouterr()
    assert exit_code == 1
    assert "could not be upgraded" in output.err


def test_check_reports_invalid_configuration(monkeypatch, capsys) -> None:
    def fail():
        raise ValueError("invalid FX_FRESHNESS_HOURS")

    monkeypatch.setattr("app.main.get_settings", fail)

    exit_code = main(["--check"])

    output = capsys.readouterr()
    assert exit_code == 1
    assert "Invalid application configuration" in output.err
    assert "invalid FX_FRESHNESS_HOURS" in output.err


def test_check_reports_invalid_database_configuration(
    monkeypatch,
    capsys,
) -> None:
    _install_settings(monkeypatch, "not-a-database-url")

    exit_code = main(["--check"])

    output = capsys.readouterr()
    assert exit_code == 1
    assert "Invalid database configuration" in output.err
