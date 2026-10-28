"""Desktop UI test setup.

Qt must be configured for headless execution before PySide6 is imported.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from app.presentation.desktop.app import create_application  # noqa: E402


@pytest.fixture(scope="session")
def qapp() -> Iterator[QApplication]:
    """Provide one QApplication for the whole presentation test session."""
    app = create_application(["resale-manager-tests"])
    try:
        yield app
    finally:
        app.quit()
