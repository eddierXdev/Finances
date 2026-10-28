"""Exchange-rate provider tests."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal

import httpx
import pytest

from app.application.exchange_rates import ExchangeRateProviderError
from app.domain.entities.currency import Currency
from app.domain.enums.exchange_rate_source import ExchangeRateSource
from app.infrastructure.config.settings import Settings
from app.infrastructure.exchange_rates import (
    ElToqueProvider,
    ManualRateProvider,
    create_exchange_rate_provider,
)

USD = Currency(code="USD", name="US Dollar", decimal_places=2)
CUP = Currency(code="CUP", name="Cuban Peso", decimal_places=2)
EUR = Currency(code="EUR", name="Euro", decimal_places=2)


class FakeCurrencyRepository:
    def __init__(self, *currencies: Currency) -> None:
        self._currencies = {
            currency.code: currency for currency in currencies
        }

    def get_by_code(self, code: str) -> Currency | None:
        return self._currencies.get(code.strip().upper())


class FakeResponse:
    def __init__(self, payload, status_code: int = 200) -> None:
        self.text = json.dumps(payload)
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("GET", "https://api.eltoque.com")
            response = httpx.Response(
                self.status_code, request=request, text=self.text
            )
            raise httpx.HTTPStatusError(
                "provider error", request=request, response=response
            )


class FakeRateRepository:
    def get_latest_by_source(self, base_code, quote_code, source):
        return None


class FakeClient:
    def __init__(self, response=None, error: Exception | None = None) -> None:
        self._response = response
        self._error = error
        self.calls: list[tuple[str, dict]] = []

    def get(self, url: str, **kwargs):
        self.calls.append((url, kwargs))
        if self._error is not None:
            raise self._error
        assert self._response is not None
        return self._response


def _provider(
    *,
    payload=None,
    error: Exception | None = None,
    token: str | None = "secret",
    currencies: FakeCurrencyRepository | None = None,
    status_code: int = 200,
) -> tuple[ElToqueProvider, FakeClient]:
    client = FakeClient(
        FakeResponse(payload, status_code) if payload is not None else None,
        error=error,
    )
    provider = ElToqueProvider(
        currencies or FakeCurrencyRepository(USD, CUP, EUR),
        api_token=token,
        api_url="https://example.test/rates",
        client=client,
    )
    return provider, client


def test_eltoque_parses_a_direct_rate_without_float_conversion() -> None:
    provider, client = _provider(
        payload={
            "base": "USD",
            "quote": "CUP",
            "rate": "320.123456789012",
            "timestamp": "2026-10-20T14:30:00Z",
        }
    )

    rate = provider.fetch_rate("usd", "cup")

    assert rate is not None
    assert rate.source is ExchangeRateSource.ELTOQUE
    assert rate.base_currency.code == "USD"
    assert rate.quote_currency.code == "CUP"
    assert rate.rate == Decimal("320.123456789012")
    assert rate.rate_timestamp == datetime(
        2026, 10, 20, 14, 30, tzinfo=UTC
    )
    assert client.calls == [
        (
            "https://example.test/rates",
            {
                "headers": {
                    "Authorization": "Bearer secret",
                    "Accept": "application/json",
                },
                "params": {"base": "USD", "quote": "CUP"},
            },
        )
    ]


def test_eltoque_parses_a_rates_mapping() -> None:
    provider, _ = _provider(payload={"rates": {"CUP": "320.50"}})

    rate = provider.fetch_rate("USD", "CUP")

    assert rate is not None
    assert rate.rate == Decimal("320.50")
    assert rate.source is ExchangeRateSource.ELTOQUE


def test_eltoque_parses_a_list_of_records() -> None:
    provider, _ = _provider(
        payload=[
            {"from": "EUR", "to": "CUP", "value": "400.00"},
            {"from": "USD", "to": "CUP", "value": "320.00"},
        ]
    )

    rate = provider.fetch_rate("USD", "CUP")

    assert rate is not None
    assert rate.rate == Decimal("320.00")


def test_eltoque_returns_none_when_the_pair_is_absent() -> None:
    provider, _ = _provider(payload={"rates": {"EUR": "400.00"}})

    assert provider.fetch_rate("USD", "CUP") is None


def test_eltoque_requires_a_token() -> None:
    provider, client = _provider(payload={"rate": "320.00"}, token=None)

    with pytest.raises(ExchangeRateProviderError, match="API_TOKEN"):
        provider.fetch_rate("USD", "CUP")

    assert client.calls == []


def test_eltoque_wraps_connectivity_failures() -> None:
    provider, _ = _provider(error=httpx.ConnectError("offline"))

    with pytest.raises(ExchangeRateProviderError, match="request failed"):
        provider.fetch_rate("USD", "CUP")


def test_eltoque_wraps_http_status_failures() -> None:
    provider, _ = _provider(
        payload={"error": "unauthorized"}, status_code=401
    )

    with pytest.raises(ExchangeRateProviderError, match="request failed"):
        provider.fetch_rate("USD", "CUP")


def test_eltoque_rejects_an_unregistered_currency() -> None:
    provider, _ = _provider(
        payload={"rate": "320.00"},
        currencies=FakeCurrencyRepository(USD),
    )

    with pytest.raises(ExchangeRateProviderError, match="not registered"):
        provider.fetch_rate("USD", "CUP")


def test_eltoque_returns_none_for_an_invalid_rate() -> None:
    provider, _ = _provider(payload={"rate": "0"})

    assert provider.fetch_rate("USD", "CUP") is None


def test_factory_builds_the_configured_provider() -> None:
    currencies = FakeCurrencyRepository(USD, CUP)
    rates = FakeRateRepository()

    manual = create_exchange_rate_provider(
        Settings(_env_file=None, fx_provider="MANUAL"),
        currencies,
        rates,
    )
    automatic = create_exchange_rate_provider(
        Settings(
            _env_file=None,
            fx_provider="ELTOQUE",
            eltoque_api_token="token",
        ),
        currencies,
        rates,
    )

    assert isinstance(manual, ManualRateProvider)
    assert isinstance(automatic, ElToqueProvider)
    automatic.close()
