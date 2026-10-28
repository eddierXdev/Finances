"""Text validation helpers shared by catalog entities."""

from __future__ import annotations


def required_text(value: str, field_name: str) -> str:
    """Return trimmed required text, or raise if it is blank."""
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string.")
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} is required.")
    return cleaned


def optional_text(value: str | None, field_name: str) -> str | None:
    """Return trimmed optional text, converting blanks to ``None``."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string or None.")
    return value.strip() or None
