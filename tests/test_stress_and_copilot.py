
from app.copilot import build_copilot_report
from app.schemas import ConcentrationAnalysis, Holding, RiskMetrics, StressScenarioResult
from app.stress import run_stress_tests


def test_stress_tests_return_named_scenarios_with_estimated_impacts():
    holdings = [Holding(ticker="NVDA", weight=0.5), Holding(ticker="TLT", weight=0.3), Holding(ticker="GLD", weight=0.2)]
    exposures = {"ai_mega_cap_tech": 0.5, "long_duration_bonds": 0.3, "gold_defensive": 0.2}

    results = run_stress_tests(holdings, exposures)

    names = {r.scenario for r in results}
    assert "AI capex sentiment reverses" in names
    assert "Rates rise sharply" in names
    assert all(-1.0 < r.estimated_impact < 1.0 for r in results)


def test_copilot_report_turns_metrics_flags_and_stress_into_plain_english():
    metrics = RiskMetrics(volatility=0.18, value_at_risk_95=-0.025, expected_shortfall_95=-0.041, max_drawdown=-0.22, sharpe_ratio=0.8)
    concentration = ConcentrationAnalysis(top_holding_weight=0.3, top_three_weight=0.65, effective_number_of_positions=4.2, flags=["Top 3 holdings make up 65% of the portfolio"])
    stress = [StressScenarioResult(scenario="AI capex sentiment reverses", estimated_impact=-0.14, rationale="High AI mega-cap exposure")]

    report = build_copilot_report(metrics, concentration, stress, {"ai_mega_cap_tech": 0.65})

    assert "Risk score" in report.summary
    assert "Top 3 holdings" in report.report_markdown
    assert "AI capex sentiment reverses" in report.report_markdown
    assert report.risk_score >= 0
