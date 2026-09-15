"""
modules/risk_scoring.py
------------------------
The core rule engine. Calculates an explainable Attrition Risk Score
(0-100) for every employee, plus a breakdown of which factors drove
the score so recommendations can be targeted rather than generic.

Every rule here is intentionally simple and transparent (as opposed to
a black-box ML model) because the brief for this utility is an
*early-warning* tool that line managers and HR need to trust and be
able to explain to an employee in a stay-interview. The rules are
calibrated using the exploratory findings from the accompanying
capstone analysis (Salifort_Motors_Project.ipynb), e.g.:
    - Satisfaction is the single strongest signal of the people who left.
    - Employees with 7 projects left 100% of the time.
    - Attrition and low satisfaction cluster heavily around tenure 3-6,
      spiking at year 4.
    - A distinct cluster of high-evaluation, heavily overworked, low-
      satisfaction employees left despite being top performers.

See config.py for every threshold/weight, and RULES_AND_METHODOLOGY.md
for the full write-up intended for the submission deck.
"""

from dataclasses import dataclass, field
from typing import Dict, List

import pandas as pd

import config as cfg


@dataclass
class RiskBreakdown:
    """Holds the per-factor score contribution for one employee."""
    scores: Dict[str, float] = field(default_factory=dict)

    @property
    def total(self) -> float:
        return round(sum(self.scores.values()), 2)

    def top_factors(self, n: int = 3) -> List[str]:
        """Return top factors with meaningful, business-visible triggers.

        A mathematically positive component is not automatically shown as a
        "risk driver". For example, a satisfaction score of 0.96 produces a
        small positive contribution under the inverse-linear scoring rule, but
        it would be misleading to label that employee as having "low job
        satisfaction". The trigger rules below keep the explanation layer
        aligned with the business interpretation of the score.
        """
        nonzero = {k: v for k, v in self.scores.items() if v > 0}
        ranked = sorted(nonzero.items(), key=lambda kv: kv[1], reverse=True)
        return [k for k, _ in ranked[:n]]


def _score_satisfaction(satisfaction_level: float) -> float:
    """Lower satisfaction -> linearly higher risk. Weight: 30."""
    satisfaction_level = min(max(satisfaction_level, 0.0), 1.0)
    return round((1 - satisfaction_level) * cfg.WEIGHTS["satisfaction"], 2)


def _score_workload(number_project: int) -> float:
    """U-shaped risk: too few or too many projects both raise risk. Weight: 15."""
    w = cfg.WEIGHTS["workload"]
    if number_project >= cfg.WORKLOAD_OVERLOAD_MIN:
        return w                      # severe overload
    if number_project <= cfg.WORKLOAD_UNDERLOAD_MAX:
        return w                      # disengagement / underutilization
    if cfg.WORKLOAD_OPTIMAL_MIN <= number_project <= cfg.WORKLOAD_OPTIMAL_MAX:
        return 0.0                    # optimal zone
    if number_project <= cfg.WORKLOAD_ELEVATED_MAX:
        return round(w * (8 / 15), 2)  # mild overload (5-6 projects)
    return 0.0


def _score_hours(average_monthly_hours: float) -> float:
    """Overwork or underwork both raise risk, scaled linearly. Weight: 15."""
    w = cfg.WEIGHTS["hours"]
    if average_monthly_hours > cfg.HOURS_NORMAL_MAX:
        span = cfg.HOURS_OVERWORK_CEILING - cfg.HOURS_NORMAL_MAX
        over = min(average_monthly_hours - cfg.HOURS_NORMAL_MAX, span)
        return round((over / span) * w, 2)
    if average_monthly_hours < cfg.HOURS_UNDERWORK_MAX:
        under = cfg.HOURS_UNDERWORK_MAX - average_monthly_hours
        # scale relative to a 60hr "fully disengaged" gap, capped at weight
        return round(min(under / 60, 1.0) * w, 2)
    return 0.0


def _score_tenure_zone(tenure: int) -> float:
    """Danger-zone tenure years. Weight: 10."""
    w = cfg.WEIGHTS["tenure_zone"]
    if tenure in cfg.TENURE_HIGH_RISK_YEARS:
        return w
    lo, hi = cfg.TENURE_MEDIUM_RISK_RANGE
    if lo <= tenure <= hi:
        return round(w * 0.6, 2)
    return 0.0


def _score_promotion(promotion_last_5years: int, tenure: int) -> float:
    """No promotion, especially with meaningful tenure, raises risk. Weight: 10."""
    w = cfg.WEIGHTS["promotion"]
    if promotion_last_5years == 1:
        return 0.0
    return w if tenure >= 3 else round(w * 0.4, 2)


def _score_salary(salary: str) -> float:
    """Lower pay band raises risk. Weight: 10."""
    w = cfg.WEIGHTS["salary"]
    band = {"low": 1.0, "medium": 0.5, "high": 0.0}
    return round(band.get(salary, 0.5) * w, 2)


