"""Configuration tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.infrastructure.config.settings import Settings


def test_database_url_can_be_overridden_by_environment(
    monkeypatch, tmp_path: Path
) -> None:
    database_url = f"sqlite:///{(tmp_path / 'from_env.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)

    settings = Settings(_env_file=None)

    assert settings.database_url == database_url


def test_default_settings_target_the_local_data_directory(monkeypatch) -> None:
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("BASE_CURRENCY", raising=False)
    monkeypatch.delenv("ANALYTICS_SLOW_MOVING_DAYS", raising=False)
    monkeypatch.delenv("FX_PROVIDER", raising=False)
    monkeypatch.delenv("FX_AUTO_UPDATE", raising=False)
    monkeypatch.delenv("FX_FRESHNESS_HOURS", raising=False)
    monkeypatch.delenv("ELTOQUE_API_TOKEN", raising=False)
    monkeypatch.delenv("ELTOQUE_API_URL", raising=False)
    monkeypatch.delenv("ELTOQUE_TIMEOUT_SECONDS", raising=False)

    settings = Settings(_env_file=None)

    assert settings.app_env == "development"
    assert settings.database_url == "sqlite:///./data/resale_manager.db"
    assert settings.base_currency == "USD"
    assert settings.analytics_slow_moving_days == 30
    assert settings.fx_provider == "MANUAL"
    assert settings.fx_auto_update is False
    assert settings.fx_freshness_hours == 24
    assert settings.eltoque_api_token is None
    assert settings.eltoque_api_url == "https://api.eltoque.com/v1/rates"
    assert settings.eltoque_timeout_seconds == 10.0


def test_exchange_rate_settings_can_be_overridden(monkeypatch) -> None:
    monkeypatch.setenv("FX_PROVIDER", "eltoque")
    monkeypatch.setenv("FX_AUTO_UPDATE", "true")
    monkeypatch.setenv("FX_FRESHNESS_HOURS", "48")
    monkeypatch.setenv("ELTOQUE_API_TOKEN", "token")
    monkeypatch.setenv("ELTOQUE_API_URL", "https://example.test/rates")
    monkeypatch.setenv("ELTOQUE_TIMEOUT_SECONDS", "5.5")

    settings = Settings(_env_file=None)

    assert settings.fx_provider == "ELTOQUE"
    assert settings.fx_auto_update is True
    assert settings.fx_freshness_hours == 48
    assert settings.eltoque_api_token == "token"
    assert settings.eltoque_api_url == "https://example.test/rates"
    assert settings.eltoque_timeout_seconds == 5.5


def test_analytics_settings_are_normalized_and_validated(monkeypatch) -> None:
    monkeypatch.setenv("BASE_CURRENCY", " eur ")
    monkeypatch.setenv("ANALYTICS_SLOW_MOVING_DAYS", "45")

    settings = Settings(_env_file=None)

    assert settings.base_currency == "EUR"
    assert settings.analytics_slow_moving_days == 45


@pytest.mark.parametrize("value", ["US", "USDD", "12A", "   "])
def test_base_currency_must_be_a_three_letter_code(
    monkeypatch, value: str
) -> None:
    monkeypatch.setenv("BASE_CURRENCY", value)

    with pytest.raises(ValueError):
        Settings(_env_file=None)


def test_slow_moving_days_must_be_positive(monkeypatch) -> None:
    monkeypatch.setenv("ANALYTICS_SLOW_MOVING_DAYS", "0")

    with pytest.raises(ValueError):
        Settings(_env_file=None)
