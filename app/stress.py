
from __future__ import annotations

from typing import Dict, List

from app.schemas import Holding, StressScenarioResult

SCENARIO_SHOCKS = {
    "Rates rise sharply": {
        "long_duration_bonds": -0.18,
        "ai_mega_cap_tech": -0.08,
        "broad_us_equity": -0.06,
        "gold_defensive": -0.03,
        "idiosyncratic_or_unmapped": -0.04,
    },
    "AI capex sentiment reverses": {
        "ai_mega_cap_tech": -0.22,
        "semiconductors": -0.28,
        "broad_us_equity": -0.07,
        "idiosyncratic_or_unmapped": -0.03,
    },
    "Recession risk-off": {
        "broad_us_equity": -0.18,
        "ai_mega_cap_tech": -0.20,
        "semiconductors": -0.24,
        "energy_oil": -0.12,
        "long_duration_bonds": 0.08,
        "gold_defensive": 0.06,
        "idiosyncratic_or_unmapped": -0.10,
    },
    "USD strength and liquidity squeeze": {
        "gold_defensive": -0.07,
        "crypto_proxy": -0.25,
        "broad_us_equity": -0.08,
        "ai_mega_cap_tech": -0.11,
        "idiosyncratic_or_unmapped": -0.05,
    },
    "Oil shock": {
        "energy_oil": 0.16,
        "broad_us_equity": -0.07,
        "ai_mega_cap_tech": -0.09,
        "long_duration_bonds": -0.04,
        "idiosyncratic_or_unmapped": -0.05,
    },
}


def run_stress_tests(holdings: List[Holding], theme_exposures: Dict[str, float]) -> List[StressScenarioResult]:
    results: list[StressScenarioResult] = []
    unmapped = max(0.0, 1.0 - sum(v for k, v in theme_exposures.items() if k != "idiosyncratic_or_unmapped"))
    exposures = dict(theme_exposures)
    exposures.setdefault("idiosyncratic_or_unmapped", unmapped)

    for scenario, shocks in SCENARIO_SHOCKS.items():
        impact = 0.0
        contributors = []
        for theme, exposure in exposures.items():
            shock = shocks.get(theme, 0.0)
            if exposure and shock:
                impact += exposure * shock
                contributors.append(f"{theme.replace('_', ' ')} {exposure:.0%} × {shock:.0%}")
        rationale = "; ".join(contributors) if contributors else "No mapped exposure to this scenario"
        results.append(StressScenarioResult(scenario=scenario, estimated_impact=round(impact, 4), rationale=rationale))
    return sorted(results, key=lambda r: r.estimated_impact)
