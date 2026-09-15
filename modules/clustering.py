"""
modules/clustering.py
-----------------------
Groups at-risk employees who share a similar *reason profile* into a small
number of "risk personas", so HR can act on a handful of common strategies
instead of reading 100+ individual reports one by one.

Approach
--------
Every employee already has 7 interpretable component scores from
risk_scoring.py (satisfaction, workload, hours, tenure_zone, promotion,
salary, burnout_flight_risk). Rather than clustering on the raw HR
features (which would be less interpretable), we cluster directly on
these component scores using K-Means. This means each resulting cluster
centroid is immediately readable as "this group's risk mostly comes from
X and Y" — no reverse-engineering required.

Only employees who are (a) still employed and (b) at least Medium risk
are clustered — Low-risk employees don't need a targeted strategy.
"""

from dataclasses import dataclass
from typing import List

import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from modules.recommendations import FACTOR_LABELS, recommend_for_factors

COMPONENT_COLUMNS = [
    "component_satisfaction", "component_workload", "component_hours",
    "component_tenure_zone", "component_promotion", "component_salary",
    "component_burnout_flight_risk",
]

SHORT_PERSONA_LABELS = {
    "component_satisfaction": "Disengaged / Unhappy",
    "component_workload": "Workload Imbalance",
    "component_hours": "Overworked",
    "component_tenure_zone": "Tenure Plateau",
    "component_promotion": "Stalled Growth",
    "component_salary": "Underpaid",
    "component_burnout_flight_risk": "Burnt-Out High Performer",
}


@dataclass
class ClusterProfile:
    cluster_id: int
    persona_name: str
    size: int
    avg_risk_score: float
    top_factors: List[str]          # internal component_* names
    recommended_strategy: List[str]


def cluster_at_risk_employees(
    scored_df: pd.DataFrame,
    n_clusters: int = 4,
    min_band: str = "Medium",
    currently_employed_only: bool = True,
    random_state: int = 42,
):
    """
    Cluster at-risk employees into shared risk personas.

    Returns
    -------
    (assigned_df, profiles)
        assigned_df : subset of scored_df (the clustered population) with an
                       added 'cluster_id' and 'persona_name' column.
        profiles    : list[ClusterProfile], one per cluster, ready to render.
    """
    band_rank = {"Low": 0, "Medium": 1, "High": 2}
    subset = scored_df[scored_df["risk_band"].map(band_rank) >= band_rank[min_band]].copy()
    if currently_employed_only:
        subset = subset[subset["left"] == 0]

    if len(subset) < n_clusters:
        # Not enough at-risk employees to form the requested number of
        # clusters — fall back to a single group rather than erroring.
        n_clusters = max(1, min(n_clusters, len(subset)))
    if len(subset) == 0:
        return subset, []

    X = subset[COMPONENT_COLUMNS].values
    X_scaled = StandardScaler().fit_transform(X)

    km = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=10)
    subset["cluster_id"] = km.fit_predict(X_scaled)

    profiles = []
    persona_names = {}
    for cid in sorted(subset["cluster_id"].unique()):
        members = subset[subset["cluster_id"] == cid]
        mean_components = members[COMPONENT_COLUMNS].mean().sort_values(ascending=False)
        top_cols = [c for c in mean_components.index[:2] if mean_components[c] > 0]
        if not top_cols:
            top_cols = [mean_components.index[0]]

        persona_name = " & ".join(SHORT_PERSONA_LABELS[c] for c in top_cols)
        persona_names[cid] = persona_name

        internal_factor_names = [c.replace("component_", "") for c in top_cols]
        strategy = recommend_for_factors(internal_factor_names)

        profiles.append(ClusterProfile(
            cluster_id=int(cid),
            persona_name=persona_name,
            size=len(members),
            avg_risk_score=round(members["risk_score"].mean(), 1),
            top_factors=[FACTOR_LABELS[f] for f in internal_factor_names],
            recommended_strategy=strategy,
        ))

    subset["persona_name"] = subset["cluster_id"].map(persona_names)
    profiles.sort(key=lambda p: p.avg_risk_score, reverse=True)

    return subset, profiles
