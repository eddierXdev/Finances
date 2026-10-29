"""Reusable read-only table model for list screens."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QColor

RowValues = Callable[[object], tuple[str, ...]]


class ReadOnlyTableModel(QAbstractTableModel):
    """Display application read models as a non-editable table."""

    def __init__(
        self,
        headers: Sequence[str],
        row_values: RowValues,
        *,
        right_columns: Sequence[int] = (),
        center_columns: Sequence[int] = (),
        muted: Callable[[object], bool] | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._headers = tuple(headers)
        self._row_values = row_values
        self._right_columns = frozenset(right_columns)
        self._center_columns = frozenset(center_columns)
        self._muted = muted
        self._rows: tuple[object, ...] = ()

    def set_rows(self, rows: Sequence[object]) -> None:
        self.beginResetModel()
        self._rows = tuple(rows)
        self.endResetModel()

    def set_headers(self, headers: Sequence[str]) -> None:
        """Replace column labels, for example after a language change."""
        self.beginResetModel()
        self._headers = tuple(headers)
        self.endResetModel()

    def rows(self) -> tuple[object, ...]:
        return self._rows

    def row_at(self, row: int) -> object | None:
        if 0 <= row < len(self._rows):
            return self._rows[row]
        return None

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._headers)

    def data(
        self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole
    ):
        if not index.isValid() or not 0 <= index.row() < len(self._rows):
            return None

        row = self._rows[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            values = self._row_values(row)
            if 0 <= index.column() < len(values):
                return values[index.column()]
            return ""

        if role == Qt.ItemDataRole.TextAlignmentRole:
            column = index.column()
            if column in self._right_columns:
                return int(
                    Qt.AlignmentFlag.AlignRight
                    | Qt.AlignmentFlag.AlignVCenter
                )
            if column in self._center_columns:
                return int(
                    Qt.AlignmentFlag.AlignCenter
                    | Qt.AlignmentFlag.AlignVCenter
                )
            return int(
                Qt.AlignmentFlag.AlignLeft
                | Qt.AlignmentFlag.AlignVCenter
            )

        if (
            role == Qt.ItemDataRole.ForegroundRole
            and self._muted is not None
            and self._muted(row)
        ):
            return QColor("#9ca3af")

        return None

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ):
        if (
            orientation == Qt.Orientation.Horizontal
            and role == Qt.ItemDataRole.DisplayRole
            and 0 <= section < len(self._headers)
        ):
            return self._headers[section]
        return None
