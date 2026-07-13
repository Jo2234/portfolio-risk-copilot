
import math

import pytest

from app.risk import (
    average_pairwise_correlation,
    compute_returns,
    correlation_matrix,
    portfolio_return_series,
    risk_contributions,
    risk_metrics,
)
from app.schemas import Holding, PortfolioRequest


def test_risk_metrics_calculates_volatility_var_expected_shortfall_and_drawdown():
    prices = {
        "AAA": [100, 102, 101, 105, 103],
        "BBB": [50, 49, 51, 52, 50],
    }
    req = PortfolioRequest(holdings=[Holding(ticker="AAA", weight=0.6), Holding(ticker="BBB", weight=0.4)])

    returns = compute_returns(prices)
    portfolio_returns = portfolio_return_series(req.holdings, returns)
    metrics = risk_metrics(portfolio_returns, risk_free_rate=0.0)

    assert metrics.volatility > 0
    assert metrics.value_at_risk_95 <= 0
    assert metrics.expected_shortfall_95 <= metrics.value_at_risk_95
    assert metrics.max_drawdown <= 0
    assert math.isfinite(metrics.sharpe_ratio)
    assert math.isfinite(metrics.sortino_ratio)


def test_correlation_matrix_uses_real_return_relationships():
    prices = {
        "AAA": [100, 110, 99, 108.9, 98.01],
        "BBB": [50, 55, 49.5, 54.45, 49.005],
        "CCC": [100, 90, 99, 89.1, 98.01],
    }

    matrix = correlation_matrix(compute_returns(prices))

    assert matrix["AAA"]["BBB"] > 0.99
    assert matrix["AAA"]["CCC"] < -0.99
    assert average_pairwise_correlation(compute_returns(prices)) == pytest.approx(-1 / 3, abs=0.001)


def test_risk_contributions_allocate_portfolio_variance_across_holdings():
    prices = {
        "AAA": [100, 104, 102, 108, 103, 110],
        "BBB": [100, 101, 100, 102, 101, 103],
    }
    holdings = [Holding(ticker="AAA", weight=0.6), Holding(ticker="BBB", weight=0.4)]

    contributions = risk_contributions(holdings, compute_returns(prices))

    assert contributions[0].ticker == "AAA"
    assert sum(row.risk_contribution_pct for row in contributions) == pytest.approx(1.0, abs=1e-6)
    assert all(row.annualized_volatility >= 0 for row in contributions)
