
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import math
import time
from typing import Callable, Dict, Iterable, List, Mapping, Sequence

import pandas as pd

MIN_PRICE_POINTS = 3
DEFAULT_RETRIES = 2
DEFAULT_TIMEOUT_SECONDS = 10
CACHE_TTL = timedelta(minutes=15)
STALE_CACHE_TTL = timedelta(hours=6)


class MarketDataError(RuntimeError):
    """Base class for recoverable market-data failures."""

    code = "market_data_error"


class MarketDataUnavailableError(MarketDataError):
    """Raised when yfinance cannot return usable data for the requested tickers."""

    code = "market_data_unavailable"


class MarketDataValidationError(MarketDataError):
    """Raised when returned market data is malformed or insufficient."""

    code = "market_data_validation_failed"


@dataclass(frozen=True)
class MarketDataResult:
    prices: Dict[str, List[float]]
    warnings: List[str] = field(default_factory=list)
    fetched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    stale: bool = False


@dataclass(frozen=True)
class _CacheEntry:
    result: MarketDataResult
    created_at: datetime


_PRICE_CACHE: dict[tuple[tuple[str, ...], str], _CacheEntry] = {}


def normalize_inline_prices(price_history: Dict[str, Iterable[float]]) -> Dict[str, List[float]]:
    normalized = {ticker.upper(): [float(v) for v in values] for ticker, values in price_history.items()}
    _validate_prices(normalized, tuple(normalized))
    return normalized


def fetch_price_history(tickers: list[str], period: str = "2y") -> Dict[str, List[float]]:
    """Fetch adjusted close prices via yfinance and return only price lists.

    Kept for backwards compatibility with callers/tests that only need prices. New
    API code uses fetch_price_history_with_metadata to surface cache/staleness and
    partial-data warnings to clients.
    """
    return fetch_price_history_with_metadata(tickers, period).prices


def fetch_price_history_with_metadata(
    tickers: Sequence[str],
    period: str = "2y",
    *,
    retries: int = DEFAULT_RETRIES,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    cache_ttl: timedelta = CACHE_TTL,
    stale_cache_ttl: timedelta = STALE_CACHE_TTL,
    downloader: Callable[..., pd.DataFrame] | None = None,
) -> MarketDataResult:
    """Fetch adjusted close prices with validation, retries, timeout, and cache.

    Fresh cache hits avoid unnecessary yfinance calls. If yfinance fails but a
    still-reasonable stale cache entry exists, stale prices are returned with an
    explicit warning instead of failing the whole analysis.
    """
    normalized_tickers = tuple(dict.fromkeys(t.strip().upper() for t in tickers if t.strip()))
    if not normalized_tickers:
        raise MarketDataValidationError("at least one ticker is required")

    cache_key = (normalized_tickers, period)
    now = datetime.now(timezone.utc)
    cached = _PRICE_CACHE.get(cache_key)
    if cached and now - cached.created_at <= cache_ttl:
        return MarketDataResult(
            prices=cached.result.prices,
            warnings=[*cached.result.warnings, "Served market data from a short-lived in-memory cache."],
            fetched_at=cached.result.fetched_at,
            stale=False,
        )

    yf_download = downloader or _yfinance_download
    last_error: Exception | None = None
    attempts = max(1, retries + 1)
    for attempt in range(1, attempts + 1):
        try:
            data = yf_download(
                list(normalized_tickers),
                period=period,
                auto_adjust=True,
                progress=False,
                threads=False,
                timeout=timeout,
            )
            prices, warnings = _prices_from_download(data, normalized_tickers)
            _validate_prices(prices, normalized_tickers)
            lengths = {ticker: len(values) for ticker, values in prices.items()}
            if len(set(lengths.values())) > 1:
                warnings.append(
                    "Live price histories have different lengths after cleaning; returns are aligned on complete rows."
                )
            result = MarketDataResult(prices=prices, warnings=warnings, fetched_at=now)
            _PRICE_CACHE[cache_key] = _CacheEntry(result=result, created_at=now)
            return result
        except Exception as exc:  # yfinance raises a mix of requests/pandas errors
            last_error = exc
            if attempt < attempts:
                time.sleep(min(0.25 * attempt, 1.0))

    if cached and now - cached.created_at <= stale_cache_ttl:
        return MarketDataResult(
            prices=cached.result.prices,
            warnings=[
                *cached.result.warnings,
                "Live market-data refresh failed; returned stale cached prices.",
            ],
            fetched_at=cached.result.fetched_at,
            stale=True,
        )

    message = str(last_error) if last_error else "unknown yfinance error"
    if isinstance(last_error, MarketDataError):
        raise last_error
    raise MarketDataUnavailableError(f"Could not fetch usable market data from yfinance: {message}") from last_error


def _yfinance_download(*args, **kwargs) -> pd.DataFrame:
    import yfinance as yf

    return yf.download(*args, **kwargs)


def _prices_from_download(data: pd.DataFrame, tickers: Sequence[str]) -> tuple[Dict[str, List[float]], List[str]]:
    if data is None or data.empty:
        raise MarketDataUnavailableError("yfinance returned no price data")

    close = _close_prices(data)
    warnings: List[str] = []
    prices: Dict[str, List[float]] = {}

    if len(tickers) == 1 and isinstance(close, pd.Series):
        values = _clean_series(close)
        if values:
            prices[tickers[0]] = values
    else:
        if isinstance(close, pd.Series):
            raise MarketDataValidationError("expected per-ticker close prices but received a single series")
        close = close.dropna(how="all")
        for ticker in tickers:
            if ticker not in close.columns:
                warnings.append(f"No close-price column returned for {ticker}.")
                continue
            values = _clean_series(close[ticker])
            if len(values) < MIN_PRICE_POINTS:
                warnings.append(f"Insufficient price observations for {ticker}; received {len(values)}.")
                continue
            prices[ticker] = values

    missing = [ticker for ticker in tickers if ticker not in prices]
    if missing:
        warnings.append(f"Missing usable market data for: {', '.join(missing)}.")
    if prices and missing:
        warnings.append("Analysis uses a partial live-data set; risk results may exclude failed tickers.")
    return prices, warnings


def _close_prices(data: pd.DataFrame) -> pd.Series | pd.DataFrame:
    if "Close" not in data:
        raise MarketDataValidationError("yfinance response did not include close prices")
    return data["Close"]


def _clean_series(series: pd.Series) -> List[float]:
    values = pd.to_numeric(series, errors="coerce").dropna().astype(float).tolist()
    return [value for value in values if math.isfinite(value) and value > 0]


def _validate_prices(prices: Mapping[str, Iterable[float]], tickers: Sequence[str]) -> None:
    missing = [ticker for ticker in tickers if ticker.upper() not in prices]
    if missing:
        raise MarketDataValidationError(f"missing price history for: {', '.join(missing)}")
    lengths = {ticker: len(list(values)) for ticker, values in prices.items()}
    short = {ticker: count for ticker, count in lengths.items() if count < MIN_PRICE_POINTS}
    if short:
        details = ", ".join(f"{ticker} has {count}" for ticker, count in short.items())
        raise MarketDataValidationError(f"at least {MIN_PRICE_POINTS} price observations are required; {details}")
