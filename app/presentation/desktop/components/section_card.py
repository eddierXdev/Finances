"""Surface container for a titled dashboard section."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)


class SectionCard(QFrame):
    """A bordered surface with a section header and content slot."""

    def __init__(
        self,
        title: str = "",
        description: str = "",
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("sectionCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(12)

        titles = QVBoxLayout()
        titles.setContentsMargins(0, 0, 0, 0)
        titles.setSpacing(2)

        self.title_label = QLabel(title, self)
        self.title_label.setObjectName("sectionTitle")
        titles.addWidget(self.title_label)

        self.description_label = QLabel(description, self)
        self.description_label.setObjectName("sectionDescription")
        self.description_label.setWordWrap(True)
        self.description_label.setVisible(bool(description))
        titles.addWidget(self.description_label)
        header.addLayout(titles, 1)

        self._actions = QHBoxLayout()
        self._actions.setContentsMargins(0, 0, 0, 0)
        self._actions.setSpacing(8)
        header.addLayout(self._actions)
        layout.addLayout(header)

        self._content = QVBoxLayout()
        self._content.setContentsMargins(0, 0, 0, 0)
        self._content.setSpacing(10)
        layout.addLayout(self._content, 1)

    def add_content(self, widget: QWidget, *, stretch: int = 1) -> None:
        self._content.addWidget(widget, stretch)

    def add_layout(self, layout, *, stretch: int = 1) -> None:
        self._content.addLayout(layout, stretch)

    def add_action(self, widget: QWidget) -> None:
        self._actions.addWidget(widget)

    def set_title(self, title: str) -> None:
        self.title_label.setText(title)

    def set_description(self, description: str) -> None:
        self.description_label.setText(description)
        self.description_label.setVisible(bool(description))
