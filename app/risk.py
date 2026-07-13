
from __future__ import annotations

from typing import Dict, Iterable, List
import math
import numpy as np
import pandas as pd

from app.schemas import Holding, RiskContribution, RiskMetrics

TRADING_DAYS = 252


def compute_returns(price_history: Dict[str, Iterable[float]]) -> pd.DataFrame:
    if not price_history:
        raise ValueError("price history is required")
    frame = pd.DataFrame({ticker.upper(): list(values) for ticker, values in price_history.items()})
    frame = frame.astype(float).dropna(axis=0, how="any")
    if len(frame) < 3:
        raise ValueError("at least three price observations are required")
    returns = frame.pct_change().dropna(how="any")
    if returns.empty:
        raise ValueError("not enough price variation to compute returns")
    return returns


def portfolio_return_series(holdings: List[Holding], returns: pd.DataFrame) -> pd.Series:
    missing = [h.ticker for h in holdings if h.ticker not in returns.columns]
    if missing:
        raise ValueError(f"missing price history for: {', '.join(missing)}")
    weights = pd.Series({h.ticker: h.weight for h in holdings}, dtype=float)
    return returns[weights.index].mul(weights, axis=1).sum(axis=1)


def max_drawdown_from_returns(returns: pd.Series) -> float:
    cumulative = (1 + returns).cumprod()
    running_max = cumulative.cummax()
    drawdowns = cumulative / running_max - 1
    return float(drawdowns.min())


def risk_metrics(portfolio_returns: pd.Series, risk_free_rate: float = 0.0) -> RiskMetrics:
    if portfolio_returns.empty:
        raise ValueError("portfolio returns cannot be empty")
    daily_rf = risk_free_rate / TRADING_DAYS
    volatility = float(portfolio_returns.std(ddof=1) * math.sqrt(TRADING_DAYS))
    var_95 = float(np.quantile(portfolio_returns, 0.05))
    tail = portfolio_returns[portfolio_returns <= var_95]
    expected_shortfall = float(tail.mean()) if not tail.empty else var_95
    excess = portfolio_returns - daily_rf
    return_std = portfolio_returns.std(ddof=1)
    sharpe = float((excess.mean() / return_std) * math.sqrt(TRADING_DAYS)) if return_std else 0.0
    downside = excess[excess < 0]
    downside_std = downside.std(ddof=1) if len(downside) > 1 else 0.0
    sortino = float((excess.mean() / downside_std) * math.sqrt(TRADING_DAYS)) if downside_std else 0.0
    return RiskMetrics(
        volatility=round(volatility, 6),
        value_at_risk_95=round(var_95, 6),
        expected_shortfall_95=round(expected_shortfall, 6),
        max_drawdown=round(max_drawdown_from_returns(portfolio_returns), 6),
        sharpe_ratio=round(sharpe, 6),
        sortino_ratio=round(sortino, 6),
    )


def correlation_matrix(returns: pd.DataFrame) -> Dict[str, Dict[str, float]]:
    corr = returns.corr().replace([np.inf, -np.inf], np.nan).fillna(0.0)
    return {row: {col: round(float(corr.loc[row, col]), 4) for col in corr.columns} for row in corr.index}


def average_pairwise_correlation(returns: pd.DataFrame) -> float:
    """Return the mean correlation across unique holding pairs."""
    corr = returns.corr().replace([np.inf, -np.inf], np.nan)
    upper_triangle = corr.where(np.triu(np.ones(corr.shape, dtype=bool), k=1))
    pairs = upper_triangle.stack()
    return round(float(pairs.mean()), 4) if not pairs.empty else 0.0


def risk_contributions(holdings: List[Holding], returns: pd.DataFrame) -> List[RiskContribution]:
    """Estimate each holding's marginal contribution to portfolio variance."""
    tickers = [holding.ticker for holding in holdings]
    weights = np.array([holding.weight for holding in holdings], dtype=float)
    covariance = returns[tickers].cov().to_numpy() * TRADING_DAYS
    portfolio_variance = float(weights.T @ covariance @ weights)

    if not math.isfinite(portfolio_variance) or portfolio_variance <= 0:
        contributions = np.zeros(len(holdings))
    else:
        contributions = weights * (covariance @ weights) / portfolio_variance

    rows = [
        RiskContribution(
            ticker=holding.ticker,
            weight=holding.weight,
            risk_contribution_pct=round(float(contribution), 6),
            annualized_volatility=round(float(returns[holding.ticker].std(ddof=1) * math.sqrt(TRADING_DAYS)), 6),
        )
        for holding, contribution in zip(holdings, contributions)
    ]
    return sorted(rows, key=lambda row: abs(row.risk_contribution_pct), reverse=True)