def _score_burnout_flight_risk(last_evaluation: float, average_monthly_hours: float,
                                satisfaction_level: float) -> float:
    """High performer + overworked + unhappy = classic silent flight risk. Weight: 10."""
    w = cfg.WEIGHTS["burnout_flight_risk"]
    if (last_evaluation >= cfg.BURNOUT_EVAL_MIN and
            average_monthly_hours > cfg.BURNOUT_HOURS_MIN and
            satisfaction_level < cfg.BURNOUT_SATISFACTION_MAX):
        return w
    return 0.0


def material_risk_factors(row: pd.Series) -> List[str]:
    """Return only risk factors that are genuinely triggered by the row.

    This is deliberately separate from the numeric score contribution. The
    score can contain small partial contributions for calibration purposes,
    while the explanation shown to HR should only name an issue when a
    recognizable business threshold is crossed.
    """
    factors: List[str] = []

    satisfaction = float(row["satisfaction_level"])
    projects = int(row["number_project"])
    hours = float(row["average_monthly_hours"])
    tenure = int(row["tenure"])
    promotion = int(row["promotion_last_5years"])
    salary = str(row["salary"]).strip().lower()
    evaluation = float(row["last_evaluation"])

    if satisfaction < 0.60:
        factors.append("satisfaction")

    if projects <= cfg.WORKLOAD_UNDERLOAD_MAX or projects >= 5:
        factors.append("workload")

    if hours < cfg.HOURS_UNDERWORK_MAX or hours > 260:
        factors.append("hours")

    lo, hi = cfg.TENURE_MEDIUM_RISK_RANGE
    if lo <= tenure <= hi:
        factors.append("tenure_zone")

    if promotion == 0 and tenure >= 3:
        factors.append("promotion")

    if salary == "low":
        factors.append("salary")

    if (evaluation >= cfg.BURNOUT_EVAL_MIN and
            hours > cfg.BURNOUT_HOURS_MIN and
            satisfaction < cfg.BURNOUT_SATISFACTION_MAX):
        factors.append("burnout_flight_risk")

    return factors


def score_employee(row: pd.Series) -> RiskBreakdown:
    """Compute the full risk breakdown for a single employee record."""
    breakdown = RiskBreakdown(scores={
        "satisfaction": _score_satisfaction(row["satisfaction_level"]),
        "workload": _score_workload(row["number_project"]),
        "hours": _score_hours(row["average_monthly_hours"]),
        "tenure_zone": _score_tenure_zone(row["tenure"]),
        "promotion": _score_promotion(row["promotion_last_5years"], row["tenure"]),
        "salary": _score_salary(row["salary"]),
        "burnout_flight_risk": _score_burnout_flight_risk(
            row["last_evaluation"], row["average_monthly_hours"], row["satisfaction_level"]
        ),
    })
    return breakdown


def risk_band(score: float) -> str:
    if score >= cfg.RISK_BAND_HIGH_MIN:
        return "High"
    if score >= cfg.RISK_BAND_MEDIUM_MIN:
        return "Medium"
    return "Low"


def score_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply the rule engine to every row of the employee dataframe.

    Returns a copy of df with added columns:
        risk_score, risk_band, top_risk_factors (list[str])
    plus one column per individual rule component for transparency.
    """
    result = df.copy()
    breakdowns = df.apply(score_employee, axis=1)

    result["risk_score"] = breakdowns.apply(lambda b: b.total)
    result["risk_band"] = result["risk_score"].apply(risk_band)

    # Explanation layer: rank only the business-triggered factors. For a
    # genuinely low-risk employee, this can correctly be an empty list even
    # though the numerical score has several small positive components.
    material = df.apply(material_risk_factors, axis=1)
    result["top_risk_factors"] = [
        [] if result.iloc[i]["risk_band"] == "Low" else sorted(
            factors,
            key=lambda f: breakdowns.iloc[i].scores.get(f, 0.0),
            reverse=True,
        )[:3]
        for i, factors in enumerate(material)
    ]

    # Medium/high cases should still have an interpretable explanation if no
    # hard trigger was crossed; fall back to the largest positive components.
    for i in result.index:
        if result.at[i, "risk_band"] in {"Medium", "High"} and not result.at[i, "top_risk_factors"]:
            result.at[i, "top_risk_factors"] = [
                f for f, v in sorted(
                    breakdowns.iloc[i].scores.items(),
                    key=lambda kv: kv[1],
                    reverse=True,
                ) if v > 0
            ][:3]

    # Expose each component score as its own column for auditability
    component_names = list(cfg.WEIGHTS.keys())
    for comp in component_names:
        result[f"component_{comp}"] = breakdowns.apply(lambda b: b.scores[comp])

    return result
