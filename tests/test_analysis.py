
from app.analysis import analyze_concentration, infer_theme_exposures
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
    assert any("Top 3" in flag for flag in result.flags)
    assert exposures["ai_mega_cap_tech"] >= 0.65
