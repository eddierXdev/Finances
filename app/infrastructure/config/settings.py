"""Application settings loaded from environment variables and ``.env``."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, independent from domain rules."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    database_url: str = "sqlite:///./data/resale_manager.db"
    base_currency: str = "USD"

    fx_provider: Literal["MANUAL", "ELTOQUE"] = "MANUAL"
    fx_auto_update: bool = False
    fx_freshness_hours: int = Field(default=24, gt=0)
    analytics_slow_moving_days: int = Field(default=30, gt=0)

    eltoque_api_token: str | None = None
    eltoque_api_url: str = Field(
        default="https://api.eltoque.com/v1/rates", min_length=1
    )
    eltoque_timeout_seconds: float = Field(default=10.0, gt=0)

    @field_validator("base_currency", mode="before")
    @classmethod
    def _normalize_base_currency(cls, value):
        if isinstance(value, str):
            normalized = value.strip().upper()
            if len(normalized) != 3 or not normalized.isalpha():
                raise ValueError(
                    "base_currency must be a three-letter currency code."
                )
            return normalized
        return value

    @field_validator("fx_provider", mode="before")
    @classmethod
    def _normalize_fx_provider(cls, value):
        if isinstance(value, str):
            return value.strip().upper()
        return value


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings instance."""
    return Settings()
