
from fastapi.testclient import TestClient

from app.main import app


def test_api_analyze_accepts_inline_prices_and_returns_full_report():
    client = TestClient(app)
    payload = {
        "holdings": [
            {"ticker": "NVDA", "weight": 0.5},
            {"ticker": "TLT", "weight": 0.3},
            {"ticker": "GLD", "weight": 0.2}
        ],
        "price_history": {
            "NVDA": [100, 104, 102, 110, 108, 112],
            "TLT": [90, 89, 88, 87, 89, 88],
            "GLD": [180, 181, 183, 182, 184, 185]
        }
    }

    response = client.post("/analyze", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["risk_score"] >= 0
    assert data["metrics"]["volatility"] > 0
    assert data["correlations"]["NVDA"]["TLT"] is not None
    assert data["stress_tests"]
    assert data["data_source"]["type"] == "inline"
    assert any("Annualized volatility" in step for step in data["methodology"])
    assert data["report_markdown"].startswith("# Portfolio Risk Copilot Report")


def test_api_analyze_fetches_live_prices_when_inline_prices_are_omitted(monkeypatch):
    client = TestClient(app)

    from app.market_data import MarketDataResult

    def fake_fetch_price_history(tickers, period):
        assert tickers == ["NVDA", "TLT", "GLD"]
        assert period == "1y"
        return MarketDataResult(
            prices={
                "NVDA": [100, 104, 102, 110, 108, 112],
                "TLT": [90, 89, 88, 87, 89, 88],
                "GLD": [180, 181, 183, 182, 184, 185],
            },
            warnings=["Served market data from a short-lived in-memory cache."],
        )

    monkeypatch.setattr("app.main.fetch_price_history_with_metadata", fake_fetch_price_history)
    payload = {
        "lookback_period": "1y",
        "holdings": [
            {"ticker": "NVDA", "weight": 0.5},
            {"ticker": "TLT", "weight": 0.3},
            {"ticker": "GLD", "weight": 0.2},
        ],
    }

    response = client.post("/analyze", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["data_source"]["type"] == "live"
    assert data["data_source"]["provider"] == "yfinance"
    assert data["data_source"]["lookback_period"] == "1y"
    assert data["data_source"]["tickers"] == ["NVDA", "TLT", "GLD"]
    assert data["data_source"]["price_points"] == {"NVDA": 6, "TLT": 6, "GLD": 6}
    assert data["data_source"]["warnings"] == ["Served market data from a short-lived in-memory cache."]
    assert any("Fetched adjusted close prices from yfinance" in step for step in data["methodology"])
    assert any("Market-data warning" in step for step in data["methodology"])


def test_api_uses_structured_error_detail_for_analysis_errors():
    client = TestClient(app)
    response = client.post(
        "/analyze",
        json={
            "holdings": [{"ticker": "AAA", "weight": 1.0}],
            "price_history": {"AAA": [100, 101]},
        },
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["code"] == "market_data_validation_failed"
    assert detail["retryable"] is False
