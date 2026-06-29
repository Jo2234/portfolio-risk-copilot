
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
    assert data["report_markdown"].startswith("# Portfolio Risk Copilot Report")
