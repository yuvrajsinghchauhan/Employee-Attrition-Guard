"""
modules/report_generator.py
-----------------------------
Turns the scored dataframe into outputs a human actually wants:
    * A console summary (counts by risk band, department hot-spots)
    * A full CSV export (every employee + score + reasons + actions)
    * A high-risk-only CSV export for line managers to action this week
    * A model-sanity validation check against historical 'left' outcomes
    * Two PNG charts: risk distribution, and average risk by department
"""

import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import config as cfg


def print_console_summary(scored_df: pd.DataFrame, top_n: int = cfg.DEFAULT_TOP_N) -> None:
    print("\n" + "=" * 70)
    print("ATTRITION EARLY-WARNING SUMMARY")
    print("=" * 70)

    total = len(scored_df)
    band_counts = scored_df["risk_band"].value_counts().reindex(["High", "Medium", "Low"], fill_value=0)
    print(f"Total employees scored: {total}\n")
    for band in ["High", "Medium", "Low"]:
        count = band_counts[band]
        pct = 100 * count / total if total else 0
        print(f"  {band:<7} risk: {count:>5}  ({pct:5.1f}%)")

    print("\nAverage risk score by department:")
    dept_avg = (
        scored_df.groupby("department")["risk_score"]
        .mean()
        .sort_values(ascending=False)
        .round(1)
    )
    for dept, avg in dept_avg.items():
        print(f"  {dept:<15} {avg:5.1f}")

    print(f"\nTop {top_n} highest-risk CURRENT employees (still employed):")
    current = scored_df[scored_df["left"] == 0].sort_values("risk_score", ascending=False)
    cols = ["employee_id", "department", "risk_score", "risk_band", "risk_reasons"]
    top = current[cols].head(top_n)
    with pd.option_context("display.max_colwidth", 60, "display.width", 140):
        print(top.to_string(index=False))
    print("=" * 70 + "\n")


def validate_against_history(scored_df: pd.DataFrame) -> None:
    """
    Sanity-check the rule-based score against actual historical attrition
    ('left' column). This is NOT used to compute the score itself (that
    would be circular/leaky for currently-employed staff) — it's purely a
    transparency check to show the rules track real-world outcomes.
    """
    left_mean = scored_df.loc[scored_df["left"] == 1, "risk_score"].mean()
    stayed_mean = scored_df.loc[scored_df["left"] == 0, "risk_score"].mean()
    corr = scored_df["risk_score"].corr(scored_df["left"])

    print("MODEL SANITY CHECK (rule score vs. historical outcomes)")
    print("-" * 70)
    print(f"  Avg risk score - employees who LEFT   : {left_mean:5.1f}")
    print(f"  Avg risk score - employees who STAYED : {stayed_mean:5.1f}")
    print(f"  Point-biserial correlation (score vs left): {corr:5.2f}")
    print("-" * 70 + "\n")


def export_reports(scored_df: pd.DataFrame, output_dir: str) -> dict:
    """Write full + high-risk-only CSV reports. Returns dict of file paths written."""
    os.makedirs(output_dir, exist_ok=True)

    full_cols = [
        "employee_id", "department", "salary", "tenure", "satisfaction_level",
        "last_evaluation", "number_project", "average_monthly_hours",
        "promotion_last_5years", "left", "risk_score", "risk_band", "risk_reasons",
    ]
    high_risk_cols = full_cols + ["recommended_interventions"]

    # Full report: every employee, score + short reason labels (kept lean).
    full_path = os.path.join(output_dir, "attrition_risk_full_report.csv")
    scored_df[full_cols].to_csv(full_path, index=False)

    # High-risk action list: currently-employed High band only, with the
    # full recommended intervention text included (this is the report a
    # manager actually reads end-to-end, so verbosity here is fine).
    high_risk = scored_df[(scored_df["risk_band"] == "High") & (scored_df["left"] == 0)]
    high_risk_path = os.path.join(output_dir, "high_risk_current_employees.csv")
    high_risk.sort_values("risk_score", ascending=False)[high_risk_cols].to_csv(high_risk_path, index=False)

    return {"full_report": full_path, "high_risk_report": high_risk_path}


def generate_charts(scored_df: pd.DataFrame, output_dir: str) -> dict:
    """Save two PNG charts: risk score distribution, and avg risk by department."""
    os.makedirs(output_dir, exist_ok=True)
    paths = {}

    # Chart 1: risk score distribution by band
    fig, ax = plt.subplots(figsize=(7, 5))
    band_order = ["Low", "Medium", "High"]
    colors = {"Low": "#4CAF50", "Medium": "#FFC107", "High": "#E53935"}
    scored_df["risk_band"].value_counts().reindex(band_order).plot(
        kind="bar", ax=ax, color=[colors[b] for b in band_order]
    )
    ax.set_title("Employee Count by Attrition Risk Band")
    ax.set_xlabel("Risk Band")
    ax.set_ylabel("Number of Employees")
    plt.tight_layout()
    dist_path = os.path.join(output_dir, "risk_distribution.png")
    fig.savefig(dist_path, dpi=150)
    plt.close(fig)
    paths["risk_distribution"] = dist_path

    # Chart 2: average risk score by department
    fig, ax = plt.subplots(figsize=(9, 5))
    dept_avg = scored_df.groupby("department")["risk_score"].mean().sort_values(ascending=False)
    dept_avg.plot(kind="bar", ax=ax, color="#3F51B5")
    ax.set_title("Average Attrition Risk Score by Department")
    ax.set_xlabel("Department")
    ax.set_ylabel("Average Risk Score")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    dept_path = os.path.join(output_dir, "risk_by_department.png")
    fig.savefig(dept_path, dpi=150)
    plt.close(fig)
    paths["risk_by_department"] = dept_path

    return paths
