"""Reusable native QPainter chart widget.

The widget only consumes prepared, presentation-ready points. It never reads
persistence and never performs financial calculations.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from PySide6.QtCore import QDate, QLocale, QPointF, QRectF, QSize, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetricsF,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import QSizePolicy, QWidget

from app.presentation.desktop.themes.chart_palette import (
    ChartPalette,
    chart_palette,
)


@dataclass(frozen=True, slots=True)
class ChartDatum:
    """One prepared chart point or category."""

    label: str
    value: float
    tone: str = "accent"
    tooltip: str = ""


class ChartWidget(QWidget):
    """Paint line, vertical bar or horizontal bar charts."""

    def __init__(
        self,
        kind: str = "line",
        *,
        value_kind: str = "money",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        if kind not in {"line", "bar", "hbar"}:
            raise ValueError(f"Unsupported chart kind: {kind}")
        if value_kind not in {"money", "quantity"}:
            raise ValueError(f"Unsupported value kind: {value_kind}")

        self._kind = kind
        self._value_kind = value_kind
        self._points: tuple[ChartDatum, ...] = ()
        self._palette: ChartPalette = chart_palette("light")
        self._currency_code = "USD"
        self._language = "en"
        self._locale = chart_locale(self._language)
        self._empty_text = ""
        self._empty_hint = ""

        self.setObjectName("chartWidget")
        self.setMinimumHeight(230)
        self.setMinimumWidth(200)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self.setMouseTracking(True)

    @property
    def chart_palette(self) -> ChartPalette:
        """Return the palette currently used by the renderer."""
        return self._palette

    def set_points(self, points: Sequence[ChartDatum]) -> None:
        self._points = tuple(points)
        self._update_tooltip()
        self.update()

    def set_palette(self, palette: ChartPalette) -> None:
        self._palette = palette
        self.update()

    def set_language(self, language: str) -> None:
        self._language = language
        self._locale = chart_locale(language)
        self._update_tooltip()
        self.update()

    def set_currency(self, currency_code: str) -> None:
        self._currency_code = currency_code
        self._update_tooltip()
        self.update()

    def set_empty_text(self, text: str, hint: str = "") -> None:
        self._empty_text = text
        self._empty_hint = hint
        self._update_tooltip()
        self.update()

    def sizeHint(self) -> QSize:
        return QSize(520, 280)

    def minimumSizeHint(self) -> QSize:
        return QSize(260, 210)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        if not self._points:
            self._paint_empty(painter)
            return

        if self._kind == "line":
            self._paint_line(painter)
        elif self._kind == "bar":
            self._paint_bars(painter)
        else:
            self._paint_horizontal_bars(painter)

    def _paint_empty(self, painter: QPainter) -> None:
        rect = QRectF(self.rect()).adjusted(20, 20, -20, -20)
        icon_font = QFont(self.font())
        icon_font.setPointSizeF(max(16.0, self.font().pointSizeF() + 6))
        painter.setFont(icon_font)
        painter.setPen(QColor(self._palette.muted_text))
        icon_rect = QRectF(
            rect.left(),
            rect.center().y() - 42,
            rect.width(),
            28,
        )
        painter.drawText(
            icon_rect,
            Qt.AlignmentFlag.AlignCenter,
            "◇",
        )

        title_font = QFont(self.font())
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.setPen(QColor(self._palette.text))
        title_rect = QRectF(
            rect.left(),
            rect.center().y() - 8,
            rect.width(),
            24,
        )
        painter.drawText(
            title_rect,
            Qt.AlignmentFlag.AlignCenter,
            self._empty_text,
        )

        hint_font = QFont(self.font())
        hint_font.setPointSizeF(max(7.5, self.font().pointSizeF() - 1))
        painter.setFont(hint_font)
        painter.setPen(QColor(self._palette.muted_text))
        hint_rect = QRectF(
            rect.left(),
            rect.center().y() + 20,
            rect.width(),
            44,
        )
        painter.drawText(
            hint_rect,
            Qt.AlignmentFlag.AlignHCenter
            | Qt.AlignmentFlag.AlignTop
            | Qt.TextFlag.TextWordWrap,
            self._empty_hint,
        )

    def _plot_rect(self) -> QRectF:
        rect = QRectF(self.rect()).adjusted(8, 8, -8, -8)
        axis_font = self._axis_font()
        metrics = QFontMetricsF(axis_font)
        labels = [
            self._format_value(value, compact=True)
            for value in self._axis_values()
        ]
        left_margin = max(
            48.0,
            max((metrics.horizontalAdvance(label) for label in labels), default=0)
            + 12.0,
        )
        bottom_margin = 34.0
        return QRectF(
            rect.left() + left_margin,
            rect.top() + 8,
            max(10.0, rect.width() - left_margin - 12.0),
            max(10.0, rect.height() - bottom_margin - 8.0),
        )

    def _paint_line(self, painter: QPainter) -> None:
        plot = self._plot_rect()
        values = [point.value for point in self._points]
        minimum, maximum = self._axis_bounds(values)
        zero_y = self._map_y(0.0, minimum, maximum, plot)
        self._paint_grid(painter, plot, minimum, maximum)

        count = len(self._points)
        if count == 1:
            xs = [plot.center().x()]
        else:
            xs = [
                plot.left() + index / (count - 1) * plot.width()
                for index in range(count)
            ]
        ys = [
            self._map_y(point.value, minimum, maximum, plot)
            for point in self._points
        ]

        area = QPainterPath()
        area.moveTo(QPointF(xs[0], zero_y))
        for x, y in zip(xs, ys, strict=True):
            area.lineTo(QPointF(x, y))
        area.lineTo(QPointF(xs[-1], zero_y))
        area.closeSubpath()
        accent = QColor(self._palette.accent)
        fill = QColor(accent)
        fill.setAlpha(38)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(fill)
        painter.drawPath(area)

        line = QPainterPath()
        line.moveTo(QPointF(xs[0], ys[0]))
        for x, y in zip(xs[1:], ys[1:], strict=True):
            line.lineTo(QPointF(x, y))
        pen = QPen(accent, 2.4)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(line)

        if count <= 16:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(accent)
            for x, y in zip(xs, ys, strict=True):
                painter.drawEllipse(QPointF(x, y), 3.2, 3.2)

        self._paint_x_labels(painter, plot, xs)

    def _paint_bars(self, painter: QPainter) -> None:
        plot = self._plot_rect()
        values = [point.value for point in self._points]
        minimum, maximum = self._axis_bounds(values)
        zero_y = self._map_y(0.0, minimum, maximum, plot)
        self._paint_grid(painter, plot, minimum, maximum)

        count = len(self._points)
        slot = plot.width() / max(1, count)
        bar_width = min(52.0, max(12.0, slot * 0.55))
        xs: list[float] = []

        for index, point in enumerate(self._points):
            center = plot.left() + (index + 0.5) * slot
            xs.append(center)
            top = self._map_y(max(0.0, point.value), minimum, maximum, plot)
            bottom = self._map_y(min(0.0, point.value), minimum, maximum, plot)
            height = max(2.0, bottom - top)
            bar_rect = QRectF(
                center - bar_width / 2,
                top,
                bar_width,
                height,
            )
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(self._tone_color(point.tone))
            painter.drawRoundedRect(bar_rect, 4, 4)

            self._paint_value_label(
                painter,
                bar_rect,
                point.value,
                positive=point.value >= 0,
            )

        self._paint_x_labels(painter, plot, xs)
        painter.setPen(QPen(QColor(self._palette.axis), 1))
        painter.drawLine(
            QPointF(plot.left(), zero_y),
            QPointF(plot.right(), zero_y),
        )

    def _paint_horizontal_bars(self, painter: QPainter) -> None:
        rect = QRectF(self.rect()).adjusted(8, 8, -8, -8)
        label_font = QFont(self.font())
        label_font.setPointSizeF(max(7.5, self.font().pointSizeF() - 1))
        metrics = QFontMetricsF(label_font)
        label_width = min(
            max(96.0, rect.width() * 0.34),
            max(
                (
                    metrics.horizontalAdvance(point.label)
                    for point in self._points
                ),
                default=96.0,
            )
            + 12.0,
        )
        plot = QRectF(
            rect.left() + label_width,
            rect.top() + 4,
            max(20.0, rect.width() - label_width - 64.0),
            max(20.0, rect.height() - 8.0),
        )
        maximum = max(
            (max(0.0, point.value) for point in self._points),
            default=0.0,
        )
        if maximum <= 0:
            maximum = 1.0

        slot = plot.height() / max(1, len(self._points))
        bar_height = min(22.0, max(9.0, slot * 0.55))
        painter.setFont(label_font)

        for index, point in enumerate(self._points):
            center = plot.top() + (index + 0.5) * slot
            label_rect = QRectF(
                rect.left(),
                center - bar_height / 2,
                label_width - 10,
                bar_height,
            )
            painter.setPen(QColor(self._palette.text))
            painter.drawText(
                label_rect,
                Qt.AlignmentFlag.AlignRight
                | Qt.AlignmentFlag.AlignVCenter,
                metrics.elidedText(
                    point.label,
                    Qt.TextElideMode.ElideRight,
                    int(label_rect.width()),
                ),
            )

            track = QRectF(
                plot.left(),
                center - bar_height / 2,
                plot.width(),
                bar_height,
            )
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(self._palette.track))
            painter.drawRoundedRect(track, bar_height / 2, bar_height / 2)

            width = max(
                2.0,
                min(1.0, max(0.0, point.value) / maximum) * plot.width(),
            )
            value_rect = QRectF(
                plot.left(),
                center - bar_height / 2,
                width,
                bar_height,
            )
            painter.setBrush(self._tone_color(point.tone))
            painter.drawRoundedRect(
                value_rect,
                bar_height / 2,
                bar_height / 2,
            )

            painter.setFont(label_font)
            painter.setPen(QColor(self._palette.muted_text))
            painter.drawText(
                QRectF(
                    plot.right() + 8,
                    center - bar_height / 2,
                    56,
                    bar_height,
                ),
                Qt.AlignmentFlag.AlignLeft
                | Qt.AlignmentFlag.AlignVCenter,
                self._format_value(point.value, compact=True),
            )

    def _paint_grid(
        self,
        painter: QPainter,
        plot: QRectF,
        minimum: float,
        maximum: float,
    ) -> None:
        painter.setFont(self._axis_font())
        metrics = QFontMetricsF(self._axis_font())
        for value in self._axis_values(minimum, maximum):
            y = self._map_y(value, minimum, maximum, plot)
            painter.setPen(QPen(QColor(self._palette.grid), 1))
            painter.drawLine(
                QPointF(plot.left(), y),
                QPointF(plot.right(), y),
            )
            label = self._format_value(value, compact=True)
            painter.setPen(QColor(self._palette.muted_text))
            painter.drawText(
                QRectF(
                    plot.left() - metrics.horizontalAdvance(label) - 10,
                    y - 9,
                    metrics.horizontalAdvance(label) + 6,
                    18,
                ),
                Qt.AlignmentFlag.AlignRight
                | Qt.AlignmentFlag.AlignVCenter,
                label,
            )

    def _paint_x_labels(
        self,
        painter: QPainter,
        plot: QRectF,
        xs: Sequence[float],
    ) -> None:
        painter.setFont(self._axis_font())
        metrics = QFontMetricsF(self._axis_font())
        count = len(self._points)
        if count == 0:
            return
        if self._kind == "bar" and count <= 6:
            indexes = list(range(count))
        else:
            max_labels = max(2, int(plot.width() // 82))
            if count <= max_labels:
                indexes = list(range(count))
            else:
                step = (count - 1) / (max_labels - 1)
                indexes = sorted(
                    {round(index * step) for index in range(max_labels)}
                )
        slot_width = plot.width() / max(1, count)
        max_width = slot_width * 0.92 if self._kind == "bar" else 96.0

        for index in indexes:
            label = self._points[index].label
            width = min(
                max_width,
                metrics.horizontalAdvance(label) + 8,
            )
            left = min(
                max(plot.left(), xs[index] - width / 2),
                plot.right() - width,
            )
            painter.setPen(QColor(self._palette.muted_text))
            painter.drawText(
                QRectF(left, plot.bottom() + 9, width, 20),
                Qt.AlignmentFlag.AlignHCenter
                | Qt.AlignmentFlag.AlignTop,
                metrics.elidedText(
                    label,
                    Qt.TextElideMode.ElideRight,
                    int(width),
                ),
            )

    def _paint_value_label(
        self,
        painter: QPainter,
        bar_rect: QRectF,
        value: float,
        *,
        positive: bool,
    ) -> None:
        painter.setFont(self._axis_font())
        metrics = QFontMetricsF(self._axis_font())
        label = self._format_value(value, compact=True)
        width = metrics.horizontalAdvance(label) + 8
        if positive:
            y = bar_rect.top() - 19
        else:
            y = bar_rect.bottom() + 2
        painter.setPen(QColor(self._palette.text))
        painter.drawText(
            QRectF(
                bar_rect.center().x() - width / 2,
                y,
                width,
                18,
            ),
            Qt.AlignmentFlag.AlignCenter,
            label,
        )

    def _axis_bounds(self, values: Sequence[float]) -> tuple[float, float]:
        minimum = min(0.0, min(values, default=0.0))
        maximum = max(0.0, max(values, default=0.0))
        if maximum == minimum:
            maximum = minimum + 1.0
        span = maximum - minimum
        if minimum < 0:
            minimum -= span * 0.08
        if maximum > 0:
            maximum += span * 0.08
        return minimum, maximum

    def _axis_values(
        self,
        minimum: float | None = None,
        maximum: float | None = None,
    ) -> tuple[float, ...]:
        if minimum is None or maximum is None:
            minimum, maximum = self._axis_bounds(
                [point.value for point in self._points]
            )
        return tuple(
            minimum + (maximum - minimum) * index / 4
            for index in range(5)
        )

    @staticmethod
    def _map_y(
        value: float,
        minimum: float,
        maximum: float,
        plot: QRectF,
    ) -> float:
        if maximum == minimum:
            return plot.center().y()
        ratio = (value - minimum) / (maximum - minimum)
        return plot.bottom() - ratio * plot.height()

    def _format_value(self, value: float, *, compact: bool = False) -> str:
        if self._value_kind == "quantity":
            return self._locale.toString(int(round(value)))
        return format_chart_money(
            value,
            self._currency_code,
            self._locale,
            compact=compact,
        )

    def _tone_color(self, tone: str) -> QColor:
        available = {
            "accent": self._palette.accent,
            "positive": self._palette.positive,
            "negative": self._palette.negative,
            "warning": self._palette.warning,
            "neutral": self._palette.neutral,
        }
        return QColor(available.get(tone, self._palette.accent))

    def _axis_font(self) -> QFont:
        font = QFont(self.font())
        font.setPointSizeF(max(7.0, self.font().pointSizeF() - 1.5))
        return font

    def _update_tooltip(self) -> None:
        if not self._points:
            self.setToolTip(
                "\n".join(
                    value
                    for value in (self._empty_text, self._empty_hint)
                    if value
                )
            )
            return
        lines = []
        for point in self._points:
            value = point.tooltip or self._format_value(point.value)
            lines.append(f"{point.label}: {value}")
        self.setToolTip("\n".join(lines))


def chart_locale(language: str) -> QLocale:
    """Return a locale suitable for chart labels and number formatting."""
    return QLocale("es_ES" if language == "es" else "en_US")


def format_chart_money(
    value: float,
    currency_code: str,
    locale: QLocale,
    *,
    compact: bool = False,
) -> str:
    """Format a monetary value for an axis, label or tooltip."""
    absolute = abs(value)
    if compact and absolute >= 1_000_000:
        number = f"{locale.toString(value / 1_000_000, 'f', 1)}M"
    elif compact and absolute >= 1_000:
        number = f"{locale.toString(value / 1_000, 'f', 1)}K"
    else:
        decimals = 0 if compact else 2
        number = locale.toString(value, "f", decimals)
    return f"{number} {currency_code}"


def format_chart_bucket(
    value,
    granularity: str,
    language: str,
) -> str:
    """Format a date bucket for a chart axis."""
    locale = chart_locale(language)
    date = QDate(value.year, value.month, value.day)
    if granularity == "month":
        pattern = "MMM yyyy"
    else:
        pattern = "d MMM" if language == "es" else "MMM d"
    return locale.toString(date, pattern)


def format_chart_tooltip_date(
    value,
    granularity: str,
    language: str,
) -> str:
    """Format a complete date for a point tooltip."""
    locale = chart_locale(language)
    date = QDate(value.year, value.month, value.day)
    if granularity == "month":
        pattern = "MMMM 'de' yyyy" if language == "es" else "MMMM yyyy"
    else:
        pattern = (
            "d 'de' MMMM 'de' yyyy"
            if language == "es"
            else "MMMM d, yyyy"
        )
    return locale.toString(date, pattern)
