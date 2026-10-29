"""Application sidebar with brand, navigation and local-data status."""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.presentation.desktop.components.status_badge import StatusBadge
from app.presentation.desktop.i18n.translator import Translator
from app.presentation.desktop.navigation import NavigationItem


class Sidebar(QFrame):
    """The main navigation rail.

    Navigation remains a plain ``QListWidget`` so screen selection and keyboard
    behavior stay exactly as before.
    """

    def __init__(
        self,
        items: Sequence[NavigationItem],
        *,
        app_name: str,
        base_currency: str | None = None,
        translator: Translator | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._items = tuple(items)
        self._app_name = app_name
        self._base_currency = base_currency
        self._translator = translator or Translator()

        self.setObjectName("sidebar")
        self.setFixedWidth(248)
        self.setAccessibleName(self._app_name)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        brand_row = QWidget(self)
        brand_row.setObjectName("sidebarBrandRow")
        brand_layout = QHBoxLayout(brand_row)
        brand_layout.setContentsMargins(18, 20, 18, 10)
        brand_layout.setSpacing(10)

        self.brand_mark = QLabel(self._initials(app_name), brand_row)
        self.brand_mark.setObjectName("brandMark")
        self.brand_mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.brand_mark.setFixedSize(34, 34)
        brand_layout.addWidget(self.brand_mark)

        titles = QVBoxLayout()
        titles.setContentsMargins(0, 0, 0, 0)
        titles.setSpacing(1)
        self.brand = QLabel(app_name, brand_row)
        self.brand.setObjectName("brand")
        titles.addWidget(self.brand)
        self.brand_subtitle = QLabel(brand_row)
        self.brand_subtitle.setObjectName("brandSubtitle")
        titles.addWidget(self.brand_subtitle)
        brand_layout.addLayout(titles, 1)
        layout.addWidget(brand_row)

        self.section_label = QLabel(self)
        self.section_label.setObjectName("sidebarSectionLabel")
        self.section_label.setContentsMargins(20, 10, 20, 4)
        layout.addWidget(self.section_label)

        self.navigation = QListWidget(self)
        self.navigation.setObjectName("navigation")
        self.navigation.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.navigation.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.navigation.setSpacing(0)
        for item in self._items:
            row = QListWidgetItem()
            row.setData(Qt.ItemDataRole.UserRole, item.key)
            self.navigation.addItem(row)
        layout.addWidget(self.navigation, 1)

        footer = QWidget(self)
        footer.setObjectName("sidebarFooter")
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(18, 10, 18, 16)
        footer_layout.setSpacing(8)

        divider = QFrame(footer)
        divider.setObjectName("sidebarDivider")
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFrameShadow(QFrame.Shadow.Plain)
        divider.setFixedHeight(1)
        footer_layout.addWidget(divider)

        self.status_badge = StatusBadge(tone="success", parent=footer)
        self.status_badge.setObjectName("statusBadge")
        footer_layout.addWidget(
            self.status_badge,
            0,
            Qt.AlignmentFlag.AlignLeft,
        )

        self.currency_label = QLabel(footer)
        self.currency_label.setObjectName("sidebarCurrencyLabel")
        footer_layout.addWidget(self.currency_label)
        layout.addWidget(footer)

        self._translator.language_changed.connect(self.retranslate)
        self.retranslate()

    def retranslate(self, *_args) -> None:
        t = self._translator.tr
        self.brand_subtitle.setText(t("app.brand_subtitle"))
        self.section_label.setText(t("app.sidebar.section"))
        self.navigation.setAccessibleName(t("app.sidebar.navigation"))
        self.navigation.setAccessibleDescription(
            t("app.sidebar.navigation_help")
        )
        self.status_badge.setText(t("app.status.offline"))
        if self._base_currency:
            self.currency_label.setText(
                t(
                    "app.sidebar.base_currency",
                    currency=self._base_currency,
                )
            )
        else:
            self.currency_label.clear()
        for row, item in enumerate(self._items):
            nav_item = self.navigation.item(row)
            nav_item.setText(
                t(
                    f"navigation.{item.key}.title",
                    default=item.title,
                )
            )
            nav_item.setToolTip(
                t(
                    f"navigation.{item.key}.description",
                    default=item.description,
                )
            )

    @staticmethod
    def _initials(app_name: str) -> str:
        words = [word for word in app_name.split() if word]
        if not words:
            return "RM"
        return "".join(word[0].upper() for word in words[:2])
