# Attrition Early-Warning Utility — Rules & Methodology

This document is written to be lifted directly into the submission slide deck.
It explains **what the utility does, why each rule exists, and how it was
validated** — every rule is transparent and explainable by design, since a
manager needs to be able to justify a stay-interview or a workload change to
an employee, not just point at a black-box score.

## 1. Data Used

Source: `HR_dataset.csv` (14,999 raw rows → 11,991 after removing exact
duplicate records). Columns used:

| Column | Meaning |
|---|---|
| satisfaction_level | Employee-reported satisfaction (0–1) |
| last_evaluation | Score on last performance review (0–1) |
| number_project | Number of projects currently assigned |
| average_montly_hours | Average hours worked per month |
| time_spend_company | Tenure in years |
| Work_accident | Whether employee had a workplace accident (0/1) |
| promotion_last_5years | Promoted in the last 5 years? (0/1) |
| Department, salary | Department and pay band (low/medium/high) |
| left | Historical outcome — did the employee actually leave? |

> Note: the brief's example schema mentions fields like Name, Date of
> Joining, Leave count and Learning Hours. The provided dataset does not
> include these; the rule set below was built entirely from the columns
> that actually exist, so the utility runs on the real data as-is. The
> code is structured (see `config.py`) so any of these additional fields
> could be dropped in as new rule components with minimal changes.

The `left` column (whether an employee has already exited) is **not used to
calculate risk** — that would be circular for people who are still with the
company. It is used only afterward, as a validation check (Section 4).

## 2. Attrition Risk Score — Rule Set (0–100 scale)

The score is a weighted sum of 7 independent, transparent rule components.
Weights were assigned based on patterns found in the exploratory data
analysis (see `Salifort_Motors_Project.ipynb`) and standard HR retention
literature, then tuned so they sum cleanly to 100.

| # | Factor | Weight | Rule |
|---|---|---|---|
| 1 | **Satisfaction level** | 30 | Risk = `(1 − satisfaction_level) × 30`. The single strongest signal in the data — leavers reported far lower satisfaction on average. |
| 2 | **Workload (project count)** | 15 | U-shaped: 3–4 projects = 0 risk (optimal). ≤2 projects → full 15 (disengagement/underutilization). ≥7 projects → full 15 (EDA showed **100% of 7-project employees left**). 5–6 projects → partial risk (mild overload). |
| 3 | **Working hours** | 15 | Healthy band = 150–240 hrs/month → 0 risk. Above 240, risk scales linearly up to the full 15 at ~310 hrs (severe overwork). Below 150, risk scales up (disengagement/quiet quitting signal). |
| 4 | **Tenure "danger zone"** | 10 | Years 4–5 → full 10 (EDA showed a sharp, unusual dip in satisfaction and a spike in attrition at the 4-year mark). Years 3–6 (excl. 4–5) → 60% of weight. Outside that window → 0. |
| 5 | **No recent promotion** | 10 | No promotion in 5 years **and** tenure ≥ 3 years → full 10 (stalled growth). No promotion with <3 years tenure → smaller penalty (less unusual early on). Promoted → 0. |
| 6 | **Compensation band** | 10 | `low` salary → full 10, `medium` → half, `high` → 0. |
| 7 | **"Silent burnout" flight risk** | 10 | Triggers only when **all three** hold: last_evaluation ≥ 0.80, average_monthly_hours > 220, satisfaction_level < 0.50. Captures the specific EDA-identified cluster of *top performers who are quietly burning out and are undervalued* — often missed by managers because their output still looks fine on paper. |

**Final score = sum of all 7 components (0–100).**

### Risk Bands
| Band | Score Range |
|---|---|
| 🔴 High | ≥ 65 |
| 🟡 Medium | 35 – 64 |
| 🟢 Low | < 35 |

All weights and thresholds live in a single `config.py` file so HR can
recalibrate the model (e.g., after a new engagement survey) without touching
any logic.

## 3. Recommended Interventions

For every employee, the tool identifies their **top contributing risk
factors** (not just the overall score) and maps each one to specific,
actionable interventions — e.g.:

- Low satisfaction → confidential stay interview + team engagement pulse survey
- Workload imbalance → project audit / redistribution or stretch assignment
- Unhealthy hours → workload rebalancing, enforce leave usage
- Tenure danger zone → career-pathing conversation, lateral move/new ownership
- No promotion → explicit growth-plan and promotion-timeline discussion
- Low compensation → market benchmarking / non-monetary levers
- Silent burnout → priority leadership-level retention conversation

This means two employees can both be "High risk" but receive **different**,
targeted recommendations depending on *why* they're at risk — this is what
makes the tool actionable rather than just a scoreboard.

## 4. Validation Against Historical Outcomes

Because the dataset includes actual historical attrition (`left`), the rule
score can be sanity-checked against reality even though `left` was never fed
into the scoring formula itself:

| Group | Avg. Rule-Based Risk Score |
|---|---|
| Employees who **left** | ~58.6 |
| Employees who **stayed** | ~34.7 |
| Point-biserial correlation (score vs. left) | **~0.55** |

A meaningfully higher average score for employees who actually left, and a
moderate-to-strong positive correlation, confirms the hand-designed rules
track real attrition behavior rather than being arbitrary.

## 5. Output of the Utility

Running `main.py` produces:
1. **Console summary** — risk band breakdown, department hot-spots, top-N
   highest-risk currently-employed staff, and the validation check above.
2. `attrition_risk_full_report.csv` — every employee, their score, band,
   reasons, and recommended interventions.
3. `high_risk_current_employees.csv` — a filtered action list of only the
   currently-employed High-risk employees, ranked by score, ready to hand to
   line managers.
4. `risk_distribution.png` — employee counts by risk band.
5. `risk_by_department.png` — average risk score by department (helps HR
   spot systemic team/department-level issues vs. one-off individual cases).

## 6. Interactive Dashboard & Risk Personas (`app.py`)

In addition to the CLI utility, the project includes a Streamlit dashboard
(`streamlit run app.py`) that adds two things beyond the original brief:

- **Interactive exploration**: filterable charts, an at-risk employee table,
  and a per-employee drill-down showing a radar chart of their 7 risk-factor
  components alongside their personalized recommended interventions.
- **Risk personas (K-Means clustering)**: rather than treating every at-risk
  employee individually, employees are grouped by *why* they're at risk
  (clustering on the 7 component scores from Section 2) into a small number
  of shared personas — e.g. *"Disengaged & Underpaid"* or *"Burnt-Out High
  Performer"*. Each persona gets **one common recommended strategy** that
  covers everyone in that group, which scales far better for HR than a
  bespoke plan per person while still being more targeted than one
  company-wide policy. The number of personas is adjustable (2–6) from the
  dashboard sidebar.

## 7. Beyond the Brief (Creativity)

- **Explainability by design**: instead of a single opaque score, every
  employee's top 3 risk drivers are surfaced and mapped 1:1 to specific
  interventions — this is what makes the tool usable in an actual
  manager conversation.
- **Self-validating**: the tool automatically checks its own rules against
  real historical outcomes on every run, rather than asking the reader to
  trust the weights blindly.
- **Config-driven architecture**: all weights/thresholds are isolated in
  `config.py`, so the tool can be recalibrated by a non-engineer without
  touching scoring code — this also makes future ML-model integration
  straightforward (swap the rule engine for a trained classifier's
  `.predict_proba()` while keeping the same reporting/recommendation layer).
- **Department-level lens**: beyond individual flags, the department-average
  chart highlights whether attrition risk is a systemic team-level problem
  (e.g., a manager, workload structure) rather than only individual cases.
