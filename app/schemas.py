
from __future__ import annotations

from typing import Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class Holding(BaseModel):
    ticker: str = Field(..., min_length=1, examples=["NVDA"])
    weight: float = Field(..., gt=0, le=1, examples=[0.25])

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        return value.strip().upper()


class PortfolioRequest(BaseModel):
    holdings: List[Holding] = Field(..., min_length=1)
    lookback_period: str = Field("2y", description="Period passed to yfinance when price_history is omitted")
    price_history: Optional[Dict[str, List[float]]] = Field(None, description="Optional inline prices for deterministic analysis")
    risk_free_rate: float = 0.0

    @model_validator(mode="after")
    def validate_weights(self):
        total = sum(h.weight for h in self.holdings)
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"holding weights must sum to 1.0; got {total:.4f}")
        return self


class RiskMetrics(BaseModel):
    volatility: float
    value_at_risk_95: float
    expected_shortfall_95: float
    max_drawdown: float
    sharpe_ratio: float


class ConcentrationAnalysis(BaseModel):
    top_holding_weight: float
    top_three_weight: float
    effective_number_of_positions: float
    flags: List[str]


class StressScenarioResult(BaseModel):
    scenario: str
    estimated_impact: float
    rationale: str


class CopilotReport(BaseModel):
    risk_score: int
    summary: str
    suggestions: List[str]
    report_markdown: str


class DataSource(BaseModel):
    type: str
    provider: str
    lookback_period: str
    tickers: List[str]
    price_points: Dict[str, int]


class PortfolioResponse(BaseModel):
    summary: str
    risk_score: int
    metrics: RiskMetrics
    concentration: ConcentrationAnalysis
    theme_exposures: Dict[str, float]
    correlations: Dict[str, Dict[str, float]]
    stress_tests: List[StressScenarioResult]
    suggestions: List[str]
    methodology: List[str]
    data_source: DataSource
    report_markdown: str
