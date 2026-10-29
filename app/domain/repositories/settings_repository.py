"""Settings repository contract."""

from typing import Protocol


class SettingsRepository(Protocol):
    """Persistence boundary for application settings."""

    def get(self, key: str) -> str | None:
        """Return a setting value by key, if it exists."""
        ...

    def set(self, key: str, value: str) -> None:
        """Create or replace a setting value."""
        ...
