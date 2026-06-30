
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.responses import HTMLResponse

from app.analysis import analyze_concentration, infer_theme_exposures
from app.copilot import build_copilot_report
from app.market_data import (
    MarketDataError,
    MarketDataUnavailableError,
    fetch_price_history_with_metadata,
    normalize_inline_prices,
)
from app.risk import compute_returns, correlation_matrix, portfolio_return_series, risk_metrics
from app.schemas import DataSource, ErrorResponse, PortfolioRequest, PortfolioResponse
from app.stress import run_stress_tests

app = FastAPI(title="Portfolio Risk Copilot", version="0.1.0")


def api_error(code: str, message: str, *, status_code: int = 400, retryable: bool = False) -> HTTPException:
    return HTTPException(status_code=status_code, detail=ErrorResponse(code=code, message=message, retryable=retryable).model_dump())


@app.exception_handler(MarketDataUnavailableError)
async def market_data_unavailable_handler(request: Request, exc: MarketDataUnavailableError) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={"detail": ErrorResponse(code=exc.code, message=str(exc), retryable=True).model_dump()},
    )


@app.exception_handler(MarketDataError)
async def market_data_error_handler(request: Request, exc: MarketDataError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": ErrorResponse(code=exc.code, message=str(exc), retryable=False).model_dump()},
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze", response_model=PortfolioResponse)
def analyze_portfolio(request: PortfolioRequest) -> PortfolioResponse:
    try:
        tickers = [h.ticker for h in request.holdings]
        if request.price_history:
            prices = normalize_inline_prices(request.price_history)
            data_source = DataSource(
                type="inline",
                provider="user_supplied",
                lookback_period=request.lookback_period,
                tickers=tickers,
                price_points={ticker: len(values) for ticker, values in prices.items()},
            )
        else:
            live_data = fetch_price_history_with_metadata(tickers, request.lookback_period)
            prices = live_data.prices
            data_source = DataSource(
                type="live",
                provider="yfinance",
                lookback_period=request.lookback_period,
                tickers=tickers,
                price_points={ticker: len(values) for ticker, values in prices.items()},
                warnings=live_data.warnings,
                stale=live_data.stale,
                fetched_at=live_data.fetched_at,
            )
        returns = compute_returns(prices)
        portfolio_returns = portfolio_return_series(request.holdings, returns)
        metrics = risk_metrics(portfolio_returns, request.risk_free_rate)
        correlations = correlation_matrix(returns[[h.ticker for h in request.holdings]])
        theme_exposures = infer_theme_exposures(request.holdings)
        concentration = analyze_concentration(request.holdings, theme_exposures)
        stress_tests = run_stress_tests(request.holdings, theme_exposures)
        report = build_copilot_report(metrics, concentration, stress_tests, theme_exposures)
        methodology = [
            (
                "Fetched adjusted close prices from yfinance for the selected lookback period."
                if data_source.type == "live"
                else "Used the inline price history supplied in the request."
            ),
            *(["Market-data warning: " + warning for warning in data_source.warnings] if data_source.warnings else []),
            "Converted prices into daily percentage returns for each holding.",
            "Built portfolio returns as the weighted sum of holding returns.",
            "Annualized volatility is daily portfolio return volatility multiplied by the square root of 252 trading days.",
            "Daily 95% VaR is the 5th percentile daily portfolio return; expected shortfall is the average loss beyond that threshold.",
            "Max drawdown is computed from the cumulative portfolio return curve.",
            "Stress-test impacts are scenario shocks multiplied by mapped theme exposures.",
        ]
        return PortfolioResponse(
            summary=report.summary,
            risk_score=report.risk_score,
            metrics=metrics,
            concentration=concentration,
            theme_exposures=theme_exposures,
            correlations=correlations,
            stress_tests=stress_tests,
            suggestions=report.suggestions,
            methodology=methodology,
            data_source=data_source,
            report_markdown=report.report_markdown,
        )
    except MarketDataError:
        raise
    except ValueError as exc:
        raise api_error("analysis_input_error", str(exc), status_code=400) from exc
    except Exception as exc:
        raise api_error("analysis_failed", "Unexpected analysis failure", status_code=500, retryable=True) from exc


@app.get("/", response_class=HTMLResponse)
def demo_page() -> str:
    with open("frontend/index.html", "r", encoding="utf-8") as f:
        return f.read()
