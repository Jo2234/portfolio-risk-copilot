from datetime import timedelta

import pandas as pd
import pytest

from app.market_data import (
    MarketDataUnavailableError,
    MarketDataValidationError,
    fetch_price_history,
    fetch_price_history_with_metadata,
)


def test_fetch_price_history_validates_and_caches_yfinance_downloads():
    calls = {"count": 0}

    def downloader(*args, **kwargs):
        calls["count"] += 1
        assert kwargs["timeout"] == 10
        return pd.DataFrame({("Close", "AAA"): [100, 101, 103], ("Close", "BBB"): [50, 51, 52]})

    result = fetch_price_history_with_metadata(["aaa", "BBB"], "1y", downloader=downloader)
    cached = fetch_price_history_with_metadata(["AAA", "BBB"], "1y", downloader=downloader)

    assert result.prices == {"AAA": [100.0, 101.0, 103.0], "BBB": [50.0, 51.0, 52.0]}
    assert cached.prices == result.prices
    assert cached.warnings == ["Served market data from a short-lived in-memory cache."]
    assert calls["count"] == 1


def test_fetch_price_history_retries_then_uses_stale_cache_when_refresh_fails():
    healthy = pd.DataFrame({"Close": [100, 101, 102]})
    fetch_price_history_with_metadata(["AAA"], "stale-test", downloader=lambda *args, **kwargs: healthy)

    calls = {"count": 0}

    def failing_downloader(*args, **kwargs):
        calls["count"] += 1
        raise TimeoutError("network timeout")

    result = fetch_price_history_with_metadata(
        ["AAA"],
        "stale-test",
        retries=1,
        cache_ttl=timedelta(seconds=0),
        stale_cache_ttl=timedelta(hours=1),
        downloader=failing_downloader,
    )

    assert result.stale is True
    assert result.prices == {"AAA": [100.0, 101.0, 102.0]}
    assert any("stale cached prices" in warning for warning in result.warnings)
    assert calls["count"] == 2


def test_fetch_price_history_raises_structured_market_data_errors_for_bad_data():
    def empty_downloader(*args, **kwargs):
        return pd.DataFrame()

    with pytest.raises(MarketDataUnavailableError):
        fetch_price_history_with_metadata(["AAA"], "empty-test", cache_ttl=timedelta(seconds=0), downloader=empty_downloader)

    def short_downloader(*args, **kwargs):
        return pd.DataFrame({"Close": [100, 101]})

    with pytest.raises(MarketDataValidationError):
        fetch_price_history_with_metadata(["AAA"], "short-test", downloader=short_downloader)


def test_fetch_price_history_keeps_backwards_compatible_dict_return():
    def downloader(*args, **kwargs):
        return pd.DataFrame({"Close": [100, 101, 102]})

    result = fetch_price_history_with_metadata(["AAA"], "compat-test", downloader=downloader)
    assert result.prices == {"AAA": [100.0, 101.0, 102.0]}

    # Public compatibility wrapper still returns only price dictionaries.
    assert fetch_price_history(["AAA"], "compat-test") == {"AAA": [100.0, 101.0, 102.0]}
