"""Dialog for selecting and exporting business information."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.application.exports.service import (
    ExportResult,
    ExportSection,
    ExportService,
)

_SECTION_LABELS = {
    ExportSection.ACCOUNTS: "Accounts and balances",
    ExportSection.INVENTORY: "Current inventory",
    ExportSection.PURCHASES: "Purchases",
    ExportSection.SALES: "Sales",
    ExportSection.RETURNS: "Customer and supplier returns",
}


class ExportDialog(QDialog):
    """Choose business sections and write them to a ZIP of CSV files."""

    def __init__(
        self,
        exports: ExportService,
        *,
        default_directory: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._exports = exports
        self._default_directory = default_directory
        self._checks: dict[ExportSection, QCheckBox] = {}
        self.export_result: ExportResult | None = None
        self.setWindowTitle("Export business data")
        self.setModal(True)
        self.resize(560, 480)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel("Export business data", self)
        title.setObjectName("dialogTitle")
        layout.addWidget(title)

        description = QLabel(
            "Select the information to include. Each selected section is "
            "written as a separate CSV file inside one ZIP archive.",
            self,
        )
        description.setObjectName("pageDescription")
        description.setWordWrap(True)
        layout.addWidget(description)

        sections = QGroupBox("Sections", self)
        sections_layout = QVBoxLayout(sections)
        for section in ExportSection:
            check = QCheckBox(_SECTION_LABELS[section], sections)
            check.setObjectName(f"exportSection_{section.value}")
            check.setChecked(True)
            sections_layout.addWidget(check)
            self._checks[section] = check
        layout.addWidget(sections)

        destination_group = QGroupBox("Destination", self)
        destination_layout = QHBoxLayout(destination_group)
        self._destination = QLineEdit(destination_group)
        self._destination.setObjectName("exportDestination")
        self._destination.setPlaceholderText("Choose a .zip file")
        destination_layout.addWidget(self._destination, 1)
        browse = QPushButton("Browse...", destination_group)
        browse.setObjectName("browseExportButton")
        browse.clicked.connect(self._choose_destination)
        destination_layout.addWidget(browse)
        layout.addWidget(destination_group)

        hint = QLabel(
            "The archive is created locally and works without an Internet "
            "connection.",
            self,
        )
        hint.setObjectName("fieldHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        layout.addStretch(1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        confirm = buttons.button(QDialogButtonBox.StandardButton.Ok)
        confirm.setText("Export")
        confirm.setObjectName("exportConfirmButton")
        confirm.setProperty("variant", "primary")
        buttons.accepted.connect(self._export)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _choose_destination(self) -> None:
        path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export business data",
            self._default_directory,
            "ZIP archives (*.zip);;All files (*)",
        )
        if path:
            self._destination.setText(path)

    def _selected_sections(self) -> tuple[ExportSection, ...]:
        return tuple(
            section
            for section, check in self._checks.items()
            if check.isChecked()
        )

    def _export(self) -> None:
        destination = self._destination.text().strip()
        if not destination:
            QMessageBox.warning(
                self,
                "Export business data",
                "Choose a destination .zip file.",
            )
            return

        sections = self._selected_sections()
        if not sections:
            QMessageBox.warning(
                self,
                "Export business data",
                "Select at least one section to export.",
            )
            return

        try:
            self.export_result = self._exports.export(destination, sections)
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Export failed",
                str(exc),
            )
            return

        self.accept()
