
import pytest

from app.analysis import infer_theme_exposures
from app.copilot import build_copilot_report
from app.schemas import ConcentrationAnalysis, Holding, RiskContribution, RiskMetrics, StressScenarioResult
from app.stress import run_stress_tests


def test_stress_tests_return_named_scenarios_with_estimated_impacts():
    holdings = [Holding(ticker="NVDA", weight=0.5), Holding(ticker="TLT", weight=0.3), Holding(ticker="GLD", weight=0.2)]
    exposures = {"ai_mega_cap_tech": 0.5, "long_duration_bonds": 0.3, "gold_defensive": 0.2}

    results = run_stress_tests(holdings, exposures)

    names = {r.scenario for r in results}
    assert "AI capex sentiment reverses" in names
    assert "Rates rise sharply" in names
    assert "Regional banking stress" in names
    assert all(-1.0 < r.estimated_impact < 1.0 for r in results)


def test_regional_banking_stress_shocks_financial_and_small_cap_exposures():
    holdings = [
        Holding(ticker="JPM", weight=0.5),
        Holding(ticker="IWM", weight=0.3),
        Holding(ticker="TLT", weight=0.2),
    ]

    result = next(
        row
        for row in run_stress_tests(holdings, infer_theme_exposures(holdings))
        if row.scenario == "Regional banking stress"
    )

    assert result.estimated_impact == pytest.approx(-0.127)
    assert "financials 50%" in result.rationale


def test_copilot_report_turns_metrics_flags_and_stress_into_plain_english():
    metrics = RiskMetrics(volatility=0.18, value_at_risk_95=-0.025, expected_shortfall_95=-0.041, max_drawdown=-0.22, sharpe_ratio=0.8, sortino_ratio=1.1)
    concentration = ConcentrationAnalysis(largest_holding_ticker="NVDA", top_holding_weight=0.3, top_three_weight=0.65, top_five_weight=0.9, herfindahl_index=0.238, number_of_positions=6, effective_number_of_positions=4.2, flags=["Top 3 holdings make up 65% of the portfolio"])
    stress = [StressScenarioResult(scenario="AI capex sentiment reverses", estimated_impact=-0.14, rationale="High AI mega-cap exposure")]

    contributions = [RiskContribution(ticker="NVDA", weight=0.3, risk_contribution_pct=0.55, annualized_volatility=0.3)]
    report = build_copilot_report(metrics, concentration, stress, {"ai_mega_cap_tech": 0.65}, contributions)

    assert "Risk score" in report.summary
    assert "Top 3 holdings" in report.report_markdown
    assert "AI capex sentiment reverses" in report.report_markdown
    assert "NVDA is the largest estimated variance contributor" in report.summary
    assert report.risk_score >= 0
