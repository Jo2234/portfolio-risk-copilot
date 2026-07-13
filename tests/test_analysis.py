
from app.analysis import analyze_concentration, infer_theme_exposures
import pytest
from pydantic import ValidationError

from app.schemas import Holding, PortfolioRequest


def test_concentration_flags_top_holding_top_three_and_theme_exposure():
    req = PortfolioRequest(holdings=[
        Holding(ticker="NVDA", weight=0.30),
        Holding(ticker="MSFT", weight=0.20),
        Holding(ticker="AAPL", weight=0.15),
        Holding(ticker="TLT", weight=0.15),
        Holding(ticker="GLD", weight=0.10),
        Holding(ticker="XLE", weight=0.10),
    ])

    exposures = infer_theme_exposures(req.holdings)
    result = analyze_concentration(req.holdings, exposures)

    assert result.top_holding_weight == 0.30
    assert result.top_three_weight == 0.65
    assert result.largest_holding_ticker == "NVDA"
    assert result.herfindahl_index == pytest.approx(sum(h.weight**2 for h in req.holdings))
    assert result.number_of_positions == 6
    assert any("Top 3" in flag for flag in result.flags)
    assert exposures["ai_mega_cap_tech"] >= 0.65


def test_portfolio_request_rejects_duplicate_tickers_after_normalization():
    with pytest.raises(ValidationError, match="duplicate holdings are not allowed: NVDA"):
        PortfolioRequest(
            holdings=[
                Holding(ticker="nvda", weight=0.5),
                Holding(ticker="NVDA", weight=0.5),
            ]
        )
