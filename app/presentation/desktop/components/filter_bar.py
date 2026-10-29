"""Reusable filter row and the Dashboard period selector."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from PySide6.QtCore import QDate, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)

from app.application.analytics.models import AnalyticsPeriod
from app.presentation.desktop.form_utils import date_to_datetime
from app.presentation.desktop.i18n.translator import Translator


class FilterBar(QFrame):
    """A low-emphasis horizontal container for screen filters."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("filterBar")
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(8)

    def add_widget(self, widget: QWidget) -> None:
        self.layout.addWidget(widget)

    def add_stretch(self) -> None:
        self.layout.addStretch(1)


class PeriodFilter(QWidget):
    """Preset date ranges with an optional custom inclusive range."""

    period_changed = Signal(object)

    def __init__(
        self,
        translator: Translator,
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._translator = translator
        self._presets = (
            ("all", "dashboard.filter.all_time"),
            ("30d", "dashboard.filter.last_30"),
            ("90d", "dashboard.filter.last_90"),
            ("year", "dashboard.filter.this_year"),
            ("custom", "dashboard.filter.custom"),
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.label = QLabel(self)
        self.label.setObjectName("filterLabel")
        layout.addWidget(self.label)

        self.combo = QComboBox(self)
        self.combo.setObjectName("periodFilterCombo")
        self.combo.setMinimumWidth(150)
        for key, _ in self._presets:
            self.combo.addItem("", key)
        layout.addWidget(self.combo)

        self.from_label = QLabel(self)
        self.from_label.setObjectName("filterLabel")
        layout.addWidget(self.from_label)

        self.start_date = QDateEdit(
            QDate.currentDate().addDays(-30), self
        )
        self.start_date.setObjectName("periodFilterStart")
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat("yyyy-MM-dd")
        layout.addWidget(self.start_date)

        self.to_label = QLabel(self)
        self.to_label.setObjectName("filterLabel")
        layout.addWidget(self.to_label)

        self.end_date = QDateEdit(QDate.currentDate(), self)
        self.end_date.setObjectName("periodFilterEnd")
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat("yyyy-MM-dd")
        layout.addWidget(self.end_date)

        self.apply_button = QPushButton(self)
        self.apply_button.setObjectName("periodFilterApply")
        self.apply_button.clicked.connect(self._apply_custom)
        layout.addWidget(self.apply_button)

        self._custom_widgets = (
            self.from_label,
            self.start_date,
            self.to_label,
            self.end_date,
            self.apply_button,
        )
        for widget in self._custom_widgets:
            widget.hide()

        self.combo.currentIndexChanged.connect(self._on_preset_changed)
        self._translator.language_changed.connect(self.retranslate)
        self.retranslate()

    @property
    def preset(self) -> str:
        data = self.combo.currentData()
        return data if isinstance(data, str) else "all"

    def current_period(self) -> AnalyticsPeriod:
        """Return the currently selected period as an application value."""
        preset = self.preset
        now = datetime.now(UTC)
        if preset == "all":
            return AnalyticsPeriod()
        if preset == "30d":
            return AnalyticsPeriod(now - timedelta(days=30), now)
        if preset == "90d":
            return AnalyticsPeriod(now - timedelta(days=90), now)
        if preset == "year":
            return AnalyticsPeriod(
                datetime(now.year, 1, 1, tzinfo=UTC),
                now,
            )

        start = date_to_datetime(self.start_date.date())
        end = (
            date_to_datetime(self.end_date.date())
            + timedelta(days=1)
            - timedelta(seconds=1)
        )
        if end < start:
            end = start + timedelta(days=1) - timedelta(seconds=1)
        return AnalyticsPeriod(start, end)

    def _on_preset_changed(self, _index: int) -> None:
        custom = self.preset == "custom"
        for widget in self._custom_widgets:
            widget.setVisible(custom)
        if not custom:
            self.period_changed.emit(self.current_period())

    def _apply_custom(self) -> None:
        if self.end_date.date() < self.start_date.date():
            self.end_date.setDate(self.start_date.date())
        self.period_changed.emit(self.current_period())

    def retranslate(self, *_args) -> None:
        t = self._translator.tr
        self.label.setText(t("dashboard.filter.period"))
        for index, (_key, translation_key) in enumerate(self._presets):
            self.combo.setItemText(index, t(translation_key))
        self.from_label.setText(t("dashboard.filter.from"))
        self.to_label.setText(t("dashboard.filter.to"))
        self.apply_button.setText(t("dashboard.filter.apply"))
        self.combo.setAccessibleName(t("dashboard.filter.accessible"))
        self.combo.setAccessibleDescription(t("dashboard.filter.help"))
        self.start_date.setAccessibleName(t("dashboard.filter.from"))
        self.end_date.setAccessibleName(t("dashboard.filter.to"))
        self.apply_button.setAccessibleName(t("dashboard.filter.apply"))
        self.combo.setToolTip(t("dashboard.filter.help"))
