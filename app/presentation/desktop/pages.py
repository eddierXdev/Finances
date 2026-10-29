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

from app.presentation.desktop.i18n.translator import Translator
from app.presentation.desktop.navigation import NavigationItem


class PlaceholderPage(QWidget):
    """Temporary content shown until a screen is implemented.

    Placeholders deliberately contain no business logic. Each will be replaced
    by a real screen that calls an application use case.
    """

    def __init__(
        self,
        item: NavigationItem,
        *,
        translator: Translator | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._item = item
        self._translator = translator or Translator()
        self.setObjectName(f"page-{item.key}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 36, 40, 36)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._title = QLabel(self)
        self._title.setObjectName("pageTitle")
        layout.addWidget(self._title)

        self._description = QLabel(self)
        self._description.setObjectName("pageDescription")
        self._description.setWordWrap(True)
        layout.addWidget(self._description)

        separator = QFrame(self)
        separator.setObjectName("pageSeparator")
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Plain)
        separator.setFixedHeight(1)
        layout.addWidget(separator)

        self._badge = QLabel(self)
        self._badge.setObjectName("pageBadge")
        self._badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._badge.setFixedWidth(84)
        layout.addWidget(self._badge)

        self._note = QLabel(self)
        self._note.setObjectName("pageNote")
        self._note.setWordWrap(True)
        layout.addWidget(self._note)

        layout.addStretch(1)
        self._translator.language_changed.connect(self.retranslate)
        self.retranslate()

    def retranslate(self, *_args) -> None:
        """Refresh static placeholder text after a language change."""
        t = self._translator.tr
        self._title.setText(
            t(
                f"navigation.{self._item.key}.title",
                default=self._item.title,
            )
        )
        self._description.setText(
            t(
                f"navigation.{self._item.key}.description",
                default=self._item.description,
            )
        )
        self._badge.setText(t("placeholder.badge"))
        self._note.setText(t("placeholder.note"))


def build_pages(
    items: tuple[NavigationItem, ...],
    *,
    overrides: Mapping[str, QWidget] | None = None,
    translator: Translator | None = None,
) -> dict[str, QWidget]:
    """Create the screen for every navigation item.

    Entries supplied in ``overrides`` replace their placeholder. This lets the
    shell grow one completed screen at a time without changing navigation.
    """
    overrides = overrides or {}
    translator = translator or Translator()
    return {
        item.key: (
            overrides[item.key]
            if item.key in overrides
            else PlaceholderPage(item, translator=translator)
        )
        for item in items
    }
