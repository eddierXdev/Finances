"""Screens and temporary placeholders for the desktop shell."""

from __future__ import annotations

from collections.abc import Mapping

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from app.presentation.desktop.navigation import NavigationItem


class PlaceholderPage(QWidget):
    """Temporary content shown until a screen is implemented.

    Placeholders deliberately contain no business logic. Each will be replaced
    by a real screen that calls an application use case.
    """

    def __init__(self, item: NavigationItem, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName(f"page-{item.key}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 36, 40, 36)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title = QLabel(item.title, self)
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        description = QLabel(item.description, self)
        description.setObjectName("pageDescription")
        description.setWordWrap(True)
        layout.addWidget(description)

        separator = QFrame(self)
        separator.setObjectName("pageSeparator")
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Plain)
        separator.setFixedHeight(1)
        layout.addWidget(separator)

        badge = QLabel("Planned", self)
        badge.setObjectName("pageBadge")
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setFixedWidth(84)
        layout.addWidget(badge)

        note = QLabel(
            "This screen will be added in a later increment of Phase 12, "
            "once its use cases are wired into the application layer.",
            self,
        )
        note.setObjectName("pageNote")
        note.setWordWrap(True)
        layout.addWidget(note)

        layout.addStretch(1)


def build_pages(
    items: tuple[NavigationItem, ...],
    *,
    overrides: Mapping[str, QWidget] | None = None,
) -> dict[str, QWidget]:
    """Create the screen for every navigation item.

    Entries supplied in ``overrides`` replace their placeholder. This lets the
    shell grow one completed screen at a time without changing navigation.
    """
    overrides = overrides or {}
    return {
        item.key: (
            overrides[item.key]
            if item.key in overrides
            else PlaceholderPage(item)
        )
        for item in items
    }
