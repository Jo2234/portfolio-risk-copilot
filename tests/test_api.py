
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

    def fake_fetch_price_history(tickers, period):
        assert tickers == ["NVDA", "TLT", "GLD"]
        assert period == "1y"
        return {
            "NVDA": [100, 104, 102, 110, 108, 112],
            "TLT": [90, 89, 88, 87, 89, 88],
            "GLD": [180, 181, 183, 182, 184, 185],
        }

    monkeypatch.setattr("app.main.fetch_price_history", fake_fetch_price_history)
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
    assert data["data_source"] == {"type": "live", "provider": "yfinance", "lookback_period": "1y", "tickers": ["NVDA", "TLT", "GLD"], "price_points": {"NVDA": 6, "TLT": 6, "GLD": 6}}
    assert any("Fetched adjusted close prices from yfinance" in step for step in data["methodology"])
