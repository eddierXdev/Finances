"""Standard page header used by redesigned screens."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)


class PageHeader(QWidget):
    """Title, optional context line and right-aligned page actions."""

    def __init__(
        self,
        *,
        title: str = "",
        description: str = "",
        eyebrow: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("pageHeader")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        titles = QVBoxLayout()
        titles.setContentsMargins(0, 0, 0, 0)
        titles.setSpacing(4)

        self.eyebrow_label = QLabel(eyebrow, self)
        self.eyebrow_label.setObjectName("pageEyebrow")
        self.eyebrow_label.setVisible(bool(eyebrow))
        titles.addWidget(self.eyebrow_label)

        self.title_label = QLabel(title, self)
        self.title_label.setObjectName("pageTitle")
        titles.addWidget(self.title_label)

        self.description_label = QLabel(description, self)
        self.description_label.setObjectName("pageDescription")
        self.description_label.setWordWrap(True)
        titles.addWidget(self.description_label)
        layout.addLayout(titles, 1)

        self._actions = QHBoxLayout()
        self._actions.setContentsMargins(0, 0, 0, 0)
        self._actions.setSpacing(8)
        layout.addLayout(self._actions)

    def add_action(
        self,
        widget: QWidget,
        *,
        alignment: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignTop,
    ) -> None:
        self._actions.addWidget(widget, 0, alignment)

    def set_title(self, title: str) -> None:
        self.title_label.setText(title)

    def set_description(self, description: str) -> None:
        self.description_label.setText(description)

    def set_eyebrow(self, eyebrow: str) -> None:
        self.eyebrow_label.setText(eyebrow)
        self.eyebrow_label.setVisible(bool(eyebrow))
