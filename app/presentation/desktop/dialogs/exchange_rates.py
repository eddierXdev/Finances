"""Manual exchange-rate dialog."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC

from PySide6.QtCore import QDateTime
from PySide6.QtWidgets import (
    QComboBox,
    QDateTimeEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.application.exchange_rates.service import ExchangeRateService
from app.application.exchange_rates.set_manual_exchange_rate import (
    SetManualExchangeRateRequest,
)
from app.domain.entities.currency import Currency
from app.presentation.desktop.form_utils import parse_optional_decimal


class ManualRateDialog(QDialog):
    """Store one immutable manual exchange-rate observation."""

    def __init__(
        self,
        rates: ExchangeRateService,
        *,
        currencies: Sequence[Currency],
        base_currency: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        if len(currencies) < 2:
            raise ValueError(
                "At least two enabled currencies are required."
            )
        self._rates = rates
        self._currencies = tuple(currencies)
        self.created_result = None
        self.setWindowTitle("Manual exchange rate")
        self.setModal(True)
        self.resize(500, 440)
        self._build_ui(base_currency)

    def _build_ui(self, base_currency: str) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel("Manual exchange rate", self)
        title.setObjectName("dialogTitle")
        layout.addWidget(title)

        form = QFormLayout()
        self._base = QComboBox(self)
        self._base.setObjectName("manualRateBase")
        self._quote = QComboBox(self)
        self._quote.setObjectName("manualRateQuote")
        for currency in self._currencies:
            label = f"{currency.code} — {currency.name}"
            self._base.addItem(label, currency)
            self._quote.addItem(label, currency)

        base_index = next(
            (
                index
                for index, currency in enumerate(self._currencies)
                if currency.code == base_currency
            ),
            0,
        )
        self._base.setCurrentIndex(base_index)
        self._quote.setCurrentIndex(
            0 if base_index != 0 else 1
        )
        self._base.currentIndexChanged.connect(self._ensure_distinct)
        self._quote.currentIndexChanged.connect(self._ensure_distinct)
        form.addRow("Base currency *", self._base)
        form.addRow("Quote currency *", self._quote)

        self._rate = QLineEdit(self)
        self._rate.setObjectName("manualRateValue")
        self._rate.setPlaceholderText("Example: 0.0025")
        form.addRow("Rate *", self._rate)

        self._timestamp = QDateTimeEdit(
            QDateTime.currentDateTime(), self
        )
        self._timestamp.setObjectName("manualRateTimestamp")
        self._timestamp.setCalendarPopup(True)
        self._timestamp.setDisplayFormat("yyyy-MM-dd HH:mm")
        form.addRow("Observed at *", self._timestamp)

        self._notes = QPlainTextEdit(self)
        self._notes.setObjectName("manualRateNotes")
        self._notes.setPlaceholderText("Optional notes")
        self._notes.setFixedHeight(60)
        form.addRow("Notes", self._notes)
        layout.addLayout(form)

        hint = QLabel(
            "Rates are historical observations. A new value never "
            "overwrites an older one.",
            self,
        )
        hint.setObjectName("fieldHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        layout.addStretch(1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel, self
        )
        save = QPushButton("Save rate", self)
        save.setObjectName("saveManualRateButton")
        save.setProperty("variant", "primary")
        save.setDefault(True)
        buttons.addButton(save, QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.rejected.connect(self.reject)
        save.clicked.connect(self._submit)
        layout.addWidget(buttons)

    def _ensure_distinct(self, *_args) -> None:
        base = self._base.currentData()
        quote = self._quote.currentData()
        if not isinstance(base, Currency) or not isinstance(
            quote, Currency
        ):
            return
        if base.code != quote.code:
            return
        for index in range(self._quote.count()):
            candidate = self._quote.itemData(index)
            if isinstance(candidate, Currency) and candidate.code != base.code:
                self._quote.setCurrentIndex(index)
                return

    def _submit(self) -> None:
        base = self._base.currentData()
        quote = self._quote.currentData()
        if not isinstance(base, Currency) or not isinstance(
            quote, Currency
        ):
            return
        if base.code == quote.code:
            QMessageBox.warning(
                self,
                "Invalid rate",
                "Base and quote currencies must differ.",
            )
            return
        try:
            rate = parse_optional_decimal(
                self._rate.text(), "Rate"
            )
            if rate is None:
                raise ValueError("Rate is required.")
            timestamp = self._timestamp.dateTime().toPython()
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=UTC)
            else:
                timestamp = timestamp.astimezone(UTC)
            self.created_result = self._rates.set_manual(
                SetManualExchangeRateRequest(
                    base_code=base.code,
                    quote_code=quote.code,
                    rate=rate,
                    rate_timestamp=timestamp,
                    notes=self._notes.toPlainText().strip() or None,
                )
            )
        except Exception as exc:
            QMessageBox.critical(
                self, "Could not save rate", str(exc)
            )
            return
        self.accept()
