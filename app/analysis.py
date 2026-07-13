
from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List

from app.schemas import ConcentrationAnalysis, Holding

THEME_MAP = {
    "ai_mega_cap_tech": {"NVDA", "MSFT", "AAPL", "GOOGL", "GOOG", "META", "AMZN", "TSLA", "AMD", "AVGO", "SMCI"},
    "semiconductors": {"NVDA", "AMD", "AVGO", "TSM", "ASML", "INTC", "QCOM", "MU", "SMCI"},
    "long_duration_bonds": {"TLT", "EDV", "IEF", "ZROZ"},
    "gold_defensive": {"GLD", "IAU", "SGOL", "GDX"},
    "broad_us_equity": {"SPY", "VOO", "IVV", "VTI", "QQQ", "DIA", "IWM"},
    "crypto_proxy": {"BTC", "ETH", "COIN", "MSTR", "IBIT", "FBTC", "ETHE"},
    "energy_oil": {"XLE", "USO", "XOM", "CVX", "OXY", "COP"},
    "financials": {"JPM", "BAC", "WFC", "C", "GS", "MS", "KRE", "XLF", "SCHW"},
    "small_cap_equity": {"IWM", "VTWO", "VB", "SCHA"},
}


def infer_theme_exposures(holdings: Iterable[Holding]) -> Dict[str, float]:
    exposures = defaultdict(float)
    for holding in holdings:
        matched = False
        for theme, tickers in THEME_MAP.items():
            if holding.ticker in tickers:
                exposures[theme] += holding.weight
                matched = True
        if not matched:
            exposures["idiosyncratic_or_unmapped"] += holding.weight
    return {theme: round(weight, 6) for theme, weight in sorted(exposures.items())}


def analyze_concentration(holdings: List[Holding], theme_exposures: Dict[str, float]) -> ConcentrationAnalysis:
    ordered = sorted(holdings, key=lambda h: h.weight, reverse=True)
    top_holding = ordered[0].weight
    top_three = sum(h.weight for h in ordered[:3])
    effective_n = 1 / sum(h.weight ** 2 for h in holdings)
    flags: list[str] = []

    if top_holding >= 0.25:
        flags.append(f"Largest holding is {top_holding:.0%}, above a typical 25% single-name risk guardrail")
    if top_three >= 0.60:
        flags.append(f"Top 3 holdings make up {top_three:.0%} of the portfolio")
    if effective_n < 5:
        flags.append(f"Effective diversification is only {effective_n:.1f} equally weighted positions")
    for theme, weight in theme_exposures.items():
        if weight >= 0.50 and theme != "idiosyncratic_or_unmapped":
            flags.append(f"{theme.replace('_', ' ').title()} exposure is {weight:.0%}")
    if not flags:
        flags.append("No major concentration flags detected")

    return ConcentrationAnalysis(
        largest_holding_ticker=ordered[0].ticker,
        top_holding_weight=round(top_holding, 6),
        top_three_weight=round(top_three, 6),
        top_five_weight=round(sum(h.weight for h in ordered[:5]), 6),
        herfindahl_index=round(sum(h.weight ** 2 for h in holdings), 6),
        number_of_positions=len(holdings),
        effective_number_of_positions=round(effective_n, 2),
        flags=flags,
    )
