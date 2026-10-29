"""Currency Rates screen with latest observations and history."""

from __future__ import annotations

from datetime import timedelta

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from app.application.exchange_rates.service import (
    ExchangeRateRow,
    ExchangeRateService,
)
from app.presentation.desktop.dialogs.exchange_rates import ManualRateDialog
from app.presentation.desktop.form_utils import display_datetime
from app.presentation.desktop.labels import exchange_rate_source_label
from app.presentation.desktop.table_model import ReadOnlyTableModel


class CurrencyRatesPage(QWidget):
    """Inspect stored rates and add manual observations."""

    def __init__(
        self,
        rates: ExchangeRateService,
        *,
        base_currency: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._rates = rates
        self._base_currency = base_currency
        self._rows: tuple[ExchangeRateRow, ...] = ()
        self.setObjectName("currencyRatesPage")
        self._build_ui()
        self.reload()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 24)
        layout.setSpacing(14)

        title = QLabel("Currency Rates", self)
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        description = QLabel(
            "Historical exchange-rate observations. Analytics converts "
            "native balances and results into the configured base currency.",
            self,
        )
        description.setObjectName("pageDescription")
        description.setWordWrap(True)
        layout.addWidget(description)

        toolbar = QHBoxLayout()
        refresh = QPushButton("Refresh", self)
        refresh.setObjectName("refreshRatesButton")
        refresh.clicked.connect(self.reload)
        toolbar.addWidget(refresh)
        toolbar.addStretch(1)

        self._add_button = QPushButton("Add manual rate", self)
        self._add_button.setObjectName("addManualRateButton")
        self._add_button.setProperty("variant", "primary")
        self._add_button.clicked.connect(self._add_rate)
        toolbar.addWidget(self._add_button)
        layout.addLayout(toolbar)

        self._error_banner = QLabel(self)
        self._error_banner.setObjectName("errorBanner")
        self._error_banner.setWordWrap(True)
        self._error_banner.hide()
        layout.addWidget(self._error_banner)

        self._latest_model = ReadOnlyTableModel(
            (
                "Base",
                "Quote",
                "Rate",
                "Source",
                "Observed",
                "Age",
                "Status",
            ),
            self._latest_values,
            right_columns=(2, 5),
            center_columns=(0, 1, 3, 6),
            muted=lambda row: row.is_stale,
            parent=self,
        )
        self._history_model = ReadOnlyTableModel(
            ("Observed", "Rate", "Source", "Notes"),
            self._history_values,
            right_columns=(1,),
            center_columns=(2,),
            parent=self,
        )

        self._latest_table = _table(
            self, "latestRatesTable", self._latest_model, 5
        )
        self._latest_table.selectionModel().selectionChanged.connect(
            self._load_history
        )
        self._history_table = _table(
            self, "rateHistoryTable", self._history_model, 3
        )

        self._latest_empty = QLabel(
            "No exchange rates stored yet. Add a manual rate to enable "
            "base-currency analytics.",
            self,
        )
        self._latest_empty.setObjectName("emptyStateHint")
        self._latest_empty.setWordWrap(True)
        self._latest_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._latest_stack = QStackedWidget(self)
        self._latest_stack.setObjectName("latestRatesContent")
        self._latest_stack.addWidget(self._latest_table)
        self._latest_stack.addWidget(self._latest_empty)

        latest_group = QWidget(self)
        latest_layout = QVBoxLayout(latest_group)
        latest_layout.setContentsMargins(0, 0, 0, 0)
        latest_layout.setSpacing(6)
        latest_title = QLabel("Latest rates", latest_group)
        latest_title.setObjectName("sectionTitle")
        latest_layout.addWidget(latest_title)
        latest_layout.addWidget(self._latest_stack, 1)

        self._history_title = QLabel("History", self)
        self._history_title.setObjectName("sectionTitle")
        history_group = QWidget(self)
        history_layout = QVBoxLayout(history_group)
        history_layout.setContentsMargins(0, 0, 0, 0)
        history_layout.setSpacing(6)
        history_layout.addWidget(self._history_title)
        history_layout.addWidget(self._history_table, 1)

        splitter = QSplitter(Qt.Orientation.Vertical, self)
        splitter.setObjectName("ratesSplitter")
        splitter.addWidget(latest_group)
        splitter.addWidget(history_group)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter, 1)

        self._footer = QLabel(self)
        self._footer.setObjectName("ratesFooter")
        layout.addWidget(self._footer)

    @staticmethod
    def _latest_values(row: ExchangeRateRow) -> tuple[str, ...]:
        return (
            row.base_code,
            row.quote_code,
            row.rate,
            exchange_rate_source_label(row.source),
            display_datetime(row.rate_timestamp),
            _format_age(row.age),
            "Stale" if row.is_stale else "Fresh",
        )

    @staticmethod
    def _history_values(row: ExchangeRateRow) -> tuple[str, ...]:
        return (
            display_datetime(row.rate_timestamp),
            row.rate,
            exchange_rate_source_label(row.source),
            row.notes or "—",
        )

    def reload(self, *_args) -> None:
        try:
            rows = self._rates.list_latest_rates()
        except Exception as exc:
            self._show_error(f"Could not load exchange rates: {exc}")
            return
        self._show_error(None)
        self._rows = tuple(rows)
        self._latest_model.set_rows(self._rows)
        self._latest_stack.setCurrentWidget(
            self._latest_table if self._rows else self._latest_empty
        )
        stale = sum(1 for row in self._rows if row.is_stale)
        self._footer.setText(
            f"{len(self._rows)} currency pairs · "
            f"{stale} stale · base currency {self._base_currency}"
            if self._rows
            else "No stored exchange rates"
        )
        self._history_model.set_rows(())
        self._history_title.setText("History")
        if self._rows:
            self._latest_table.selectRow(0)
            self._load_history()
        else:
            self._history_title.setText(
                "History · select a currency pair"
            )

    def _show_error(self, message: str | None) -> None:
        if message is None:
            self._error_banner.clear()
            self._error_banner.hide()
            return
        self._error_banner.setText(message)
        self._error_banner.show()

    def _load_history(self, *_args) -> None:
        indexes = self._latest_table.selectionModel().selectedRows()
        if not indexes:
            return
        value = self._latest_model.row_at(indexes[0].row())
        if not isinstance(value, ExchangeRateRow):
            return
        try:
            history = self._rates.list_history(
                value.base_code, value.quote_code
            )
        except Exception as exc:
            self._show_error(f"Could not load rate history: {exc}")
            return
        self._show_error(None)
        self._history_model.set_rows(history)
        self._history_title.setText(
            f"History · {value.base_code}/{value.quote_code} · "
            f"{len(history)} observations"
        )

    def _add_rate(self) -> None:
        try:
            currencies = self._rates.list_currencies()
        except Exception as exc:
            QMessageBox.critical(
                self, "Could not load currencies", str(exc)
            )
            return
        if len(currencies) < 2:
            QMessageBox.information(
                self,
                "Not enough currencies",
                "At least two enabled currencies are required.",
            )
            return
        try:
            dialog = ManualRateDialog(
                self._rates,
                currencies=currencies,
                base_currency=self._base_currency,
                parent=self,
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Cannot add rate", str(exc))
            return
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.reload()


def _table(
    parent: QWidget,
    object_name: str,
    model: ReadOnlyTableModel,
    stretch_column: int,
) -> QTableView:
    table = QTableView(parent)
    table.setObjectName(object_name)
    table.setModel(model)
    table.setAlternatingRowColors(True)
    table.setSelectionBehavior(
        QAbstractItemView.SelectionBehavior.SelectRows
    )
    table.setSelectionMode(
        QAbstractItemView.SelectionMode.SingleSelection
    )
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.verticalHeader().setVisible(False)
    table.horizontalHeader().setSectionResizeMode(
        stretch_column, QHeaderView.ResizeMode.Stretch
    )
    for column in range(model.columnCount()):
        if column != stretch_column:
            table.horizontalHeader().setSectionResizeMode(
                column, QHeaderView.ResizeMode.ResizeToContents
            )
    return table


def _format_age(age: timedelta) -> str:
    seconds = int(age.total_seconds())
    if seconds < 60:
        return "just now"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 48:
        return f"{hours}h ago"
    days = hours // 24
    return f"{days}d ago"
