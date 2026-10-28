"""Exchange-rate use-case tests against a migrated database."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.application.exchange_rates import (
    ExchangeRatePair,
    ExchangeRateProviderError,
    ResolveExchangeRate,
    ResolveExchangeRateRequest,
    SetManualExchangeRate,
    SetManualExchangeRateRequest,
    UpdateExchangeRates,
    UpdateExchangeRatesRequest,
)
from app.domain.entities.currency import Currency
from app.domain.entities.exchange_rate import ExchangeRate
from app.domain.enums.exchange_rate_source import ExchangeRateSource
from app.domain.exceptions import (
    CurrencyNotFoundError,
    ExchangeRateNotFoundError,
    InvalidExchangeRateError,
    StaleExchangeRateError,
)
from app.infrastructure.database.repositories import (
    SqlAlchemyCurrencyRepository,
    SqlAlchemyExchangeRateRepository,
)
from app.infrastructure.exchange_rates.manual_provider import ManualRateProvider

NOW = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)


class FakeProvider:
    source = ExchangeRateSource.ELTOQUE

    def __init__(
        self,
        rate: ExchangeRate | None = None,
        error: Exception | None = None,
    ) -> None:
        self._rate = rate
        self._error = error
        self.calls: list[tuple[str, str]] = []

    def fetch_rate(
        self, base_code: str, quote_code: str
    ) -> ExchangeRate | None:
        self.calls.append((base_code, quote_code))
        if self._error is not None:
            raise self._error
        return self._rate


def _currency(db_session, code: str) -> Currency:
    currency = SqlAlchemyCurrencyRepository(db_session).get_by_code(code)
    assert currency is not None
    return currency


def _rates(db_session) -> SqlAlchemyExchangeRateRepository:
    return SqlAlchemyExchangeRateRepository(db_session)


def _add_rate(
    db_session,
    base: Currency,
    quote: Currency,
    rate: str,
    *,
    source: ExchangeRateSource = ExchangeRateSource.MANUAL,
    timestamp: datetime = NOW,
    notes: str | None = None,
) -> ExchangeRate:
    return _rates(db_session).add(
        ExchangeRate(
            base_currency=base,
            quote_currency=quote,
            rate=Decimal(rate),
            source=source,
            rate_timestamp=timestamp,
            notes=notes,
        )
    )


def _manual_service(db_session) -> SetManualExchangeRate:
    return SetManualExchangeRate(
        SqlAlchemyCurrencyRepository(db_session),
        _rates(db_session),
        clock=lambda: NOW,
    )


def _resolve_service(db_session) -> ResolveExchangeRate:
    return ResolveExchangeRate(
        _rates(db_session),
        freshness=timedelta(hours=24),
        clock=lambda: NOW,
    )


def _update_service(db_session, provider) -> UpdateExchangeRates:
    return UpdateExchangeRates(
        _rates(db_session),
        provider,
        freshness=timedelta(hours=24),
        clock=lambda: NOW,
    )


def test_set_manual_exchange_rate_persists_a_manual_record(
    db_session,
) -> None:
    usd = _currency(db_session, "USD")
    cup = _currency(db_session, "CUP")

    stored = _manual_service(db_session).execute(
        SetManualExchangeRateRequest(
            base_code="usd",
            quote_code="cup",
            rate="320.123456789012",
            rate_timestamp=NOW,
            notes="  street rate  ",
        )
    )

    assert stored.id is not None
    assert stored.source is ExchangeRateSource.MANUAL
    assert stored.base_currency.code == "USD"
    assert stored.quote_currency.code == "CUP"
    assert stored.rate == Decimal("320.123456789012")
    assert stored.notes == "street rate"

    latest = _rates(db_session).get_latest("USD", "CUP")
    assert latest == stored
    assert latest is not None
    assert latest.id == stored.id


def test_set_manual_exchange_rate_rejects_unknown_currency(
    db_session,
) -> None:
    with pytest.raises(CurrencyNotFoundError):
        _manual_service(db_session).execute(
            SetManualExchangeRateRequest(
                base_code="USD",
                quote_code="XYZ",
                rate="320.50",
                rate_timestamp=NOW,
            )
        )


def test_set_manual_exchange_rate_rejects_the_same_currency(
    db_session,
) -> None:
    with pytest.raises(InvalidExchangeRateError):
        _manual_service(db_session).execute(
            SetManualExchangeRateRequest(
                base_code="USD",
                quote_code="USD",
                rate="1.00",
                rate_timestamp=NOW,
            )
        )


def test_resolve_returns_a_fresh_stored_rate(db_session) -> None:
    usd = _currency(db_session, "USD")
    cup = _currency(db_session, "CUP")
    stored = _add_rate(
        db_session,
        usd,
        cup,
        "320.50",
        timestamp=NOW - timedelta(hours=2),
    )

    quote = _resolve_service(db_session).execute(
        ResolveExchangeRateRequest(
            base_code="usd",
            quote_code="cup",
        )
    )

    assert quote.exchange_rate.id == stored.id
    assert quote.is_stale is False
    assert quote.age == timedelta(hours=2)
    assert quote.provider_error is None
    assert quote.source is ExchangeRateSource.MANUAL


def test_resolve_identifies_and_can_reject_a_stale_rate(
    db_session,
) -> None:
    usd = _currency(db_session, "USD")
    cup = _currency(db_session, "CUP")
    _add_rate(
        db_session,
        usd,
        cup,
        "300.00",
        timestamp=NOW - timedelta(hours=48),
    )
    service = _resolve_service(db_session)

    quote = service.execute(
        ResolveExchangeRateRequest(
            base_code="USD",
            quote_code="CUP",
            allow_stale=True,
        )
    )
    assert quote.is_stale is True
    assert quote.age == timedelta(hours=48)

    with pytest.raises(StaleExchangeRateError):
        service.execute(
            ResolveExchangeRateRequest(
                base_code="USD",
                quote_code="CUP",
                allow_stale=False,
            )
        )


def test_resolve_raises_when_no_rate_exists(db_session) -> None:
    with pytest.raises(ExchangeRateNotFoundError, match="manual"):
        _resolve_service(db_session).execute(
            ResolveExchangeRateRequest(
                base_code="USD",
                quote_code="CUP",
            )
        )


def test_resolve_uses_the_latest_rate_at_or_before_as_of(db_session) -> None:
    usd = _currency(db_session, "USD")
    cup = _currency(db_session, "CUP")
    older = _add_rate(
        db_session,
        usd,
        cup,
        "300.00",
        timestamp=NOW - timedelta(hours=48),
    )
    _add_rate(
        db_session,
        usd,
        cup,
        "320.00",
        timestamp=NOW - timedelta(hours=1),
    )

    quote = _resolve_service(db_session).execute(
        ResolveExchangeRateRequest(
            base_code="USD",
            quote_code="CUP",
            as_of=NOW - timedelta(hours=24),
        )
    )

    assert quote.exchange_rate.id == older.id
    assert quote.exchange_rate.rate == Decimal("300.00")
    assert quote.age == timedelta(hours=24)


def test_resolve_as_of_does_not_use_a_future_rate(db_session) -> None:
    usd = _currency(db_session, "USD")
    cup = _currency(db_session, "CUP")
    _add_rate(
        db_session,
        usd,
        cup,
        "320.00",
        timestamp=NOW - timedelta(hours=1),
    )

    with pytest.raises(ExchangeRateNotFoundError):
        _resolve_service(db_session).execute(
            ResolveExchangeRateRequest(
                base_code="USD",
                quote_code="CUP",
                as_of=NOW - timedelta(hours=24),
            )
        )


def test_resolve_as_of_must_be_timezone_aware(db_session) -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        _resolve_service(db_session).execute(
            ResolveExchangeRateRequest(
                base_code="USD",
                quote_code="CUP",
                as_of=datetime(2026, 10, 27, 12, 0),
            )
        )


def test_update_persists_a_successful_provider_rate(db_session) -> None:
    usd = _currency(db_session, "USD")
    cup = _currency(db_session, "CUP")
    fetched = ExchangeRate(
        base_currency=usd,
        quote_currency=cup,
        rate=Decimal("320.50"),
        source=ExchangeRateSource.ELTOQUE,
        rate_timestamp=NOW,
    )
    provider = FakeProvider(fetched)

    quotes = _update_service(db_session, provider).execute(
        UpdateExchangeRatesRequest(
            pairs=(ExchangeRatePair("usd", "cup"),)
        )
    )

    assert provider.calls == [("USD", "CUP")]
    assert len(quotes) == 1
    assert quotes[0].exchange_rate.id is not None
    assert quotes[0].source is ExchangeRateSource.ELTOQUE
    assert quotes[0].is_stale is False
    assert quotes[0].provider_error is None

    stored = _rates(db_session).get_latest("USD", "CUP")
    assert stored is not None
    assert stored.rate == Decimal("320.50")
    assert stored.source is ExchangeRateSource.ELTOQUE
    assert len(_rates(db_session).list_for_pair("USD", "CUP")) == 1


def test_update_falls_back_to_a_stored_rate_after_provider_failure(
    db_session,
) -> None:
    usd = _currency(db_session, "USD")
    cup = _currency(db_session, "CUP")
    stored = _add_rate(
        db_session,
        usd,
        cup,
        "310.00",
        timestamp=NOW - timedelta(hours=2),
    )
    provider = FakeProvider(
        error=ExchangeRateProviderError("network unavailable")
    )

    quote = _update_service(db_session, provider).execute(
        UpdateExchangeRatesRequest(
            pairs=(ExchangeRatePair("USD", "CUP"),)
        )
    )[0]

    assert quote.exchange_rate.id == stored.id
    assert quote.source is ExchangeRateSource.MANUAL
    assert quote.is_stale is False
    assert quote.provider_error == "network unavailable"
    assert len(_rates(db_session).list_for_pair("USD", "CUP")) == 1


def test_update_marks_a_stale_fallback_and_can_reject_it(
    db_session,
) -> None:
    usd = _currency(db_session, "USD")
    cup = _currency(db_session, "CUP")
    _add_rate(
        db_session,
        usd,
        cup,
        "300.00",
        timestamp=NOW - timedelta(hours=48),
    )
    provider = FakeProvider(
        error=ExchangeRateProviderError("network unavailable")
    )
    service = _update_service(db_session, provider)

    quote = service.execute(
        UpdateExchangeRatesRequest(
            pairs=(ExchangeRatePair("USD", "CUP"),)
        )
    )[0]
    assert quote.is_stale is True
    assert quote.age == timedelta(hours=48)

    with pytest.raises(StaleExchangeRateError):
        service.execute(
            UpdateExchangeRatesRequest(
                pairs=(ExchangeRatePair("USD", "CUP"),),
                allow_stale=False,
            )
        )


def test_update_raises_when_provider_fails_without_a_stored_rate(
    db_session,
) -> None:
    provider = FakeProvider(
        error=ExchangeRateProviderError("network unavailable")
    )

    with pytest.raises(ExchangeRateNotFoundError, match="manual"):
        _update_service(db_session, provider).execute(
            UpdateExchangeRatesRequest(
                pairs=(ExchangeRatePair("USD", "CUP"),)
            )
        )


def test_update_uses_a_manual_provider_without_duplicating_the_rate(
    db_session,
) -> None:
    usd = _currency(db_session, "USD")
    cup = _currency(db_session, "CUP")
    stored = _add_rate(
        db_session,
        usd,
        cup,
        "320.50",
        timestamp=NOW - timedelta(hours=1),
    )
    provider = ManualRateProvider(_rates(db_session))

    quote = _update_service(db_session, provider).execute(
        UpdateExchangeRatesRequest(
            pairs=(ExchangeRatePair("USD", "CUP"),)
        )
    )[0]

    assert quote.exchange_rate.id == stored.id
    assert quote.source is ExchangeRateSource.MANUAL
    assert quote.is_stale is False
    assert len(_rates(db_session).list_for_pair("USD", "CUP")) == 1


def test_update_ignores_a_rate_for_the_wrong_pair_and_uses_stored_data(
    db_session,
) -> None:
    usd = _currency(db_session, "USD")
    cup = _currency(db_session, "CUP")
    eur = _currency(db_session, "EUR")
    stored = _add_rate(
        db_session,
        usd,
        cup,
        "310.00",
        timestamp=NOW - timedelta(hours=1),
    )
    wrong_rate = ExchangeRate(
        base_currency=eur,
        quote_currency=cup,
        rate=Decimal("400.00"),
        source=ExchangeRateSource.ELTOQUE,
        rate_timestamp=NOW,
    )
    provider = FakeProvider(wrong_rate)

    quote = _update_service(db_session, provider).execute(
        UpdateExchangeRatesRequest(
            pairs=(ExchangeRatePair("USD", "CUP"),)
        )
    )[0]

    assert quote.exchange_rate.id == stored.id
    assert quote.provider_error == (
        "Provider returned a rate for a different currency pair."
    )
    assert len(_rates(db_session).list_for_pair("USD", "CUP")) == 1


def test_update_with_no_pairs_returns_no_quotes(db_session) -> None:
    provider = FakeProvider()

    assert _update_service(db_session, provider).execute(
        UpdateExchangeRatesRequest(pairs=())
    ) == []
    assert provider.calls == []
