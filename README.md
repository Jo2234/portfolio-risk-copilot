# Portfolio Risk Copilot

API-first portfolio risk copilot for serious portfolio analysis. It accepts holdings, fetches or receives price history, calculates risk metrics, detects concentration and theme exposures, runs scenario stress tests, and returns a plain-English investment risk memo.

> Built as a polished Option A finance/AI engineering project: professional, testable, API-first, and product-like.

## Features

- **Portfolio risk metrics**: annualized volatility, daily 95% VaR, daily 95% expected shortfall, max drawdown, Sharpe-like ratio
- **Concentration analysis**: largest holding, top-three weight, effective number of positions, concentration flags
- **Correlation map**: pairwise holding correlations from return history
- **Theme exposure detection**: AI mega-cap tech, semiconductors, long-duration bonds, gold, broad US equity, crypto proxy, energy/oil
- **Stress tests**: rates spike, AI capex reversal, recession risk-off, USD/liquidity squeeze, oil shock
- **Plain-English copilot report**: markdown memo with summary, flags, stress tests, and suggestions
- **FastAPI backend** with `/analyze` and `/health`
- **Demo UI** at `/`
- **CI + tests** for core behavior

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000> or call the API directly.

## Example request

```bash
curl -X POST http://127.0.0.1:8000/analyze \
  -H 'Content-Type: application/json' \
  -d '{
    "holdings": [
      {"ticker": "NVDA", "weight": 0.50},
      {"ticker": "TLT", "weight": 0.30},
      {"ticker": "GLD", "weight": 0.20}
    ],
    "price_history": {
      "NVDA": [100, 104, 102, 110, 108, 112],
      "TLT": [90, 89, 88, 87, 89, 88],
      "GLD": [180, 181, 183, 182, 184, 185]
    }
  }'
```

If `price_history` is omitted, the app fetches prices with `yfinance` using the supplied tickers and `lookback_period`.

## Response shape

```json
{
  "summary": "Risk score 74/100...",
  "risk_score": 74,
  "metrics": {
    "volatility": 0.18,
    "value_at_risk_95": -0.025,
    "expected_shortfall_95": -0.041,
    "max_drawdown": -0.22,
    "sharpe_ratio": 0.8
  },
  "concentration": {
    "top_holding_weight": 0.5,
    "top_three_weight": 1.0,
    "effective_number_of_positions": 2.63,
    "flags": ["Largest holding is 50%, above a typical 25% single-name risk guardrail"]
  },
  "theme_exposures": {"ai_mega_cap_tech": 0.5, "long_duration_bonds": 0.3, "gold_defensive": 0.2},
  "correlations": {"NVDA": {"NVDA": 1.0, "TLT": -0.4}},
  "stress_tests": [{"scenario": "AI capex sentiment reverses", "estimated_impact": -0.11, "rationale": "..."}],
  "suggestions": ["Reduce top-three concentration or add assets with genuinely different drivers."],
  "report_markdown": "# Portfolio Risk Copilot Report..."
}
```

## Why this project exists

Most portfolio dashboards show numbers without interpretation. Portfolio Risk Copilot keeps the calculations transparent while converting them into a concise risk memo that a human investor can actually act on.

## Development

```bash
pytest -q
```

## Disclaimer

Educational software only. Not financial advice.
