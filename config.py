"""
config.py
---------
All tunable parameters for the Attrition Early Warning Utility live here.
Keeping rules/weights/thresholds in one place means HR/analytics teams can
recalibrate the model (e.g. after a fresh engagement survey) WITHOUT
touching any scoring logic in the rest of the codebase.

Every weight below is documented with the business rationale behind it.
Weights across all rule components sum to 100, so the final Attrition
Risk Score is naturally expressed on a 0-100 scale.
"""

# ---------------------------------------------------------------------------
# 1. Column mapping
#    Maps the raw column names found in HR_dataset.csv to the standardized
#    internal names used throughout the utility. Edit this if you plug in a
#    dataset from a different HRIS export.
# ---------------------------------------------------------------------------
COLUMN_MAP = {
    "Work_accident": "work_accident",
    "average_montly_hours": "average_monthly_hours",
    "time_spend_company": "tenure",
    "Department": "department",
}

# ---------------------------------------------------------------------------
# 2. Rule weights (must sum to 100)
# ---------------------------------------------------------------------------
WEIGHTS = {
    "satisfaction": 30,          # self-reported satisfaction (inverse)
    "workload": 15,              # number_project sweet-spot vs over/under-load
    "hours": 15,                 # average_monthly_hours over/under-work
    "tenure_zone": 10,           # "danger zone" tenure years
    "promotion": 10,             # no promotion in last 5 years
    "salary": 10,                # compensation band
    "burnout_flight_risk": 10,   # high performer + overworked + unhappy
}
assert sum(WEIGHTS.values()) == 100, "Rule weights must sum to 100"

# ---------------------------------------------------------------------------
# 3. Workload (number_project) thresholds
# ---------------------------------------------------------------------------
WORKLOAD_UNDERLOAD_MAX = 2       # <=2 projects -> disengagement risk
WORKLOAD_OPTIMAL_MIN = 3         # 3-4 projects -> optimal, zero risk
WORKLOAD_OPTIMAL_MAX = 4
WORKLOAD_ELEVATED_MAX = 6        # 5-6 projects -> mild overload
WORKLOAD_OVERLOAD_MIN = 7        # >=7 projects -> severe overload (EDA: 100% left)

# ---------------------------------------------------------------------------
# 4. Working hours thresholds (monthly)
# ---------------------------------------------------------------------------
HOURS_UNDERWORK_MAX = 150        # below this -> disengagement signal
HOURS_NORMAL_MAX = 240           # 150-240 considered healthy range
HOURS_OVERWORK_CEILING = 310     # hours at/above this hit max overwork penalty

# ---------------------------------------------------------------------------
# 5. Tenure "danger zone" (years) - derived from EDA showing peak attrition
#    and unusually low satisfaction around the 3-6 year mark, spiking at 4-5
# ---------------------------------------------------------------------------
TENURE_HIGH_RISK_YEARS = (4, 5)
TENURE_MEDIUM_RISK_RANGE = (3, 6)   # inclusive

# ---------------------------------------------------------------------------
# 6. Burnout / flight-risk trigger (high performer quietly overworked)
# ---------------------------------------------------------------------------
BURNOUT_EVAL_MIN = 0.80
BURNOUT_HOURS_MIN = 220
BURNOUT_SATISFACTION_MAX = 0.50

# ---------------------------------------------------------------------------
# 7. Final risk bands
# ---------------------------------------------------------------------------
RISK_BAND_HIGH_MIN = 65
RISK_BAND_MEDIUM_MIN = 35
# score < RISK_BAND_MEDIUM_MIN -> Low

# ---------------------------------------------------------------------------
# 8. Reporting
# ---------------------------------------------------------------------------
DEFAULT_TOP_N = 20               # how many highest-risk employees to spotlight
