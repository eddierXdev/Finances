"""elTOQUE exchange-rate provider.

The provider is intentionally isolated in Infrastructure. It translates HTTP
and JSON failures into ``ExchangeRateProviderError`` so the application can fall
back to a locally stored rate instead of making the application unavailable.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from app.application.exchange_rates.provider import ExchangeRateProviderError
from app.domain.entities.exchange_rate import ExchangeRate
from app.domain.enums.exchange_rate_source import ExchangeRateSource
from app.domain.exceptions import InvalidExchangeRateError
from app.domain.repositories.currency_repository import CurrencyRepository

_DEFAULT_API_URL = "https://api.eltoque.com/v1/rates"
_CONTAINER_KEYS = (
    "rates",
    "data",
    "result",
    "results",
    "items",
    "payload",
)
_BASE_KEYS = (
    "base",
    "base_currency",
    "from",
    "from_currency",
    "source_currency",
    "currency_from",
)
_QUOTE_KEYS = (
    "quote",
    "quote_currency",
    "to",
    "to_currency",
    "target_currency",
    "currency_to",
)
_CURRENCY_KEYS = ("currency", "code", "symbol")
_RATE_KEYS = (
    "rate",
    "value",
    "price",
    "exchange_rate",
    "amount",
    "sell",
    "buy",
)
_TIMESTAMP_KEYS = (
    "timestamp",
    "rate_timestamp",
    "updated_at",
    "date",
    "datetime",
    "created_at",
    "time",
    "last_updated",
)


class ElToqueProvider:
    """Fetch Cuban-market exchange rates from the elTOQUE HTTP API."""

    source = ExchangeRateSource.ELTOQUE

    def __init__(
        self,
        currencies: CurrencyRepository,
        *,
        api_token: str | None,
        api_url: str = _DEFAULT_API_URL,
        timeout: float = 10.0,
        client: httpx.Client | None = None,
    ) -> None:
        if not isinstance(api_url, str) or not api_url.strip():
            raise ValueError("elTOQUE API URL is required.")
        if timeout <= 0:
            raise ValueError("elTOQUE timeout must be greater than zero.")

        self._currencies = currencies
        self._api_token = api_token.strip() if api_token else None
        self._api_url = api_url.strip()
        self._client = client or httpx.Client(
            timeout=timeout, follow_redirects=True
        )
        self._owns_client = client is None

    def close(self) -> None:
        """Close the internally created HTTP client."""
        if self._owns_client:
            self._client.close()

    def fetch_rate(
        self, base_code: str, quote_code: str
    ) -> ExchangeRate | None:
        base_code = _normalize_code(base_code, "Base")
        quote_code = _normalize_code(quote_code, "Quote")

        if not self._api_token:
            raise ExchangeRateProviderError(
                "ELTOQUE_API_TOKEN is not configured."
            )

        base_currency = self._currencies.get_by_code(base_code)
        if base_currency is None:
            raise ExchangeRateProviderError(
                f"Currency {base_code} is not registered locally."
            )
        quote_currency = self._currencies.get_by_code(quote_code)
        if quote_currency is None:
            raise ExchangeRateProviderError(
                f"Currency {quote_code} is not registered locally."
            )

        headers = {
            "Authorization": f"Bearer {self._api_token}",
            "Accept": "application/json",
        }
        try:
            response = self._client.get(
                self._api_url,
                headers=headers,
                params={"base": base_code, "quote": quote_code},
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ExchangeRateProviderError(
                f"elTOQUE request failed: {exc}"
            ) from exc

        try:
            payload = _decode_payload(response)
            extracted = _extract_rate(payload, base_code, quote_code)
        except (TypeError, ValueError) as exc:
            raise ExchangeRateProviderError(
                f"elTOQUE returned an invalid response: {exc}"
            ) from exc

        if extracted is None:
            return None

        rate_value, observed_at = extracted
        try:
            return ExchangeRate(
                base_currency=base_currency,
                quote_currency=quote_currency,
                rate=rate_value,
                source=ExchangeRateSource.ELTOQUE,
                rate_timestamp=observed_at or datetime.now(UTC),
            )
        except InvalidExchangeRateError as exc:
            raise ExchangeRateProviderError(
                f"elTOQUE returned an invalid rate: {exc}"
            ) from exc


def _normalize_code(code: str, label: str) -> str:
    if not isinstance(code, str) or not code.strip():
        raise ValueError(f"{label} currency code is required.")
    return code.strip().upper()


def _decode_payload(response: Any) -> Any:
    text = getattr(response, "text", None)
    if isinstance(text, str) and text.strip():
        return json.loads(text, parse_float=Decimal)
    return response.json()


def _extract_rate(
    payload: Any, base_code: str, quote_code: str
) -> tuple[Decimal, datetime | None] | None:
    if isinstance(payload, dict):
        direct = _record_rate(payload, base_code, quote_code)
        if direct is not None:
            return direct

        context_base = _first_code(payload, _BASE_KEYS)
        context_quote = _first_code(payload, _QUOTE_KEYS)
        if context_base is not None and context_base != base_code:
            return None
        if context_quote is not None and context_quote != quote_code:
            return None

        for key in _CONTAINER_KEYS:
            if key in payload:
                found = _extract_rate(payload[key], base_code, quote_code)
                if found is not None:
                    rate, observed_at = found
                    return rate, observed_at or _timestamp_from(payload)

        return _mapping_rate(payload, base_code, quote_code)

    if isinstance(payload, list):
        for item in payload:
            found = _extract_rate(item, base_code, quote_code)
            if found is not None:
                return found

    return None


def _record_rate(
    record: dict[str, Any], base_code: str, quote_code: str
) -> tuple[Decimal, datetime | None] | None:
    base = _first_code(record, _BASE_KEYS)
    quote = _first_code(record, _QUOTE_KEYS)
    currency = _first_code(record, _CURRENCY_KEYS)
    rate_value = _first_value(record, _RATE_KEYS)

    if rate_value is None:
        return None
    if base is not None and base != base_code:
        return None
    if quote is not None and quote != quote_code:
        return None
    if currency is not None and currency not in (base_code, quote_code):
        return None

    rate = _as_decimal(rate_value)
    if rate is None:
        return None
    return rate, _timestamp_from(record)


def _mapping_rate(
    payload: dict[str, Any], base_code: str, quote_code: str
) -> tuple[Decimal, datetime | None] | None:
    quote_value = _lookup(payload, quote_code)
    rate = _as_decimal(quote_value)
    if rate is not None:
        return rate, _timestamp_from(payload)

    base_value = _lookup(payload, base_code)
    if isinstance(base_value, dict):
        quote_value = _lookup(base_value, quote_code)
        rate = _as_decimal(quote_value)
        if rate is not None:
            return rate, _timestamp_from(base_value) or _timestamp_from(payload)
        return _extract_rate(base_value, base_code, quote_code)

    if isinstance(base_value, list):
        return _extract_rate(base_value, base_code, quote_code)

    return None


def _lookup(mapping: dict[str, Any], code: str) -> Any:
    if code in mapping:
        return mapping[code]
    normalized = code.upper()
    for key, value in mapping.items():
        if isinstance(key, str) and key.strip().upper() == normalized:
            return value
    return None


def _first_value(
    record: dict[str, Any], keys: tuple[str, ...]
) -> Any:
    for key in keys:
        if key in record and record[key] is not None:
            return record[key]

    normalized = {key.lower() for key in keys}
    for key, value in record.items():
        if (
            isinstance(key, str)
            and key.strip().lower() in normalized
            and value is not None
        ):
            return value
    return None


def _first_code(
    record: dict[str, Any], keys: tuple[str, ...]
) -> str | None:
    value = _first_value(record, keys)
    if isinstance(value, str) and value.strip():
        return value.strip().upper()
    return None


def _as_decimal(value: Any) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, Decimal):
        result = value
    elif isinstance(value, int):
        result = Decimal(value)
    elif isinstance(value, str):
        try:
            result = Decimal(value.strip())
        except InvalidOperation:
            return None
    else:
        return None

    if not result.is_finite() or result <= 0:
        return None
    return result


def _timestamp_from(record: dict[str, Any]) -> datetime | None:
    return _parse_timestamp(_first_value(record, _TIMESTAMP_KEYS))


def _parse_timestamp(value: Any) -> datetime | None:
    if isinstance(value, bool) or value is None:
        return None

    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value, UTC)
        except (OverflowError, OSError, ValueError):
            return None

    if not isinstance(value, str):
        return None

    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"

    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        parsed = None
        for pattern in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                parsed = datetime.strptime(text, pattern)
                break
            except ValueError:
                continue
        if parsed is None:
            return None

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
