
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from app.analysis import analyze_concentration, infer_theme_exposures
from app.copilot import build_copilot_report
from app.market_data import fetch_price_history, normalize_inline_prices
from app.risk import compute_returns, correlation_matrix, portfolio_return_series, risk_metrics
from app.schemas import PortfolioRequest, PortfolioResponse
from app.stress import run_stress_tests

app = FastAPI(title="Portfolio Risk Copilot", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze", response_model=PortfolioResponse)
def analyze_portfolio(request: PortfolioRequest) -> PortfolioResponse:
    try:
        tickers = [h.ticker for h in request.holdings]
        prices = normalize_inline_prices(request.price_history) if request.price_history else fetch_price_history(tickers, request.lookback_period)
        returns = compute_returns(prices)
        portfolio_returns = portfolio_return_series(request.holdings, returns)
        metrics = risk_metrics(portfolio_returns, request.risk_free_rate)
        correlations = correlation_matrix(returns[[h.ticker for h in request.holdings]])
        theme_exposures = infer_theme_exposures(request.holdings)
        concentration = analyze_concentration(request.holdings, theme_exposures)
        stress_tests = run_stress_tests(request.holdings, theme_exposures)
        report = build_copilot_report(metrics, concentration, stress_tests, theme_exposures)
        return PortfolioResponse(
            summary=report.summary,
            risk_score=report.risk_score,
            metrics=metrics,
            concentration=concentration,
            theme_exposures=theme_exposures,
            correlations=correlations,
            stress_tests=stress_tests,
            suggestions=report.suggestions,
            report_markdown=report.report_markdown,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/", response_class=HTMLResponse)
def demo_page() -> str:
    with open("frontend/index.html", "r", encoding="utf-8") as f:
        return f.read()
