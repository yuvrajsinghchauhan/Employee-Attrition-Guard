"""
AttritionGuard - Employee Attrition Early-Warning & Retention Intelligence
-------------------------------------------------------------------------
A Streamlit presentation layer over the project's transparent, rule-based
risk scoring engine. The app is intentionally organized as a decision-
support workflow rather than a single long dashboard:

    Overview -> Risk Explorer -> Employee Profile -> Risk Personas
    -> Retention Actions -> Methodology

Run with:
    streamlit run app.py
or:
    python app.py
"""

import os
import sys
import tempfile
from typing import Dict, List

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import config as cfg
from modules.clustering import COMPONENT_COLUMNS, cluster_at_risk_employees
from modules.data_loader import load_employee_data
from modules.recommendations import FACTOR_LABELS, add_recommendations, recommend_for_factors
from modules.risk_scoring import score_dataframe

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Resolve the project folder from this file, not from the user's current working directory.
# This makes `python app.py` (including VS Code's Run Python File button) work from any location.
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
DEFAULT_CSV = os.path.join(SCRIPT_DIR, "HR_dataset.csv")

BAND_COLORS = {"Low": "#2ECC71", "Medium": "#F1C40F", "High": "#E74C3C"}
BAND_ORDER = ["High", "Medium", "Low"]
FACTOR_ORDER = list(cfg.WEIGHTS.keys())

DEPARTMENT_LABELS = {
    "accounting": "Accounting",
    "hr": "HR",
    "it": "IT",
    "management": "Management",
    "marketing": "Marketing",
    "product_mng": "Product Management",
    "randd": "R&D",
    "sales": "Sales",
    "support": "Support",
    "technical": "Technical",
}

def department_label(value: str) -> str:
    key = str(value).strip().lower()
    return DEPARTMENT_LABELS.get(key, key.replace("_", " ").title())

