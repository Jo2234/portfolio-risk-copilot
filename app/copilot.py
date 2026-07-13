
from __future__ import annotations

from typing import Dict, List

from app.schemas import ConcentrationAnalysis, CopilotReport, RiskContribution, RiskMetrics, StressScenarioResult


def compute_risk_score(metrics: RiskMetrics, concentration: ConcentrationAnalysis, stress_tests: List[StressScenarioResult]) -> int:
    score = 35
    score += min(30, max(0, int(metrics.volatility * 100)))
    score += min(15, max(0, int(abs(metrics.max_drawdown) * 50)))
    score += min(15, max(0, int(concentration.top_three_weight * 15)))
    worst_stress = abs(min((s.estimated_impact for s in stress_tests), default=0.0))
    score += min(20, int(worst_stress * 100))
    if metrics.sharpe_ratio > 1:
        score -= 8
    elif metrics.sharpe_ratio < 0:
        score += 8
    return max(0, min(100, score))


def build_suggestions(metrics: RiskMetrics, concentration: ConcentrationAnalysis, theme_exposures: Dict[str, float], stress_tests: List[StressScenarioResult]) -> List[str]:
    suggestions: list[str] = []
    if concentration.top_holding_weight >= 0.25:
        suggestions.append("Set a max single-position limit or trim the largest holding before adding more risk.")
    if concentration.top_three_weight >= 0.60:
        suggestions.append("Reduce top-three concentration or add assets with genuinely different drivers.")
    if theme_exposures.get("ai_mega_cap_tech", 0) >= 0.45:
        suggestions.append("Separate AI-theme conviction from total portfolio risk by capping AI mega-cap exposure.")
    if theme_exposures.get("long_duration_bonds", 0) >= 0.25:
        suggestions.append("Check duration exposure; rate spikes can hurt bonds and growth equities at the same time.")
    worst = min(stress_tests, key=lambda s: s.estimated_impact, default=None)
    if worst and worst.estimated_impact < -0.10:
        suggestions.append(f"Run a position-level plan for the worst scenario: {worst.scenario}.")
    if metrics.volatility >= 0.20:
        suggestions.append("Consider adding lower-volatility or lower-correlation assets if drawdown control matters.")
    if not suggestions:
        suggestions.append("Risk looks reasonably balanced; monitor correlations and rebalance on drift.")
    return suggestions


def build_copilot_report(
    metrics: RiskMetrics,
    concentration: ConcentrationAnalysis,
    stress_tests: List[StressScenarioResult],
    theme_exposures: Dict[str, float],
    risk_contributions: List[RiskContribution] | None = None,
) -> CopilotReport:
    risk_score = compute_risk_score(metrics, concentration, stress_tests)
    worst = min(stress_tests, key=lambda s: s.estimated_impact, default=None)
    top_theme = max(theme_exposures.items(), key=lambda kv: kv[1], default=("unmapped", 0.0))
    top_risk = risk_contributions[0] if risk_contributions else None
    risk_driver = f" {top_risk.ticker} is the largest estimated variance contributor." if top_risk else ""
    summary = (
        f"Risk score {risk_score}/100. Annualized volatility is {metrics.volatility:.1%}, "
        f"max drawdown is {metrics.max_drawdown:.1%}, and the largest mapped exposure is "
        f"{top_theme[0].replace('_', ' ')} at {top_theme[1]:.0%}." + risk_driver
    )
    suggestions = build_suggestions(metrics, concentration, theme_exposures, stress_tests)
    stress_lines = "\n".join(f"- **{s.scenario}**: {s.estimated_impact:.1%} estimated impact — {s.rationale}" for s in stress_tests)
    flag_lines = "\n".join(f"- {flag}" for flag in concentration.flags)
    theme_lines = "\n".join(f"- {theme.replace('_', ' ').title()}: {weight:.0%}" for theme, weight in theme_exposures.items())
    suggestion_lines = "\n".join(f"- {s}" for s in suggestions)
    markdown = f"""# Portfolio Risk Copilot Report

## Executive Summary
{summary}

## Key Metrics
- Annualized volatility: **{metrics.volatility:.1%}**
- Daily 95% VaR: **{metrics.value_at_risk_95:.2%}**
- Daily 95% expected shortfall: **{metrics.expected_shortfall_95:.2%}**
- Max drawdown: **{metrics.max_drawdown:.1%}**
- Sharpe-like ratio: **{metrics.sharpe_ratio:.2f}**
- Sortino-like ratio: **{metrics.sortino_ratio:.2f}**

## Concentration Flags
{flag_lines}

## Theme Exposures
{theme_lines}

## Stress Tests
{stress_lines}

## Suggestions
{suggestion_lines}
"""
    return CopilotReport(risk_score=risk_score, summary=summary, suggestions=suggestions, report_markdown=markdown)
