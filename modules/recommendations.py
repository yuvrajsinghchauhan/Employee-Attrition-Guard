"""
modules/recommendations.py
----------------------------
Translates *why* an employee scored as high-risk into concrete,
actionable interventions a line manager or HRBP can actually run with.

Each risk factor computed in risk_scoring.py maps to one or more
recommended interventions. An employee's final recommendation list is
built from their top contributing factors, de-duplicated, and ordered
by relevance.
"""

from typing import List
import pandas as pd

INTERVENTIONS = {
    "satisfaction": [
        "Start with a confidential stay interview to understand what is making the employee unhappy and agree on practical changes.",
        "Use a focused engagement check-in or pulse survey to uncover the main source of dissatisfaction.",
        "Create a short action plan with the employee and manager around the biggest day-to-day pain point.",
    ],
    "workload": [
        "Review project allocation and rebalance the workload so responsibilities are challenging without becoming overwhelming.",
        "Clarify priorities, remove low-value work where possible, and make sure responsibilities match the employee's role and capacity.",
        "Explore a better-fit assignment, additional support, or a stretch opportunity depending on the workload pattern.",
    ],
    "hours": [
        "Review recent working hours, reset healthy boundaries, and rebalance work where sustained overwork is visible.",
        "Discuss workload versus available capacity and encourage healthier working patterns, including time off where appropriate.",
        "Look at the cause of unusually long or low hours and adjust staffing, priorities, or schedules where needed.",
    ],
    "tenure_zone": [
        "Set up a career conversation covering the next role, new responsibilities, and what growth could look like over the next 6–12 months.",
        "Explore a stretch assignment, mentoring opportunity, or internal move to keep the employee's next step visible.",
        "Refresh the employee's development plan and create a concrete next milestone for progression.",
    ],
    "promotion": [
        "Be explicit about promotion expectations, timing, and the skills or outcomes needed for the next step.",
        "Create a visible growth plan with ownership of a project, mentoring, training, or another development opportunity.",
        "Agree on a clear review point so the employee is not left with an open-ended promise about progression.",
    ],
    "salary": [
        "Review pay against the role and market, and pair the conversation with recognition or other rewards where a change is not immediate.",
        "Benchmark compensation for the role and explain the path for future pay progression as clearly as possible.",
        "Consider a compensation review alongside recognition, bonus eligibility, flexibility, or development opportunities.",
    ],
    "burnout_flight_risk": [
        "Bring the manager and HR together for a priority retention conversation, then reduce avoidable pressure and recognize recent performance.",
        "Protect the employee from sustained overload while keeping recognition high; strong performance should not depend on endless extra hours.",
        "Use a focused leadership check-in to address burnout signals, workload, recognition, and the employee's longer-term goals.",
    ],
}

FACTOR_LABELS = {
    "satisfaction": "Low job satisfaction",
    "workload": "Workload imbalance (too many or too few projects)",
    "hours": "Unhealthy working hours (over/under-work)",
    "tenure_zone": "In a historically high-attrition tenure window",
    "promotion": "No recent promotion / stalled growth",
    "salary": "Below-market / low compensation band",
    "burnout_flight_risk": "High performer showing silent burnout signs",
}


def recommend_for_factors(top_factors: List[str]) -> List[str]:
    """Build a de-duplicated, ordered list of interventions for the given factors."""
    recs: List[str] = []
    for factor in top_factors:
        for action in INTERVENTIONS.get(factor, []):
            if action not in recs:
                recs.append(action)
    if not recs:
        recs.append("No specific risk drivers detected — continue standard engagement cadence.")
    return recs


def label_factors(top_factors: List[str]) -> List[str]:
    return [FACTOR_LABELS.get(f, f) for f in top_factors]


def add_recommendations(df: pd.DataFrame) -> pd.DataFrame:
    """Add human-readable 'risk_reasons' and 'recommended_interventions' columns."""
    result = df.copy()
    result["risk_reasons"] = result["top_risk_factors"].apply(label_factors)
    result["recommended_interventions"] = result["top_risk_factors"].apply(recommend_for_factors)
    return result
