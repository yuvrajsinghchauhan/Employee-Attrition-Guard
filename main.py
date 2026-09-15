#!/usr/bin/env python3
"""
main.py
========
Early Warning (Attrition) Indicator — main entry point.

Usage
-----
    python main.py --input HR_dataset.csv --output output/ --top 20

What it does
------------
1. Imports employee data from a CSV file (data_loader).
2. Calculates a transparent, rule-based Attrition Risk Score (0-100) for
   every employee (risk_scoring).
3. Highlights high-risk employees still on the payroll (report_generator).
4. Recommends specific interventions tied to each employee's actual risk
   drivers (recommendations).
5. Exports CSV reports + PNG charts, and sanity-checks the rules against
   historical attrition outcomes already present in the dataset.

See RULES_AND_METHODOLOGY.md for the full documented rule set (weights,
thresholds, and business rationale) — intended to be lifted directly into
the project submission deck.
"""

import argparse
import os
import sys

import config as cfg

# Directory this script lives in — used so defaults work regardless of the
# current working directory the script happens to be launched from.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_INPUT = os.path.join(SCRIPT_DIR, "HR_dataset.csv")
DEFAULT_OUTPUT = os.path.join(SCRIPT_DIR, "output")
from modules.data_loader import load_employee_data
from modules.risk_scoring import score_dataframe
from modules.recommendations import add_recommendations
from modules.report_generator import (
    print_console_summary,
    validate_against_history,
    export_reports,
    generate_charts,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Employee Attrition Early-Warning Utility"
    )
    parser.add_argument(
        "--input", "-i", default=DEFAULT_INPUT,
        help=f"Path to the input employee data CSV (default: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "--output", "-o", default=DEFAULT_OUTPUT,
        help=f"Directory to write reports/charts to (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--top", "-n", type=int, default=cfg.DEFAULT_TOP_N,
        help=f"Number of highest-risk employees to spotlight in the console "
             f"summary (default: {cfg.DEFAULT_TOP_N})",
    )
    parser.add_argument(
        "--no-charts", action="store_true",
        help="Skip generating PNG charts (faster, headless-friendly).",
    )
    return parser.parse_args()


def run(input_path: str, output_dir: str, top_n: int, make_charts: bool = True) -> None:
    print(f"[main] Loading employee data from '{input_path}' ...")
    df = load_employee_data(input_path)
    print(f"[main] Loaded {len(df)} employee records.")

    print("[main] Calculating attrition risk scores ...")
    scored = score_dataframe(df)

    print("[main] Building recommended interventions ...")
    scored = add_recommendations(scored)

    print_console_summary(scored, top_n=top_n)
    validate_against_history(scored)

    print(f"[main] Writing CSV reports to '{output_dir}' ...")
    paths = export_reports(scored, output_dir)
    for label, path in paths.items():
        print(f"    - {label}: {path}")

    if make_charts:
        print(f"[main] Generating charts in '{output_dir}' ...")
        chart_paths = generate_charts(scored, output_dir)
        for label, path in chart_paths.items():
            print(f"    - {label}: {path}")

    print("\n[main] Done. Review the high-risk report first — those are the "
          "currently-employed people most worth a proactive conversation.")


if __name__ == "__main__":
    args = parse_args()
    try:
        run(args.input, args.output, args.top, make_charts=not args.no_charts)
    except Exception as exc:
        print(f"[main] ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
