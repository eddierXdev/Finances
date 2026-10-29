"""Settings data-operation UI tests (headless)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from PySide6.QtWidgets import QCheckBox, QLabel, QLineEdit, QPushButton

from app.application.exports.service import ExportSection
from app.infrastructure.config.settings import Settings
from app.presentation.desktop.dialogs.export import ExportDialog
from app.presentation.desktop.views.settings import SettingsPage


class FakeBackup:
    def __init__(self, directory: str) -> None:
        self.directory = directory
        self.created = 0

    def get_backup_directory(self) -> str:
        return self.directory

    def create_backup(self):
        self.created += 1
        return SimpleNamespace(
            filename="backup.db",
            size_bytes=2048,
            path=str(Path(self.directory) / "backup.db"),
        )


class FakeExport:
    def __init__(self) -> None:
        self.calls = []

    def export(self, destination, sections):
        self.calls.append((destination, tuple(sections)))
        return SimpleNamespace(
            path=destination,
            row_count=4,
            size_bytes=123,
        )


def test_settings_page_shows_effective_backup_directory(qapp) -> None:
    page = SettingsPage(
        Settings(),
        backup=FakeBackup(r"C:\Backups"),
    )
    try:
        value = page.findChild(QLabel, "settingsValue_backup_directory")
        create = page.findChild(QPushButton, "createBackupButton")
        restore = page.findChild(QPushButton, "restoreBackupButton")
        assert value is not None and value.text() == r"C:\Backups"
        assert create is not None and create.isEnabled()
        assert restore is not None and restore.isEnabled()
    finally:
        page.close()


def test_settings_page_creates_a_backup(qapp) -> None:
    backup = FakeBackup(r"C:\Backups")
    page = SettingsPage(Settings(), backup=backup)
    try:
        page.findChild(QPushButton, "createBackupButton").click()

        status = page.findChild(QLabel, "settingsDataStatus")
        assert backup.created == 1
        assert status is not None and "Backup created" in status.text()
        assert "backup.db" in status.text()
    finally:
        page.close()


def test_settings_page_disables_data_actions_without_services(qapp) -> None:
    page = SettingsPage(Settings())
    try:
        assert not page.findChild(
            QPushButton, "createBackupButton"
        ).isEnabled()
        assert not page.findChild(
            QPushButton, "restoreBackupButton"
        ).isEnabled()
        assert not page.findChild(
            QPushButton, "exportDataButton"
        ).isEnabled()
    finally:
        page.close()


def test_export_dialog_passes_selected_sections(qapp, tmp_path: Path) -> None:
    export = FakeExport()
    dialog = ExportDialog(export)
    try:
        dialog.findChild(
            QLineEdit, "exportDestination"
        ).setText(str(tmp_path / "business.zip"))
        dialog.findChild(
            QCheckBox, "exportSection_sales"
        ).setChecked(False)

        dialog.findChild(QPushButton, "exportConfirmButton").click()

        assert dialog.export_result is not None
        assert dialog.export_result.path == str(tmp_path / "business.zip")
        assert export.calls == [
            (
                str(tmp_path / "business.zip"),
                (
                    ExportSection.ACCOUNTS,
                    ExportSection.INVENTORY,
                    ExportSection.PURCHASES,
                    ExportSection.RETURNS,
                ),
            )
        ]
        assert dialog.result() == ExportDialog.DialogCode.Accepted
    finally:
        dialog.close()
