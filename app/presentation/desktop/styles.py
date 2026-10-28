"""Application stylesheet for the desktop shell."""

APP_STYLESHEET = """
QMainWindow {
    background: #f5f6f8;
}

#sidebar {
    background: #1f2937;
    border: none;
}

#brand {
    color: #f9fafb;
    font-size: 18px;
    font-weight: 600;
    padding: 22px 20px 6px 20px;
}

#brandSubtitle {
    color: #9ca3af;
    font-size: 12px;
    padding: 0 20px 18px 20px;
}

#navigation {
    background: transparent;
    border: none;
    color: #d1d5db;
    font-size: 14px;
    outline: 0;
}

#navigation::item {
    padding: 10px 18px;
    margin: 2px 8px;
    border-radius: 6px;
}

#navigation::item:hover {
    background: #374151;
}

#navigation::item:selected {
    background: #2563eb;
    color: #ffffff;
}

#content {
    background: #f5f6f8;
}

#pageTitle {
    color: #111827;
    font-size: 26px;
    font-weight: 600;
}

#pageDescription {
    color: #4b5563;
    font-size: 14px;
}

#pageSeparator {
    background: #e5e7eb;
    border: none;
    margin: 8px 0;
}

#pageBadge {
    background: #e0e7ff;
    color: #3730a3;
    border-radius: 10px;
    font-size: 11px;
    font-weight: 600;
    padding: 3px 10px;
}

#pageNote {
    color: #6b7280;
    font-size: 13px;
}

QStatusBar {
    background: #ffffff;
    color: #4b5563;
    border-top: 1px solid #e5e7eb;
}

QPushButton {
    background: #ffffff;
    color: #374151;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    padding: 7px 14px;
    font-size: 13px;
}

QPushButton:hover {
    background: #f3f4f6;
}

QPushButton:pressed {
    background: #e5e7eb;
}

QPushButton:disabled {
    background: #f9fafb;
    color: #9ca3af;
    border-color: #e5e7eb;
}

QPushButton[variant="primary"] {
    background: #2563eb;
    color: #ffffff;
    border-color: #2563eb;
    font-weight: 600;
}

QPushButton[variant="primary"]:hover {
    background: #1d4ed8;
}

QPushButton[variant="primary"]:disabled {
    background: #bfdbfe;
    color: #eff6ff;
    border-color: #bfdbfe;
}

QLineEdit,
QComboBox,
QPlainTextEdit {
    background: #ffffff;
    color: #111827;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    padding: 6px 8px;
    font-size: 13px;
}

QLineEdit:focus,
QComboBox:focus,
QPlainTextEdit:focus {
    border-color: #2563eb;
}

QCheckBox {
    color: #374151;
    font-size: 13px;
    spacing: 6px;
}

QTableView {
    background: #ffffff;
    alternate-background-color: #f9fafb;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    gridline-color: #f3f4f6;
    selection-background-color: #dbeafe;
    selection-color: #111827;
}

QTableView::item {
    padding: 7px 8px;
    border: none;
}

QHeaderView::section {
    background: #f9fafb;
    color: #6b7280;
    border: none;
    border-bottom: 1px solid #e5e7eb;
    padding: 8px;
    font-size: 12px;
    font-weight: 600;
}

QTreeWidget {
    background: #ffffff;
    alternate-background-color: #f9fafb;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 4px;
}

QTreeWidget::item {
    padding: 4px 6px;
    border-radius: 4px;
}

QTreeWidget::item:selected {
    background: #dbeafe;
    color: #111827;
}

#productsFooter {
    color: #6b7280;
    font-size: 12px;
}

#emptyStateTitle {
    color: #374151;
    font-size: 17px;
    font-weight: 600;
}

#emptyStateHint {
    color: #6b7280;
    font-size: 13px;
}

#errorBanner {
    background: #fef2f2;
    color: #b91c1c;
    border: 1px solid #fecaca;
    border-radius: 6px;
    padding: 9px 12px;
    font-size: 13px;
}

QDialog {
    background: #f5f6f8;
}

#dialogTitle {
    color: #111827;
    font-size: 20px;
    font-weight: 600;
}

#fieldHint {
    color: #6b7280;
    font-size: 12px;
}

QGroupBox {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    margin-top: 10px;
    padding: 12px 10px 8px 10px;
    font-size: 13px;
    font-weight: 600;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: #374151;
}
"""

