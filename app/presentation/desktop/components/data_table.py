"""Read-only table wrapper with a built-in empty state."""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QStackedLayout,
    QTableView,
    QWidget,
)

from app.presentation.desktop.components.empty_state import EmptyState
from app.presentation.desktop.table_model import ReadOnlyTableModel


class DataTable(QWidget):
    """A configured table that switches to an empty state when necessary."""

    def __init__(
        self,
        object_name: str,
        model: ReadOnlyTableModel,
        *,
        stretch_column: int = 0,
        empty_title: str = "",
        empty_hint: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._stack = QStackedLayout(self)
        self._stack.setContentsMargins(0, 0, 0, 0)

        self.table = QTableView(self)
        self.table.setObjectName(object_name)
        self.table.setModel(model)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setHighlightSections(False)
        self.table.horizontalHeader().setSectionResizeMode(
            stretch_column, QHeaderView.ResizeMode.Stretch
        )
        for column in range(model.columnCount()):
            if column != stretch_column:
                self.table.horizontalHeader().setSectionResizeMode(
                    column, QHeaderView.ResizeMode.ResizeToContents
                )
        self.table.setMinimumHeight(180)
        self._stretch_column = stretch_column

        self.empty_state = EmptyState(
            empty_title,
            empty_hint,
            parent=self,
        )
        self._stack.addWidget(self.table)
        self._stack.addWidget(self.empty_state)
        self._stack.setCurrentWidget(self.empty_state)

    def set_rows(self, rows: Sequence[object]) -> None:
        model = self.table.model()
        if isinstance(model, ReadOnlyTableModel):
            model.set_rows(rows)
        self._apply_size_modes()
        self._stack.setCurrentWidget(
            self.table if rows else self.empty_state
        )

    def set_headers(self, headers: Sequence[str]) -> None:
        model = self.table.model()
        if isinstance(model, ReadOnlyTableModel):
            model.set_headers(headers)
        self._apply_size_modes()

    def _apply_size_modes(self) -> None:
        model = self.table.model()
        if model is None:
            return
        header = self.table.horizontalHeader()
        for column in range(model.columnCount()):
            header.setSectionResizeMode(
                column,
                (
                    QHeaderView.ResizeMode.Stretch
                    if column == self._stretch_column
                    else QHeaderView.ResizeMode.ResizeToContents
                ),
            )

    def set_empty_state(self, title: str, hint: str = "") -> None:
        self.empty_state.set_text(title, hint)

    def set_accessible_name(self, name: str, description: str = "") -> None:
        self.table.setAccessibleName(name)
        self.table.setAccessibleDescription(description)
        self.empty_state.setAccessibleName(name)
        if description:
            self.empty_state.setAccessibleDescription(description)

    def selected_row(self) -> int:
        selection = self.table.selectionModel()
        if selection is None:
            return -1
        rows = selection.selectedRows()
        return rows[0].row() if rows else -1
