
from __future__ import annotations

from typing import Dict, Iterable, List


def normalize_inline_prices(price_history: Dict[str, Iterable[float]]) -> Dict[str, List[float]]:
    return {ticker.upper(): [float(v) for v in values] for ticker, values in price_history.items()}


def fetch_price_history(tickers: list[str], period: str = "2y") -> Dict[str, List[float]]:
    """Fetch adjusted close prices via yfinance. Kept isolated so tests can use inline prices."""
    import yfinance as yf

    data = yf.download(tickers, period=period, auto_adjust=True, progress=False, threads=False)
    if data.empty:
        raise ValueError("yfinance returned no price data")
    if len(tickers) == 1:
        close = data["Close"].dropna()
        return {tickers[0].upper(): close.astype(float).tolist()}
    close = data["Close"].dropna(how="all")
    return {ticker.upper(): close[ticker].dropna().astype(float).tolist() for ticker in tickers if ticker in close}
