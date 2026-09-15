# AttritionGuard — Employee Attrition Early-Warning & Retention Intelligence

A local Python/Streamlit utility that imports employee data, applies a transparent rule-based attrition risk score, explains the main risk drivers, identifies employees needing attention, groups similar risk profiles into personas, and recommends targeted retention actions.

## Why this version is structured as an application

The assignment brief asks the solution to import employee data, calculate an attrition risk score, highlight high-risk employees, and recommend interventions. It also explicitly permits assumptions and scope expansion. This version therefore uses a decision-support workflow rather than a single scrolling dashboard:

1. **Executive Overview** — headline KPIs, risk distribution, department hotspots, common drivers, and a priority employee queue.
2. **Risk Explorer** — filterable employee table plus interactive relationship analysis.
3. **Employee Profile** — individual risk score, context, contribution by factor, explanation, and recommended next steps.
4. **Risk Personas** — K-Means grouping of medium/high-risk employees based on the seven interpretable score components.
5. **Retention Actions** — an action queue grouped by common risk drivers plus a top-priority review list and CSV export.
6. **Methodology** — weights, thresholds, rule logic, risk bands, and validation against historical attrition.

## Run the app

### Easiest option — VS Code
Open the project folder in VS Code, select the Python environment where the requirements are installed, open `app.py`, and click **Run Python File** (the play button in the top-right).

`app.py` is designed to start Streamlit automatically, open the browser at `http://localhost:8501`, and locate `HR_dataset.csv` relative to the script. It does not depend on whatever folder VS Code happens to use as the current working directory.

### Command line
You can also run:

```bash
python app.py
```

or:

```bash
python -m streamlit run app.py
```

### Windows launcher
Double-click `RUN_APP.bat` to start the same local Streamlit application.

## Project structure

```text
attrition_risk_utility/
├── app.py
├── main.py
├── config.py
├── HR_dataset.csv
├── RULES_AND_METHODOLOGY.md
├── requirements.txt
├── modules/
│   ├── data_loader.py
│   ├── risk_scoring.py
│   ├── recommendations.py
│   ├── clustering.py
│   └── report_generator.py
├── output/
└── .streamlit/
    └── config.toml
```

## Risk model

The score is a weighted 0–100 sum of seven transparent components:

| Factor | Weight |
|---|---:|
| Satisfaction | 30 |
| Workload | 15 |
| Working hours | 15 |
| Tenure zone | 10 |
| No recent promotion | 10 |
| Salary band | 10 |
| Silent-burnout flight risk | 10 |

Risk bands:

- **High:** 65–100
- **Medium:** 35–64
- **Low:** 0–34

The historical `left` outcome is not used as an input into the score; it is used afterward to validate whether higher rule-based risk is associated with actual historical attrition.

See `RULES_AND_METHODOLOGY.md` for the complete rule definitions and business rationale.


### Presentation labels
The raw HR dataset keeps its original department keys (for example `product_mng` and `randd`) so that the scoring and data-loading logic remain compatible with the supplied file. The application converts these values to business-friendly labels such as **Product Management** and **R&D** everywhere they are shown to the user. The Risk Explorer relationship selectors likewise use readable labels such as **Number of Projects**, **Working Hours**, **Tenure (Years)**, and **Last Evaluation** instead of raw CSV field names.
