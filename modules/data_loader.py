"""
modules/data_loader.py
-----------------------
Handles importing employee data and getting it into a clean, standardized
shape that the rest of the utility can rely on.

Responsibilities:
    * Read the raw CSV
    * Standardize column names (snake_case, consistent spelling)
    * Assign a stable Employee_ID (the raw HR export has no unique key)
    * Basic sanity cleaning: drop exact duplicate rows, validate dtypes
"""

import os
import pandas as pd

from config import COLUMN_MAP

REQUIRED_COLUMNS = {
    "satisfaction_level",
    "last_evaluation",
    "number_project",
    "average_monthly_hours",
    "tenure",
    "work_accident",
    "left",
    "promotion_last_5years",
    "department",
    "salary",
}


def load_employee_data(csv_path: str) -> pd.DataFrame:
    """
    Import employee data from a CSV file and return a standardized,
    analysis-ready DataFrame.

    Parameters
    ----------
    csv_path : str
        Path to the employee data CSV file.

    Returns
    -------
    pd.DataFrame
        Cleaned dataframe with an Employee_ID column and standardized
        column names.
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Employee data file not found: {csv_path}")

    df = pd.read_csv(csv_path)

    # Standardize column names
    df = df.rename(columns=COLUMN_MAP)
    df.columns = [c.strip() for c in df.columns]

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(
            f"Input data is missing required columns: {sorted(missing)}. "
            f"Check config.COLUMN_MAP if your export uses different headers."
        )

    # Drop exact duplicate records (e.g. accidental double export)
    before = len(df)
    df = df.drop_duplicates(keep="first").reset_index(drop=True)
    dropped = before - len(df)

    # Assign a stable, human-friendly Employee ID since the raw HRIS
    # export does not include one. In a production deployment this
    # would instead be the real employee ID/name pulled from the HRIS.
    df.insert(0, "employee_id", [f"EMP{i+1:05d}" for i in range(len(df))])

    # Type safety
    numeric_cols = [
        "satisfaction_level", "last_evaluation", "number_project",
        "average_monthly_hours", "tenure", "work_accident",
        "left", "promotion_last_5years",
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["department"] = df["department"].astype(str).str.strip().str.lower()
    df["salary"] = df["salary"].astype(str).str.strip().str.lower()

    if dropped:
        print(f"[data_loader] Dropped {dropped} exact duplicate rows.")

    return df
