"""Compact KPI card with a value and a supporting hint."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


class StatCard(QFrame):
    """A semantic metric card styled through object names and properties."""

    def __init__(
        self,
        title: str = "",
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("metricCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumWidth(170)
        self.setProperty("tone", "neutral")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        self.title_label = QLabel(title, self)
        self.title_label.setObjectName("metricTitle")
        layout.addWidget(self.title_label)

        self.value_label = QLabel("—", self)
        self.value_label.setObjectName("metricValue")
        self.value_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addWidget(self.value_label)

        self.hint_label = QLabel("", self)
        self.hint_label.setObjectName("metricHint")
        self.hint_label.setWordWrap(True)
        layout.addWidget(self.hint_label)

    def set_title(self, title: str) -> None:
        self.title_label.setText(title)
        self.setAccessibleName(title)

    def set_value(
        self,
        value: str,
        hint: str = "",
        *,
        negative: bool = False,
        tone: str | None = None,
    ) -> None:
        self.value_label.setText(value)
        self.value_label.setProperty("negative", negative)
        self.hint_label.setText(hint)
        selected_tone = tone or ("negative" if negative else "neutral")
        self.setProperty("tone", selected_tone)
        self._refresh_style(self.value_label)
        self._refresh_style(self)

    @staticmethod
    def _refresh_style(widget: QWidget) -> None:
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()