st.set_page_config(
    page_title="AttritionGuard | HR Risk Intelligence",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------
def inject_css() -> None:
    st.markdown(
        """
        <style>
        :root { --ag-accent: #ff4b4b; }
        .block-container { padding-top: 1.9rem; padding-bottom: 2.5rem; max-width: 1500px; }
        [data-testid="stSidebar"] { border-right: 1px solid rgba(255,255,255,.08); }
        [data-testid="stSidebar"] h1 { margin-top: .35rem; margin-bottom: .1rem; letter-spacing: -.02em; }
        [data-testid="stSidebar"] [data-testid="stRadio"] { margin-top: .15rem; }
        [data-testid="stMetric"] {
            background: rgba(255,255,255,.035);
            border: 1px solid rgba(255,255,255,.08);
            padding: 1rem 1rem .85rem;
            border-radius: 14px;
        }
        .ag-hero {
            background: linear-gradient(135deg, rgba(255,75,75,.18), rgba(60,65,85,.12));
            border: 1px solid rgba(255,255,255,.08);
            border-radius: 18px;
            padding: 1.45rem 1.55rem 1.35rem;
            margin: .35rem 0 1.1rem;
            overflow: visible;
        }
        .ag-eyebrow {
            color: #ff8a8a;
            font-size: .78rem;
            font-weight: 800;
            line-height: 1.35;
            letter-spacing: .11em;
            text-transform: uppercase;
            margin: 0 0 .35rem;
            padding-top: .05rem;
        }
        .ag-title { font-size: 2rem; font-weight: 800; line-height: 1.15; margin: 0; }
        .ag-subtitle { color: rgba(255,255,255,.68); margin-top: .35rem; }
        .ag-section-title { font-size: 1.25rem; font-weight: 750; margin-top: .4rem; }
        .ag-card {
            background: rgba(255,255,255,.025);
            border: 1px solid rgba(255,255,255,.08);
            border-radius: 16px;
            padding: 1rem 1.1rem;
            height: 100%;
        }
        .ag-risk-high { color: #ff6b6b; font-weight: 800; }
        .ag-risk-medium { color: #ffd166; font-weight: 800; }
        .ag-risk-low { color: #67e8a0; font-weight: 800; }
        .ag-muted { color: rgba(255,255,255,.62); font-size: .9rem; }
        .ag-pill {
            display: inline-block;
            padding: .23rem .55rem;
            border-radius: 999px;
            font-size: .75rem;
            font-weight: 700;
            background: rgba(255,75,75,.12);
            border: 1px solid rgba(255,75,75,.25);
            margin-right: .35rem;
            margin-bottom: .25rem;
        }
        .ag-action {
            border-left: 3px solid #ff4b4b;
            background: rgba(255,255,255,.025);
            padding: .75rem .9rem;
            margin: .55rem 0;
            border-radius: 0 10px 10px 0;
        }
        .ag-small { font-size: .82rem; color: rgba(255,255,255,.62); }
        .ag-footer { color: rgba(255,255,255,.45); font-size: .78rem; padding-top: .4rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_and_score(csv_bytes: bytes, filename: str) -> pd.DataFrame:
    safe_name = os.path.basename(filename) or "uploaded.csv"
    tmp_path = os.path.join(tempfile.gettempdir(), f"attritionguard_{safe_name}")
    with open(tmp_path, "wb") as f:
        f.write(csv_bytes)
    df = load_employee_data(tmp_path)
    scored = score_dataframe(df)
    return add_recommendations(scored)


def get_csv_bytes(uploaded_file) -> tuple:
    if uploaded_file is not None:
        return uploaded_file.getvalue(), uploaded_file.name
    with open(DEFAULT_CSV, "rb") as f:
        return f.read(), "HR_dataset.csv"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def apply_filters(
    scored_df: pd.DataFrame,
    selected_depts: List[str],
    bands: List[str],
    only_current: bool,
) -> pd.DataFrame:
    result = scored_df[
        scored_df["department"].isin(selected_depts)
        & scored_df["risk_band"].isin(bands)
    ].copy()
    if only_current:
        result = result[result["left"] == 0]
    return result


def risk_class(band: str) -> str:
    return {"High": "ag-risk-high", "Medium": "ag-risk-medium", "Low": "ag-risk-low"}.get(
        band, "ag-risk-low"
    )


def top_factor_counts(df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    counts: Dict[str, int] = {k: 0 for k in FACTOR_LABELS}
    for factors in df["top_risk_factors"]:
        for factor in factors:
            counts[factor] = counts.get(factor, 0) + 1
    rows = [
        {"factor": factor, "label": FACTOR_LABELS.get(factor, factor), "employees": count}
        for factor, count in counts.items()
        if count > 0
    ]
    return pd.DataFrame(rows).sort_values("employees", ascending=False).head(n)


def action_queue_df(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate actionable employees into a risk-driver action queue.

    Priority is driven by the volume of High-risk employees sharing the warning sign.
    A driver affecting 50 or more High-risk employees is marked HIGH; drivers
    affecting fewer than 50 High-risk employees are marked MEDIUM. This keeps
    both urgency and breadth visible instead of making every driver HIGH.
    """
    rows = []
    for factor, label in FACTOR_LABELS.items():
        subset = df[df["top_risk_factors"].apply(lambda x: factor in x)]
        if subset.empty:
            continue
        high_count = int((subset["risk_band"] == "High").sum())
        medium_count = int((subset["risk_band"] == "Medium").sum())
        rows.append(
            {
                "Priority": "HIGH" if high_count >= 50 else "MEDIUM",
                "Employees": len(subset),
                "High risk employees": high_count,
                "Medium risk employees": medium_count,
                "Main concern": label,
                "Average risk": round(subset["risk_score"].mean(), 1),
                "Suggested next step": recommend_for_factors([factor])[0],
            }
        )
    if not rows:
        return pd.DataFrame(columns=[
            "Priority", "Employees", "High risk employees", "Medium risk employees",
            "Main concern", "Average risk", "Suggested next step"
        ])
    out = pd.DataFrame(rows)
    priority_order = pd.CategoricalDtype(["HIGH", "MEDIUM"], ordered=True)
    out["Priority"] = out["Priority"].astype(priority_order)
    return out.sort_values(["Priority", "High risk employees", "Employees"], ascending=[True, False, False]).reset_index(drop=True)


def risk_band_chart(df: pd.DataFrame):
    counts = df["risk_band"].value_counts().reindex(BAND_ORDER, fill_value=0)
    fig = px.bar(
        x=counts.index,
        y=counts.values,
        color=counts.index,
        color_discrete_map=BAND_COLORS,
        labels={"x": "Risk level", "y": "Employees"},
    )
    fig.update_layout(
        showlegend=False,
        margin=dict(l=10, r=10, t=10, b=10),
        height=330,
    )
    return fig


def department_chart(df: pd.DataFrame):
    # Keep the dataset's internal department keys unchanged for scoring/filtering,
    # but always use business-friendly names for presentation.
    dept = (
        df.groupby("department", dropna=False)["risk_score"]
        .mean()
        .sort_values(ascending=True)
        .rename("Average Risk Score")
        .reset_index()
    )
    dept["Department"] = dept["department"].map(department_label)

    fig = px.bar(
        dept,
        x="Average Risk Score",
        y="Department",
        orientation="h",
        labels={
            "Average Risk Score": "Average Risk Score",
            "Department": "Department",
        },
        color="Average Risk Score",
        color_continuous_scale="Reds",
        hover_data={"Average Risk Score": ":.1f", "department": False},
    )
    display_order = dept["Department"].tolist()
    fig.update_layout(
        title=None,
        coloraxis_showscale=False,
        margin=dict(l=10, r=10, t=10, b=10),
        height=360,
    )
    # Explicit tick text prevents Plotly from falling back to the raw dataset
    # keys such as product_mng / randd / hr.
    fig.update_yaxes(
        categoryorder="array",
        categoryarray=display_order,
        tickmode="array",
        tickvals=display_order,
        ticktext=display_order,
        automargin=True,
    )
    return fig


def factor_chart(df: pd.DataFrame):
    top = top_factor_counts(df, 7).sort_values("employees")
    fig = px.bar(
        top,
        x="employees",
        y="label",
        orientation="h",
        labels={"employees": "Employees", "label": "Risk driver"},
    )
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=360)
    return fig


def render_header(title: str, subtitle: str, eyebrow: str = "ATTRITION GUARD") -> None:
    st.markdown(
        f"""
        <div class="ag-hero">
            <div class="ag-eyebrow">{eyebrow}</div>
            <div class="ag-title">{title}</div>
            <div class="ag-subtitle">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_risk_badge(band: str) -> None:
    st.markdown(f"<span class='{risk_class(band)}'>{band.upper()} RISK</span>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Presentation helpers
# ---------------------------------------------------------------------------
def employee_display_table(df: pd.DataFrame, *, include_actions: bool = False, height: int = 520) -> pd.DataFrame:
    """Build a consistent, readable employee table for every page."""
    cols = [
        "employee_id", "department", "salary", "tenure",
        "satisfaction_level", "average_monthly_hours", "risk_score",
        "risk_band", "risk_reasons",
    ]
    if include_actions:
        cols.append("recommended_interventions")

    table = df[cols].sort_values("risk_score", ascending=False).copy()
    table["department"] = table["department"].apply(department_label)
    table["risk_reasons"] = table["risk_reasons"].apply(
        lambda x: ", ".join(x) if isinstance(x, list) and x else "No material risk drivers detected"
    )
    if include_actions:
        table["recommended_interventions"] = table["recommended_interventions"].apply(
            lambda x: " | ".join(x) if isinstance(x, list) else str(x)
        )
    return table


def render_employee_table(df: pd.DataFrame, *, include_actions: bool = False, height: int = 520, key_prefix: str = "table") -> pd.DataFrame:
    """Render a common employee table and return the display dataframe."""
    table = employee_display_table(df, include_actions=include_actions, height=height)
    config = {
        "employee_id": "Employee",
        "department": "Department",
        "salary": "Salary",
        "tenure": "Tenure (years)",
        "risk_score": st.column_config.ProgressColumn("Risk score", min_value=0, max_value=100, format="%.0f"),
        "risk_band": "Risk level",
        "satisfaction_level": st.column_config.NumberColumn("Satisfaction", format="%.2f"),
        "average_monthly_hours": st.column_config.NumberColumn("Monthly working hours", format="%.0f"),
        "risk_reasons": st.column_config.TextColumn("Warning signs", width="large"),
    }
    if include_actions:
        config["recommended_interventions"] = st.column_config.TextColumn("Suggested next step", width="large")
    st.dataframe(
        table,
        use_container_width=True,
        height=height,
        hide_index=True,
        column_config=config,
        key=f"{key_prefix}_dataframe",
    )
    return table


def page_overview(df: pd.DataFrame, scored_df: pd.DataFrame) -> None:
    render_header(
        "Employee Attrition Early-Warning System",
        "See who may need support, understand what is driving the risk, and decide what to do next.",
    )

    total = len(df)
    high = int((df["risk_band"] == "High").sum())
    medium = int((df["risk_band"] == "Medium").sum())
    low = int((df["risk_band"] == "Low").sum())
    avg = float(df["risk_score"].mean()) if total else 0
    high_pct = (high / total * 100) if total else 0

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Employees in view", f"{total:,}")
    k2.metric("High risk", f"{high:,}", f"{high_pct:.1f}% of view")
    k3.metric("Medium risk", f"{medium:,}")
    k4.metric("Low risk", f"{low:,}")
    k5.metric("Avg. risk score", f"{avg:.1f}/100")

    st.markdown("### What needs a closer look?")
    high_df = df[df["risk_band"] == "High"].sort_values("risk_score", ascending=False)
    top_reason = top_factor_counts(high_df if not high_df.empty else df, 4)

    c1, c2 = st.columns([1.1, 1.2])
    with c1:
        st.plotly_chart(risk_band_chart(df), use_container_width=True)
    with c2:
        if high_df.empty:
            st.info("No high-risk employees are present under the current filters.")
        else:
            st.markdown("**Current priority group**")
            st.markdown(
                f"<div class='ag-card'><div style='font-size:1.55rem;font-weight:800'>{len(high_df):,} high-risk employees</div>"
                f"<div class='ag-muted'>The highest scores should be reviewed first. The most common risk drivers in this group are:</div></div>",
                unsafe_allow_html=True,
            )
            st.write("")
            for _, r in top_reason.iterrows():
                st.markdown(f"**{r['label']}** — {int(r['employees']):,} employees")

    st.markdown("### Where risk is highest")
    c3, c4 = st.columns([1.15, 1])
    with c3:
        st.plotly_chart(department_chart(df), use_container_width=True)
    with c4:
        st.plotly_chart(factor_chart(df), use_container_width=True)

    st.markdown("### Employees to review first")
    if high_df.empty:
        st.info("No high-risk employees match the current view.")
        return
    queue_cols = [
        "employee_id", "department", "risk_score", "risk_band", "salary",
        "tenure", "satisfaction_level", "average_monthly_hours", "risk_reasons",
    ]
    queue = high_df[queue_cols].head(10).copy()
    queue["risk_reasons"] = queue["risk_reasons"].apply(
        lambda x: ", ".join(x[:2]) if x else "No material risk drivers detected"
    )
    st.dataframe(
        queue,
        use_container_width=True,
        hide_index=True,
        column_config={
            "employee_id": "Employee",
            "risk_score": st.column_config.ProgressColumn("Risk score", min_value=0, max_value=100, format="%.0f"),
            "risk_band": "Band",
            "satisfaction_level": st.column_config.NumberColumn("Satisfaction", format="%.2f"),
            "average_monthly_hours": st.column_config.NumberColumn("Monthly working hours", format="%.0f"),
            "risk_reasons": "Main warning signs",
        },
    )

    st.markdown(
        f"<div class='ag-footer'>Dataset currently contains {len(scored_df):,} analyzed employee records after the loader's duplicate-handling step.</div>",
        unsafe_allow_html=True,
    )


def page_risk_explorer(df: pd.DataFrame) -> None:
    render_header(
        "Risk Explorer",
        "Look closer at the patterns behind employee risk and see how the different factors relate to each other.",
        eyebrow="ANALYTICS",
    )

    if df.empty:
        st.warning("No employees match the current filters.")
        return

    top_left, top_right = st.columns([1.1, 1])
    with top_left:
        st.markdown("### Risk by department")
        st.plotly_chart(department_chart(df), use_container_width=True)
    with top_right:
        st.markdown("### Most common warning signs")
        st.plotly_chart(factor_chart(df), use_container_width=True)

    st.markdown("### Employee risk overview")
    table = render_employee_table(df, height=460, key_prefix="risk_explorer")
    st.download_button(
        "Download this filtered list (CSV)",
        data=table.to_csv(index=False).encode("utf-8"),
        file_name="attritionguard_filtered_employees.csv",
        mime="text/csv",
    )

    st.caption("Warning signs are shown only when a defined threshold is crossed. That keeps low-risk employees from being flagged for small score contributions that are not meaningful on their own.")

    st.markdown("### Explore a relationship")
    # User-facing labels are deliberately decoupled from raw CSV column names.
    # The raw names remain internal so the scoring engine continues to work unchanged.
    x_col_map = {
        "Working Hours": "average_monthly_hours",
        "Number of Projects": "number_project",
        "Tenure (Years)": "tenure",
        "Last Evaluation": "last_evaluation",
    }
    y_col_map = {
        "Satisfaction": "satisfaction_level",
        "Working Hours": "average_monthly_hours",
        "Number of Projects": "number_project",
        "Tenure (Years)": "tenure",
        "Last Evaluation": "last_evaluation",
    }
    c1, c2 = st.columns([.8, .8])
    with c1:
        x_label = st.selectbox("X-axis", list(x_col_map), index=0)
    with c2:
        y_label = st.selectbox("Y-axis", list(y_col_map), index=0)
    fig = px.scatter(
        df,
        x=x_col_map[x_label],
        y=y_col_map[y_label],
        color="risk_band",
        size="risk_score",
        color_discrete_map=BAND_COLORS,
        hover_data=["employee_id", "department", "salary", "tenure", "risk_score"],
        labels={
            x_col_map[x_label]: x_label,
            y_col_map[y_label]: y_label,
            "risk_band": "Risk Band",
            "risk_score": "Risk Score",
            "department": "Department",
            "employee_id": "Employee",
        },
        opacity=.55,
    )
    fig.update_layout(
        height=480,
        margin=dict(l=10, r=10, t=10, b=10),
        legend_title_text="Risk Band",
    )
    st.plotly_chart(fig, use_container_width=True)


def page_employee_profile(df: pd.DataFrame) -> None:
    render_header(
        "Employee Profile",
        "Take a closer look at one employee, understand the warning signs, and see what could help.",
        eyebrow="CASE REVIEW",
    )
    if df.empty:
        st.warning("No employees match the current filters.")
        return

    ordered_ids = df.sort_values("risk_score", ascending=False)["employee_id"].tolist()
    selected = st.selectbox("Select employee", ordered_ids)
    row = df[df["employee_id"] == selected].iloc[0]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Risk score", f"{row['risk_score']:.0f}/100")
    c2.metric("Risk level", row["risk_band"])
    c3.metric("Satisfaction", f"{row['satisfaction_level']:.2f}")
    c4.metric("Monthly working hours", f"{row['average_monthly_hours']:.0f}")

    left, right = st.columns([1, 1.35])
    with left:
        st.markdown("### About this employee")
        st.markdown(
            f"""
            <div class='ag-card'>
            <b>Department</b><br>{department_label(row['department'])}<br><br>
            <b>Salary band</b><br>{str(row['salary']).title()}<br><br>
            <b>Tenure</b><br>{row['tenure']} years<br><br>
            <b>Projects</b><br>{row['number_project']}<br><br>
            <b>Last evaluation</b><br>{row['last_evaluation']:.2f}<br><br>
            <b>Promotion in last 5 years</b><br>{'Yes' if row['promotion_last_5years'] == 1 else 'No'}
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("### Warning signs")
        for factor in row["top_risk_factors"]:
            score_col = f"component_{factor}"
            score = float(row[score_col])
            st.progress(min(score / cfg.WEIGHTS[factor], 1.0), text=f"{FACTOR_LABELS[factor]} — {score:.1f} points")

    with right:
        st.markdown("### What is driving the score?")
        if row["top_risk_factors"]:
            st.markdown(
                "<div class='ag-card'><div class='ag-muted'>The score is driven by the following factors, ranked by their contribution:</div>"
                + "".join([f"<p><b>{i}. {FACTOR_LABELS[f]}</b></p>" for i, f in enumerate(row["top_risk_factors"], 1)])
                + "</div>",
                unsafe_allow_html=True,
            )
        else:
            st.info("Nothing stands out as a meaningful risk signal for this employee.")

        st.markdown("### What could help")
        for action in row["recommended_interventions"]:
            st.markdown(f"<div class='ag-action'>{action}</div>", unsafe_allow_html=True)

    st.markdown("### How the score is built")
    factor_rows = []
    for comp in COMPONENT_COLUMNS:
        key = comp.replace("component_", "")
        factor_rows.append({"Factor": FACTOR_LABELS[key], "Points": float(row[comp])})
    contrib = pd.DataFrame(factor_rows).sort_values("Points")
    fig = px.bar(contrib, x="Points", y="Factor", orientation="h", labels={"Points": "Risk points"})
    fig.update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)



def page_personas(scored_df: pd.DataFrame, selected_depts: List[str], only_current: bool) -> None:
    render_header(
        "Risk Groups",
        "Group employees with similar warning signs so one thoughtful retention plan can support many people.",
        eyebrow="RETENTION INTELLIGENCE",
    )

    c1, c2 = st.columns([.65, 1.35])
    with c1:
        n_clusters = st.slider("Number of groups", 2, 6, 4)
    with c2:
        min_band = st.selectbox("Include employees from", ["Medium", "High"], index=0)

    cluster_source = scored_df[scored_df["department"].isin(selected_depts)]
    clustered_df, profiles = cluster_at_risk_employees(
        cluster_source,
        n_clusters=n_clusters,
        min_band=min_band,
        currently_employed_only=only_current,
    )

    if not profiles:
        st.info("There are not enough employees in the current view to create meaningful groups.")
        return

    summary = pd.DataFrame(
        [
            {
                "Persona": p.persona_name,
                "Employees": p.size,
                "Average risk": p.avg_risk_score,
                "Dominant drivers": ", ".join(p.top_factors),
            }
            for p in profiles
        ]
    )
    st.dataframe(summary, use_container_width=True, hide_index=True)

    tabs = st.tabs([f"{p.persona_name} ({p.size})" for p in profiles])
    for tab, profile in zip(tabs, profiles):
        with tab:
            left, right = st.columns([.95, 1.2])
            with left:
                st.metric("Employees in persona", f"{profile.size:,}")
                st.metric("Average risk score", f"{profile.avg_risk_score:.1f}/100")
                st.markdown("**Dominant risk factors**")
                for f in profile.top_factors:
                    st.markdown(f"• {f}")
            with right:
                st.markdown("**Recommended group strategy**")
                for action in profile.recommended_strategy:
                    st.markdown(f"<div class='ag-action'>{action}</div>", unsafe_allow_html=True)

            members = clustered_df[clustered_df["cluster_id"] == profile.cluster_id].copy()
            with st.expander(f"View all employees in this persona ({profile.size})"):
                members_table = render_employee_table(members, height=500, key_prefix=f"persona_{profile.cluster_id}")
                st.download_button(
                    "Download persona employee table (CSV)",
                    data=members_table.to_csv(index=False).encode("utf-8"),
                    file_name=f"attritionguard_persona_{profile.cluster_id}_employees.csv",
                    mime="text/csv",
                    key=f"persona_{profile.cluster_id}_download",
                )



def build_retention_plan(row: pd.Series, position: int = 0) -> str:
    """Create a concise, varied retention plan from an employee's actual risk signals."""
    factors = list(row.get("top_risk_factors", []) or [])
    plans = {
        "satisfaction": [
            "Start with a confidential stay interview to understand what is making the employee unhappy and agree on practical changes.",
            "Have a candid manager check-in focused on the biggest source of frustration, then act on the clearest issue.",
            "Use a focused engagement check-in to uncover the main concern and turn it into a short, visible action plan.",
        ],
        "workload": [
            "Review project allocation and rebalance the workload so responsibilities are challenging without becoming overwhelming.",
            "Clarify priorities, remove low-value work where possible, and make sure the workload matches the employee's capacity.",
            "Reset the project mix with the manager and consider a better-fit assignment or additional support.",
        ],
        "hours": [
            "Review recent working hours, reset healthy boundaries, and rebalance work where sustained overwork is visible.",
            "Discuss workload versus available capacity and encourage healthier working patterns, including time off where appropriate.",
            "Look at the cause of unusually long or low hours and adjust staffing, priorities, or schedules accordingly.",
        ],
        "tenure_zone": [
            "Set up a career conversation covering the next role, new responsibilities, and what growth could look like over the next 6–12 months.",
            "Explore a stretch assignment, mentoring opportunity, or internal move to keep the employee's next step visible.",
            "Refresh the employee's development plan and create a concrete next milestone rather than leaving growth open-ended.",
        ],
        "promotion": [
            "Be explicit about promotion expectations, timing, and the skills or outcomes needed for the next step.",
            "Create a visible growth plan with project ownership, mentoring, training, or another development opportunity.",
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
    companion = {
        "satisfaction": "Keep the follow-up close so the employee can see that their feedback led to action.",
        "workload": "Set a simple follow-up date to check whether the workload feels sustainable.",
        "hours": "Revisit the working pattern after a few weeks to make sure the change is holding.",
        "tenure_zone": "Put the next development milestone on the calendar so progress is visible.",
        "promotion": "Document the agreed milestones and review them at the next 1:1.",
        "salary": "Be clear about what can change now and what the employee can expect later.",
        "burnout_flight_risk": "Check back quickly rather than treating the conversation as a one-time intervention.",
    }
    if not factors:
        return "Keep a regular check-in rhythm and continue monitoring engagement."
    primary = factors[0]
    options = plans.get(primary, [])
    recommendation = options[position % len(options)] if options else "Discuss the main concern with the employee and agree on a practical next step."
    if len(factors) > 1:
        secondary = factors[1]
        secondary_options = plans.get(secondary, [])
        if secondary_options:
            # Add a shorter, relevant second action so employees with multiple
            # warning signs get a more tailored plan without a wall of text.
            secondary_text = secondary_options[(position + 1) % len(secondary_options)]
            recommendation += " " + secondary_text + " " + companion.get(secondary, "Follow up on the change at the next 1:1.")
    return recommendation


def retention_table(df: pd.DataFrame) -> pd.DataFrame:
    """Build a complete, readable table for every employee needing attention."""
    source_cols = [
        "employee_id", "department", "salary", "tenure", "satisfaction_level",
        "last_evaluation", "number_project", "average_monthly_hours",
        "work_accident", "promotion_last_5years", "left",
        "risk_score", "risk_band", "risk_reasons"
    ]

    missing = [c for c in source_cols if c not in df.columns]
    if missing:
        raise ValueError(
            "The employee table could not be built because these expected fields "
            f"are missing after data loading: {', '.join(missing)}"
        )

    table = df.loc[:, source_cols].copy()
    table = table.sort_values(
        ["risk_band", "risk_score"],
        key=lambda col: col.map({"High": 0, "Medium": 1, "Low": 2})
        if col.name == "risk_band" else col,
        ascending=[True, False],
    )

    table["Retention plan"] = [
        build_retention_plan(row, i) for i, (_, row) in enumerate(table.iterrows())
    ]
    table["department"] = table["department"].apply(department_label)
    table["salary"] = table["salary"].astype(str).str.title()
    table["work_accident"] = table["work_accident"].map({1: "Yes", 0: "No"}).fillna(table["work_accident"].astype(str))
    table["promotion_last_5years"] = table["promotion_last_5years"].map({1: "Yes", 0: "No"}).fillna(table["promotion_last_5years"].astype(str))
    table["left"] = table["left"].map({1: "Yes", 0: "No"}).fillna(table["left"].astype(str))
    table["risk_reasons"] = table["risk_reasons"].apply(
        lambda x: ", ".join(x) if isinstance(x, list) and x else "No material risk drivers detected"
    )

    return table.rename(columns={
        "employee_id": "Employee",
        "department": "Department",
        "salary": "Salary band",
        "tenure": "Tenure (years)",
        "satisfaction_level": "Satisfaction",
        "last_evaluation": "Last evaluation",
        "number_project": "Number of projects",
        "average_monthly_hours": "Monthly working hours",
        "work_accident": "Work accident",
        "promotion_last_5years": "Promotion in last 5 years",
        "left": "Past attrition",
        "risk_score": "Risk score",
        "risk_band": "Risk level",
        "risk_reasons": "Warning signs",
    })


def page_retention_actions(df: pd.DataFrame) -> None:
    render_header(
        "Retention Action Center",
        "Turn warning signs into practical next steps, with the people who need attention all in one place.",
        eyebrow="ACTION",
    )

    at_risk = df[df["risk_band"].isin(["High", "Medium"])].copy()
    if at_risk.empty:
        st.info("There are no medium- or high-risk employees in the current view.")
        return

    high = int((at_risk["risk_band"] == "High").sum())
    medium = int((at_risk["risk_band"] == "Medium").sum())
    c1, c2, c3 = st.columns(3)
    c1.metric("Employees needing attention", f"{len(at_risk):,}")
    c2.metric("High priority", f"{high:,}")
    c3.metric("Medium priority", f"{medium:,}")

    st.markdown("### Priorities by warning sign")
    st.caption("HIGH means the warning sign is shared by 50 or more high-risk employees; MEDIUM means it affects fewer than 50 high-risk employees. Counts can overlap because one employee can have several warning signs.")
    aq = action_queue_df(at_risk)
    st.dataframe(
        aq,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Priority": "Priority",
            "Employees": st.column_config.NumberColumn("Employees", format="%d"),
            "High risk employees": st.column_config.NumberColumn("High risk", format="%d"),
            "Medium risk employees": st.column_config.NumberColumn("Medium risk", format="%d"),
            "Average risk": st.column_config.NumberColumn("Average risk", format="%.1f"),
            "Suggested next step": st.column_config.TextColumn("Suggested next step", width="large"),
        },
    )

    st.markdown("### All employees who need attention")
    st.caption("Every medium- and high-risk employee is shown below, with the available HR data and a retention approach tailored to the warning signs behind the score.")
    table = retention_table(at_risk)
    st.caption(f"Showing all {len(table):,} medium- and high-risk employees in the current view. Scroll horizontally to see every field.")
    st.dataframe(
        table,
        use_container_width=True,
        height=780,
        hide_index=True,
        column_config={
            "Employee": "Employee",
            "Department": "Department",
            "Salary band": "Salary band",
            "Tenure (years)": st.column_config.NumberColumn("Tenure (years)", format="%d"),
            "Satisfaction": st.column_config.NumberColumn("Satisfaction", format="%.2f"),
            "Last evaluation": st.column_config.NumberColumn("Last evaluation", format="%.2f"),
            "Number of projects": st.column_config.NumberColumn("Number of projects", format="%d"),
            "Monthly working hours": st.column_config.NumberColumn("Monthly working hours", format="%d"),
            "Work accident": "Work accident",
            "Promotion in last 5 years": "Promotion in last 5 years",
            "Past attrition": "Past attrition",
            "Risk score": st.column_config.ProgressColumn("Risk score", min_value=0, max_value=100, format="%.0f"),
            "Warning signs": st.column_config.TextColumn("Warning signs", width="large"),
            "Retention plan": st.column_config.TextColumn("Retention approach", width="large"),
        },
        key="actions_all_employees_dataframe",
    )

    st.download_button(
        "Download the full retention list (CSV)",
        data=table.to_csv(index=False).encode("utf-8"),
        file_name="attritionguard_all_employees_needing_attention.csv",
        mime="text/csv",
        key="actions_all_employees_download",
    )


def page_methodology(scored_df: pd.DataFrame) -> None:
    render_header(
        "Methodology & Model Transparency",
        "Here is how the score is built, what each factor contributes, and where the risk bands come from.",
        eyebrow="GOVERNANCE",
    )

    st.markdown("### How the risk score works")
    weights = pd.DataFrame(
        [
            {
                "Factor": FACTOR_LABELS[key],
                "Weight": cfg.WEIGHTS[key],
                "Maximum points": cfg.WEIGHTS[key],
            }
            for key in FACTOR_ORDER
        ]
    )
    st.dataframe(weights, use_container_width=True, hide_index=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("High risk threshold", f"≥ {cfg.RISK_BAND_HIGH_MIN}")
    c2.metric("Medium risk threshold", f"≥ {cfg.RISK_BAND_MEDIUM_MIN}")
    c3.metric("Maximum score", "100")

    st.markdown("### Risk levels")
    st.markdown(
        "🔴 **High:** score ≥ 65 &nbsp;&nbsp; | &nbsp;&nbsp; "
        "🟡 **Medium:** 35–64 &nbsp;&nbsp; | &nbsp;&nbsp; "
        "🟢 **Low:** < 35"
    )

    st.markdown("### What the rules look at")
    st.markdown(
        f"""
        **Satisfaction:** inverse linear risk across the 0–1 satisfaction scale.<br>
        **Workload:** 3–4 projects is treated as the optimal zone; very low or very high project loads increase risk.<br>
        **Working hours:** 150–240 hours/month is the healthy band; risk increases below/above it.<br>
        **Tenure:** years 4–5 are the highest-risk tenure zone, with a smaller penalty across years 3–6.<br>
        **Promotion:** no promotion in the last 5 years creates a larger penalty once tenure is meaningful.<br>
        **Compensation:** low and medium pay bands carry progressively larger risk contributions.<br>
        **Silent burnout:** a full component triggers only for high evaluation + high hours + low satisfaction.<br>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### A quick check against past attrition")
    validation = scored_df.groupby("left")["risk_score"].agg(["count", "mean"]).rename(index={0: "Stayed", 1: "Left"})
    st.dataframe(validation, use_container_width=True)
    st.caption(
        "The historical `left` field is used only as a check against past outcomes. "
        "It is kept out of the score itself, so the warning remains independent of the outcome we are trying to understand."
    )

    st.markdown("### A note about the data")
    st.info(
        "The provided HR dataset includes satisfaction, evaluation, project load, working hours, tenure, "
        "work accidents, promotion history, department, salary and past attrition. The score is built "
        "only from the fields that are actually available in the dataset."
    )


def page_data_quality(df: pd.DataFrame) -> None:
    pass


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    inject_css()

    # Sidebar branding
    st.sidebar.markdown("# 🛡️ Attrition Guard")
    st.sidebar.caption("Spot risk • Understand why • Take action")

    # Navigation stays at the top because it is used throughout the application.
    page = st.sidebar.radio(
        "Go to",
        [
            "Overview",
            "Risk Explorer",
            "Employee Profile",
            "Risk Groups",
            "Retention Actions",
            "How it works",
        ],
        index=0,
    )

    csv_bytes, csv_name = get_csv_bytes(None)
    scored_df = load_and_score(csv_bytes, csv_name)

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Filters")
    departments = sorted(scored_df["department"].dropna().unique().tolist())
    department_options = {department_label(d): d for d in departments}
    selected_department_labels = st.sidebar.multiselect("Department", list(department_options.keys()), default=list(department_options.keys()))
    selected_depts = [department_options[d] for d in selected_department_labels]
    bands = st.sidebar.multiselect("Risk level", BAND_ORDER, default=BAND_ORDER)
    only_current = st.sidebar.checkbox("Currently employed", value=True)

    view_df = apply_filters(scored_df, selected_depts, bands, only_current)

    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**{len(view_df):,}** employees in this view")

    if page == "Overview":
        page_overview(view_df, scored_df)
    elif page == "Risk Explorer":
        page_risk_explorer(view_df)
    elif page == "Employee Profile":
        page_employee_profile(view_df)
    elif page == "Risk Groups":
        page_personas(scored_df, selected_depts, only_current)
    elif page == "Retention Actions":
        page_retention_actions(view_df)
    elif page == "How it works":
        page_methodology(scored_df)

    st.markdown("---")
    st.markdown(
        "<div class='ag-footer'>Rule-based early-warning utility • Transparent scoring • Local Streamlit app • See RULES_AND_METHODOLOGY.md for the documented rule set.</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    # This block makes the normal VS Code "Run Python File" button launch
    # Streamlit automatically. We use the same Python interpreter that VS Code
    # selected, so the installed environment and package versions stay aligned.
    from streamlit import runtime

    if runtime.exists():
        main()
    else:
        import socket
        import subprocess
        import time
        import webbrowser

        app_path = os.path.abspath(__file__)
        host = "localhost"
        port = "8501"

        # Run Streamlit as a module instead of relying on a global `streamlit`
        # command. The project directory is used as the working directory so
        # relative imports and bundled files are resolved consistently.
        cmd = [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            app_path,
            "--server.address",
            host,
            "--server.port",
            port,
            "--server.headless",
            "true",
            "--browser.gatherUsageStats",
            "false",
        ]

        process = subprocess.Popen(cmd, cwd=SCRIPT_DIR)

        # Wait briefly for Streamlit to start, then open the app automatically.
        # This is deliberately best-effort: Streamlit will still be reachable
        # at http://localhost:8501 if the browser cannot be opened automatically.
        for _ in range(40):
            if process.poll() is not None:
                sys.exit(process.returncode or 1)
            try:
                with socket.create_connection((host, int(port)), timeout=0.25):
                    break
            except OSError:
                time.sleep(0.25)
        webbrowser.open(f"http://{host}:{port}")
        sys.exit(process.wait())
