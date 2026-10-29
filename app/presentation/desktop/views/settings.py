"""Settings screen with UI preferences, backup, restore and export actions."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.application.backup.service import BackupService
from app.application.exports.service import ExportService
from app.application.preferences.service import UiPreferencesService
from app.infrastructure.config.settings import Settings
from app.presentation.desktop.dialogs.export import ExportDialog
from app.presentation.desktop.i18n.translator import (
    SUPPORTED_LANGUAGES,
    Translator,
)
from app.presentation.desktop.themes.theme_manager import (
    SUPPORTED_THEMES,
    ThemeManager,
)


class SettingsPage(QWidget):
    """Show runtime configuration and manage local data operations."""

    def __init__(
        self,
        settings: Settings,
        *,
        backup: BackupService | None = None,
        exports: ExportService | None = None,
        translator: Translator | None = None,
        theme_manager: ThemeManager | None = None,
        preferences: UiPreferencesService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._settings = settings
        self._backup = backup
        self._exports = exports
        self._translator = translator or Translator()
        self._theme_manager = theme_manager or ThemeManager()
        self._preferences = preferences
        self._values: dict[str, QLabel] = {}
        self._form_labels: dict[str, QLabel] = {}
        self._label_keys: dict[str, str] = {}
        self._backup_buttons: list[QPushButton] = []

        self.setObjectName("settingsPage")
        self._build_ui()
        self._translator.language_changed.connect(self._on_language_changed)
        self._theme_manager.theme_changed.connect(self._on_theme_changed)
        self.retranslate()
        self.reload()

    def _build_ui(self) -> None:
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(0)

        self._scroll_area = QScrollArea(self)
        self._scroll_area.setObjectName("settingsScrollArea")
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        content = QWidget(self._scroll_area)
        content.setObjectName("settingsContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(32, 28, 32, 24)
        layout.setSpacing(14)

        header = QHBoxLayout()
        titles = QVBoxLayout()
        self._title = QLabel(self)
        self._title.setObjectName("pageTitle")
        titles.addWidget(self._title)
        self._description = QLabel(self)
        self._description.setObjectName("pageDescription")
        self._description.setWordWrap(True)
        titles.addWidget(self._description)
        header.addLayout(titles, 1)

        self._refresh_button = QPushButton(self)
        self._refresh_button.setObjectName("refreshSettingsButton")
        self._refresh_button.clicked.connect(self.reload)
        header.addWidget(self._refresh_button)
        layout.addLayout(header)

        layout.addWidget(self._build_preferences_group())

        self._application_group = QGroupBox(self)
        application_form = QFormLayout(self._application_group)
        self._add(application_form, "app_env", "settings.environment")
        self._add(application_form, "database_url", "settings.database_url")
        self._add(application_form, "base_currency", "settings.base_currency")
        layout.addWidget(self._application_group)

        self._exchange_group = QGroupBox(self)
        exchange_form = QFormLayout(self._exchange_group)
        self._add(exchange_form, "fx_provider", "settings.provider")
        self._add(exchange_form, "fx_auto_update", "settings.auto_updates")
        self._add(
            exchange_form,
            "fx_freshness_hours",
            "settings.freshness_hours",
        )
        self._add(
            exchange_form,
            "eltoque_api_url",
            "settings.eltoque_api_url",
        )
        self._add(
            exchange_form,
            "eltoque_timeout_seconds",
            "settings.eltoque_timeout",
        )
        self._add(exchange_form, "eltoque_api_token", "settings.eltoque_token")
        layout.addWidget(self._exchange_group)

        self._analytics_group = QGroupBox(self)
        analytics_form = QFormLayout(self._analytics_group)
        self._add(
            analytics_form,
            "analytics_slow_moving_days",
            "settings.slow_moving",
        )
        layout.addWidget(self._analytics_group)

        layout.addWidget(self._build_data_group())

        self._data_note = QLabel(self)
        self._data_note.setObjectName("fieldHint")
        self._data_note.setWordWrap(True)
        layout.addWidget(self._data_note)
        layout.addStretch(1)

        self._scroll_area.setWidget(content)
        page_layout.addWidget(self._scroll_area)

    def _build_preferences_group(self) -> QGroupBox:
        self._preferences_group = QGroupBox(self)
        preferences_layout = QVBoxLayout(self._preferences_group)

        preferences_form = QFormLayout()
        preferences_form.setRowWrapPolicy(
            QFormLayout.RowWrapPolicy.WrapLongRows
        )
        preferences_form.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
        )

        self._language_label = QLabel(self)
        self._language_combo = QComboBox(self._preferences_group)
        self._language_combo.setObjectName("uiLanguageCombo")
        self._language_combo.setMinimumWidth(180)
        self._language_label.setBuddy(self._language_combo)
        self._language_combo.currentIndexChanged.connect(
            self._change_language
        )
        preferences_form.addRow(self._language_label, self._language_combo)

        self._theme_label = QLabel(self)
        self._theme_combo = QComboBox(self._preferences_group)
        self._theme_combo.setObjectName("uiThemeCombo")
        self._theme_combo.setMinimumWidth(180)
        self._theme_label.setBuddy(self._theme_combo)
        self._theme_combo.currentIndexChanged.connect(self._change_theme)
        preferences_form.addRow(self._theme_label, self._theme_combo)

        preferences_layout.addLayout(preferences_form)
        self._preference_status = QLabel(self._preferences_group)
        self._preference_status.setObjectName("settingsPreferencesStatus")
        self._preference_status.setWordWrap(True)
        preferences_layout.addWidget(self._preference_status)
        return self._preferences_group

    def _build_data_group(self) -> QGroupBox:
        self._data_group = QGroupBox(self)
        data_layout = QVBoxLayout(self._data_group)

        data_form = QFormLayout()
        self._add(data_form, "backup_directory", "settings.backup_folder")
        data_layout.addLayout(data_form)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        self._change_folder_button = QPushButton(self._data_group)
        self._change_folder_button.setObjectName(
            "changeBackupDirectoryButton"
        )
        self._change_folder_button.clicked.connect(
            self._change_backup_directory
        )
        actions.addWidget(self._change_folder_button)

        self._create_backup_button = QPushButton(self._data_group)
        self._create_backup_button.setObjectName("createBackupButton")
        self._create_backup_button.setProperty("variant", "primary")
        self._create_backup_button.clicked.connect(self._create_backup)
        actions.addWidget(self._create_backup_button)

        self._restore_button = QPushButton(self._data_group)
        self._restore_button.setObjectName("restoreBackupButton")
        self._restore_button.clicked.connect(self._restore_backup)
        actions.addWidget(self._restore_button)

        self._export_button = QPushButton(self._data_group)
        self._export_button.setObjectName("exportDataButton")
        self._export_button.clicked.connect(self._export_data)
        actions.addWidget(self._export_button)

        actions.addStretch(1)
        data_layout.addLayout(actions)

        self._backup_buttons = [
            self._change_folder_button,
            self._create_backup_button,
            self._restore_button,
            self._export_button,
        ]
        if self._backup is None:
            for button in self._backup_buttons[:3]:
                button.setEnabled(False)
        if self._exports is None:
            self._export_button.setEnabled(False)

        self._data_status = QLabel("", self._data_group)
        self._data_status.setObjectName("settingsDataStatus")
        self._data_status.setWordWrap(True)
        data_layout.addWidget(self._data_status)
        return self._data_group

    def _add(
        self,
        form: QFormLayout,
        key: str,
        label_key: str,
    ) -> None:
        label = QLabel(self)
        value = QLabel(self)
        value.setObjectName(f"settingsValue_{key}")
        value.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        form.addRow(label, value)
        self._values[key] = value
        self._form_labels[key] = label
        self._label_keys[key] = label_key

    def retranslate(self) -> None:
        """Refresh every static label after a language change."""
        t = self._translator.tr
        self._title.setText(t("settings.title"))
        self._description.setText(t("settings.description"))
        self._refresh_button.setText(t("settings.refresh"))

        self._preferences_group.setTitle(t("settings.preferences_group"))
        self._language_label.setText(t("settings.language"))
        self._theme_label.setText(t("settings.theme"))
        self._language_combo.setAccessibleName(
            t("settings.language.accessible")
        )
        self._language_combo.setAccessibleDescription(
            t("settings.language.help")
        )
        self._theme_combo.setAccessibleName(t("settings.theme.accessible"))
        self._theme_combo.setAccessibleDescription(t("settings.theme.help"))
        self._update_combo_items(
            self._language_combo,
            SUPPORTED_LANGUAGES,
            "settings.language.option",
        )
        self._update_combo_items(
            self._theme_combo,
            SUPPORTED_THEMES,
            "settings.theme.option",
        )

        self._application_group.setTitle(t("settings.application_group"))
        self._exchange_group.setTitle(t("settings.exchange_group"))
        self._analytics_group.setTitle(t("settings.analytics_group"))
        self._data_group.setTitle(t("settings.data_group"))
        for key, label in self._form_labels.items():
            label.setText(t(self._label_keys[key]))

        self._change_folder_button.setText(t("settings.change_folder"))
        self._create_backup_button.setText(t("settings.create_backup"))
        self._restore_button.setText(t("settings.restore_backup"))
        self._export_button.setText(t("settings.export_data"))
        self._data_note.setText(t("settings.note"))

    def reload(self, *_args) -> None:
        settings = self._settings
        self._values["app_env"].setText(settings.app_env)
        self._values["database_url"].setText(settings.database_url)
        self._values["base_currency"].setText(settings.base_currency)
        self._values["fx_provider"].setText(settings.fx_provider)
        self._values["fx_auto_update"].setText(
            self._translator.tr("settings.enabled")
            if settings.fx_auto_update
            else self._translator.tr("settings.disabled")
        )
        self._values["fx_freshness_hours"].setText(
            str(settings.fx_freshness_hours)
        )
        self._values["eltoque_api_url"].setText(settings.eltoque_api_url)
        self._values["eltoque_timeout_seconds"].setText(
            str(settings.eltoque_timeout_seconds)
        )
        self._values["eltoque_api_token"].setText(
            self._translator.tr("settings.configured")
            if settings.eltoque_api_token
            else self._translator.tr("settings.not_configured")
        )
        self._values["analytics_slow_moving_days"].setText(
            str(settings.analytics_slow_moving_days)
        )

        self._sync_preferences()

        if self._backup is None:
            self._values["backup_directory"].setText(
                settings.backup_directory
            )
            return

        try:
            directory = self._backup.get_backup_directory()
        except Exception as exc:
            self._values["backup_directory"].setText(
                self._translator.tr("settings.unavailable")
            )
            self._set_status(
                self._translator.tr(
                    "settings.backup_read_error",
                    error=str(exc),
                )
            )
        else:
            self._values["backup_directory"].setText(directory)
            self._set_status("")

    def _sync_preferences(self) -> None:
        self._select_combo_data(
            self._language_combo,
            self._translator.language,
        )
        self._select_combo_data(
            self._theme_combo,
            self._theme_manager.theme,
        )

    @staticmethod
    def _select_combo_data(combo: QComboBox, value: str) -> None:
        index = combo.findData(value)
        if index < 0:
            return
        combo.blockSignals(True)
        try:
            combo.setCurrentIndex(index)
        finally:
            combo.blockSignals(False)

    def _update_combo_items(
        self,
        combo: QComboBox,
        values: tuple[str, ...],
        key_prefix: str,
    ) -> None:
        current = combo.currentData()
        combo.blockSignals(True)
        try:
            combo.clear()
            for value in values:
                combo.addItem(
                    self._translator.tr(f"{key_prefix}.{value}"),
                    value,
                )
            if isinstance(current, str):
                index = combo.findData(current)
                if index >= 0:
                    combo.setCurrentIndex(index)
        finally:
            combo.blockSignals(False)

    def _change_language(self, index: int) -> None:
        language = self._language_combo.itemData(index)
        if not isinstance(language, str):
            return
        if language == self._translator.language:
            return

        if self._preferences is not None:
            try:
                self._preferences.set_language(language)
            except Exception as exc:
                self._sync_preferences()
                self._show_preference_save_error(exc)
                return

        if not self._translator.set_language(language):
            self._sync_preferences()
            return
        self._preference_status.setText(
            self._translator.tr("settings.preferences_saved")
        )

    def _change_theme(self, index: int) -> None:
        theme = self._theme_combo.itemData(index)
        if not isinstance(theme, str):
            return
        if theme == self._theme_manager.theme:
            return

        if self._preferences is not None:
            try:
                self._preferences.set_theme(theme)
            except Exception as exc:
                self._sync_preferences()
                self._show_preference_save_error(exc)
                return

        if not self._theme_manager.set_theme(theme):
            self._sync_preferences()
            return
        self._preference_status.setText(
            self._translator.tr("settings.preferences_saved")
        )

    def _show_preference_save_error(self, error: Exception) -> None:
        QMessageBox.critical(
            self,
            self._translator.tr("settings.preference_save_failed_title"),
            self._translator.tr(
                "settings.preference_save_failed",
                error=str(error),
            ),
        )

    def _on_language_changed(self, _language: str) -> None:
        self.retranslate()
        self.reload()
        self._preference_status.clear()

    def _on_theme_changed(self, theme: str) -> None:
        self._select_combo_data(self._theme_combo, theme)

    def _change_backup_directory(self) -> None:
        if self._backup is None:
            return
        selected = QFileDialog.getExistingDirectory(
            self,
            self._translator.tr("settings.choose_backup_folder_title"),
            self._values["backup_directory"].text(),
        )
        if not selected:
            return
        try:
            directory = self._backup.set_backup_directory(selected)
        except Exception as exc:
            QMessageBox.critical(
                self,
                self._translator.tr("settings.backup_folder_title"),
                str(exc),
            )
            return
        self.reload()
        self._set_status(
            self._translator.tr(
                "settings.backup_folder_set",
                directory=directory,
            )
        )

    def _create_backup(self) -> None:
        if self._backup is None:
            return
        try:
            artifact = self._backup.create_backup()
        except Exception as exc:
            QMessageBox.critical(
                self,
                self._translator.tr("settings.backup_failed_title"),
                str(exc),
            )
            return
        self._set_status(
            self._translator.tr(
                "settings.backup_created",
                filename=artifact.filename,
                size=_format_bytes(artifact.size_bytes),
                path=artifact.path,
            )
        )

    def _restore_backup(self) -> None:
        if self._backup is None:
            return
        path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            self._translator.tr("settings.restore_backup_title"),
            self._values["backup_directory"].text(),
            self._translator.tr("settings.backup_filter"),
        )
        if not path:
            return

        try:
            validation = self._backup.validate_backup(path)
        except Exception as exc:
            QMessageBox.critical(
                self,
                self._translator.tr("settings.invalid_backup_title"),
                str(exc),
            )
            return
        if not validation.valid:
            QMessageBox.critical(
                self,
                self._translator.tr("settings.invalid_backup_title"),
                validation.message,
            )
            return

        answer = QMessageBox.question(
            self,
            self._translator.tr("settings.restore_backup_title"),
            self._translator.tr(
                "settings.restore_warning",
                path=validation.path,
                schema=validation.schema_revision,
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            result = self._backup.restore_backup(path)
        except Exception as exc:
            QMessageBox.critical(
                self,
                self._translator.tr("settings.restore_failed_title"),
                str(exc),
            )
            return

        self.reload()
        self._set_status(
            self._translator.tr(
                "settings.restore_completed",
                path=result.safety_backup.path,
            )
        )

    def _export_data(self) -> None:
        if self._exports is None:
            return
        dialog = ExportDialog(
            self._exports,
            default_directory=self._values["backup_directory"].text(),
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        result = dialog.export_result
        if result is None:
            return
        self._set_status(
            self._translator.tr(
                "settings.exported",
                rows=result.row_count,
                path=result.path,
                size=_format_bytes(result.size_bytes),
            )
        )

    def _set_status(self, message: str) -> None:
        self._data_status.setText(message)


def _format_bytes(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"
