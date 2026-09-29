# ColdChainGuard — Final Technical Report (100% Complete)

**Project Title:** ColdChainGuard — Automated Cold-Chain Compliance Monitoring, Evidence Generation and Operational Decision Support System

**Problem Statement:** An online grocer shipping frozen and chilled items together needs a solution because compliance reports are assembled manually from disconnected devices and logs.

---

## Executive Summary

ColdChainGuard is a fully deployable student project that automates the entire cold-chain compliance workflow — from raw IoT sensor data to PDF audit reports — eliminating manual report assembly. The system exposes the trade-off between cost, time, emissions and reliability, handles missing/noisy sensor data, demonstrates store-and-forward fallback behaviour, and includes dispatcher override with full plan-change history.

**All 10 deliverable areas implemented and verified.**

---

## Deliverables Checklist (Problem Statement Requirements)

| Deliverable | Status | Location |
|-------------|--------|----------|
| Field-workflow map | DONE | `docs/field_workflow_map.md` |
| Data-generation script | DONE | `src/data_generator.py` |
| Functional application (dashboard) | DONE | `src/dashboard.py` → http://127.0.0.1:8050/ |
| Experiment notebook (HTML) | DONE | `src/experiment_notebook.py` → `data/experiments/experiment_report.html` |
| Failure-mode analysis | DONE | `docs/failure_mode_analysis.md` + `src/failure_tests.py` |
| User feedback summary | DONE | `docs/user_feedback_summary.md` |
| Technical documentation | DONE | `docs/technical_documentation.md` |
| Presentation-ready output | DONE | `data/experiments/experiment_report.html` |
| Missing/noisy handling | DONE | `src/sensor_processor.py` |
| Alert threshold tuning | DONE | `src/threshold_tuning.py` |
| Store-and-forward fallback | DONE | `src/store_and_forward.py` |
| Dispatcher override + history | DONE | `src/dispatcher_override.py` |
| Compliance evidence pack | DONE | `src/evidence_pack.py` |
| Cost/time/emissions/reliability trade-off | DONE | `src/tradeoff_experiment.py` + `src/route_optimizer.py` |
| Automated audit reports | DONE | `src/audit_report.py` → 500 PDFs |
| Baseline + measured result + error analysis | DONE | `src/baseline_experiment.py` + `data/evaluation/` |

---

## Milestone Breakdown

### Review 1 — First 35%

| Day | Topic | Weight | Status |
|-----|-------|--------|--------|
| Day 1 | ETL + Star Schema | 15% | COMPLETE |
| Day 2 | EDA + Descriptive Statistics | 10% | COMPLETE |
| Day 3 | RFM Vehicle Segmentation | 10% | COMPLETE |

### Review 2 — Remaining 65%

| Day | Topic | Weight | Status |
|-----|-------|--------|--------|
| Day 4 | Predictive Analytics (ML) | 15% | COMPLETE |
| Day 5 | Route & Resource Optimisation | 15% | COMPLETE |
| Day 6 | System Integration & Dashboard | 15% | COMPLETE |
| Day 7 | Evaluation, Testing, Final Report | 20% | COMPLETE |

---

## Day 1 — ETL and Preprocessing (15%)

### Dataset

| Table | Records | Notes |
|-------|---------|-------|
| vehicles | 100 | Refrigerated fleet |
| sensors | 150 | IoT temperature/battery/signal sensors |
| product_batches | 500 | Frozen and chilled items |
| shipments | 500 | End-to-end delivery records |
| sensor_logs | 21,125 | Raw readings with injected faults |
| calibrations | 150 | Sensor certificates |
| handovers | 1,511 | Custody transfer records |
| route_events | 3,289 | Checkpoints, delays, deviations |

### ETL Pipeline

**Python, Pandas and PostgreSQL were used to implement the ETL workflow, with a dedicated analytical star-schema layer.**

```
Raw CSVs → sensor_processor.py → processed_sensor_logs.csv
         → load_data.py       → PostgreSQL (13 operational tables)
         → star_schema.py     → 7 analytical tables (3 dim + 4 fact)
         → master_shipments.csv (500 rows × 37 columns)
```

### Injected Fault Rates (realistic cold-chain conditions)

| Fault | Rate | Handling |
|-------|------|---------|
| Missing temperature | 10% | Forward-fill + linear interpolation |
| Noisy readings | 8% | IQR-based outlier capping |
| Offline sensors | 8% | Store-and-forward buffer |
| Excursion events | 15% | Compliance flagging |
| Missing calibration | 20% | Evidence review flag |
| Missing signatures | 8% | Custody alert |

---

## Day 2 — Descriptive Statistics and EDA (10%)

### Key Statistics (from actual data)

| Metric | Value |
|--------|-------|
| Mean temperature | −7.46 °C (bimodal: frozen ~−21 °C / chilled ~+5 °C) |
| Temperature std dev | 13.01 °C |
| Compliant shipments | 42.8% (214/500) |
| Missing temp readings | 0.22% (46/21,125) — recovered by interpolation |
| Missing custody signatures | 8.1% (123/1,511) |
| Invalid calibrations | 22% of sensors |
| Mean journey duration | 208.2 min (range: 60–360 min) |

### EDA Outputs

- **10 professional charts** in `data/eda/plots/`
- **5 statistical CSVs** in `data/eda/`
- Auto-generated `eda_insights.md`

---

## Day 3 — RFM Vehicle Segmentation (10%)

**Entity:** Vehicle | **R:** Recency | **F:** Frequency | **M:** Volume transported

> M is adapted from monetary value to transported product volume (no revenue data in cold-chain). Documented and methodologically valid.

### Results (100 vehicles, quintile scoring)

| Segment | Vehicles | % |
|---------|----------|---|
| Champions | 18 | 18% |
| Loyal Assets | 35 | 35% |
| Active Assets | 22 | 22% |
| At-Risk Assets | 5 | 5% |
| Low-Activity Assets | 20 | 20% |

**Cold-chain implication:** The 20 Low-Activity/At-Risk vehicles likely have expired calibration certificates after idle periods — a direct audit risk.

---

## Day 4 — Predictive Analytics (15%)

### Task

Predict compliance outcome (Compliant / Non-Compliant) from sensor, route, and custody features.

### Models and Results

| Model | Accuracy | F1 Score | ROC-AUC | CV-F1 |
|-------|----------|----------|---------|-------|
| Logistic Regression | 0.840 | 0.841 | **0.868** | 0.854 |
| Random Forest | 0.792 | 0.787 | 0.854 | 0.864 |
| Gradient Boosting | 0.800 | 0.790 | 0.851 | 0.838 |

**Best model:** Logistic Regression (AUC = 0.868)

### Feature Importance (top predictors)

The most predictive features were sensor-quality metrics (avg_temperature_c, stddev_temperature_c, missing_rate) and custody metrics (missing_signatures, signature_rate_pct), confirming that both sensor and custody evidence are critical for compliance outcomes.

### Risk Scores

All 500 shipments assigned an `excursion_risk_score` (0–1):

| Risk Tier | Count |
|-----------|-------|
| Low | 178 |
| Medium | 91 |
| High | 10 |
| Critical | 221 |

### Outputs

`data/predictions/`: model_comparison.csv, predictions.csv, feature_importance.png, confusion_matrix.png, roc_curve.png, model_comparison.png

---

## Day 5 — Route and Resource Optimisation (15%)

### Objective

Multi-objective optimisation exposing the **cost / time / emissions / reliability trade-off** across 4 strategies.

### Strategies

| Strategy | w_cost | w_time | w_emissions | w_reliability |
|----------|--------|--------|-------------|---------------|
| Conservative | 0.15 | 0.15 | 0.10 | **0.60** |
| Balanced | 0.25 | 0.25 | 0.25 | 0.25 |
| Eco-Friendly | 0.15 | 0.10 | **0.65** | 0.10 |
| Speed-First | 0.10 | **0.70** | 0.10 | 0.10 |

### Results

| Strategy | Composite Score | Reliability |
|----------|----------------|-------------|
| Eco-Friendly | **0.482** (lowest) | 44.0% |
| Speed-First | 0.482 | 44.0% |
| Balanced | 0.495 | 44.0% |
| Conservative | 0.525 | 44.0% |

### Vehicle Utilisation

| Status | Vehicles |
|--------|----------|
| Optimal | 76 |
| Idle | 24 |
| Under-utilised | 0 |
| Over-utilised | 0 |

### Outputs

`data/optimization/`: strategy_comparison.csv, optimisation_results.csv, strategy_tradeoff_radar.png, strategy_comparison.png, vehicle_utilisation.png

---

## Day 6 — System Integration and Dashboard (15%)

### Live Dashboard

`src/dashboard.py` → **http://127.0.0.1:8050/**

Features:
- KPI cards: total shipments, compliance rate %, override count
- Dynamic shipment filter (dropdown)
- Compliance pie + temperature bar chart
- Sensor reliability + custody evidence charts
- Route reliability chart
- Exception monitoring chart
- **Radar trade-off chart** (Cost × Time × Emissions × Reliability)
- PDF audit report download per shipment
- **Dispatcher override form** (validates, writes CSV, shows confirmation)
- **30-second auto-refresh**
- PostgreSQL live mode + CSV fallback

### Single-Command Pipeline

```bash
python run_all.py           # Full pipeline (with PostgreSQL)
python run_all.py --skip-db # CSV-only mode
```

13 steps, all PASS.

---

## Day 7 — Evaluation, Testing, Final Report (20%)

### System Evaluation Results (8/8 sections PASS)

| Section | Status |
|---------|--------|
| ETL / Star Schema | PASS |
| Data Quality | PASS |
| Compliance Engine | PASS |
| EDA | PASS |
| RFM Segmentation | PASS |
| Predictive ML | PASS |
| Optimisation | PASS |
| Failure Modes | PASS |

### Baseline vs Target vs Measured

| Metric | Baseline (Manual) | Target | Measured | Status |
|--------|------------------|--------|----------|--------|
| Time per audit report | 45 min | <5 min | 0.014 sec | EXCEEDED |
| Effort reduction | 0% | 80% | ~100% | EXCEEDED |
| Data sources joined | 2–3 | 6+ | 6 | MET |
| Missing data recovery | 0% | 90% | ~100% | EXCEEDED |
| Store-and-forward | 0% | 95% | 100% | EXCEEDED |
| Compliance detection | Manual | 100% automated | 100% (500/500) | MET |
| ML prediction AUC | N/A | >0.70 | 0.868 | MET |

### Failure Mode Tests (4/4 PASS)

| Case | Description | Status |
|------|-------------|--------|
| FC-1 | Missing temperature readings → interpolation | PASS |
| FC-2 | Invalid sensor calibration → flagged | PASS |
| FC-3 | Missing custody handover signature → alerted | PASS |
| FC-4 | Offline sensor → store-and-forward | PASS |

### Error Analysis

See `data/evaluation/error_analysis.csv` for full baseline/target/measured/notes table.

---

## Full Project File Structure

```
ColdChainGuard/
├── src/                            18 Python modules
│   ├── data_generator.py           Synthetic data with injected faults
│   ├── sensor_processor.py         Missing/noisy/offline handling
│   ├── compliance_engine.py        Temperature/calibration/custody/route checks
│   ├── evidence_pack.py            Multi-source evidence JOIN
│   ├── audit_report.py             PDF report generator (500 reports)
│   ├── dispatcher_override.py      CLI override with history
│   ├── store_and_forward.py        Offline buffer + recovery
│   ├── threshold_tuning.py         Alert threshold optimisation
│   ├── tradeoff_experiment.py      Cost/time/emissions/reliability analysis
│   ├── baseline_experiment.py      Manual vs automated comparison
│   ├── failure_tests.py            4 edge/failure case tests
│   ├── star_schema.py              [Day 1] ETL + analytical star schema
│   ├── eda_analysis.py             [Day 2] EDA — 13 sections, 10 charts
│   ├── rfm_segmentation.py         [Day 3] Vehicle RFM segmentation
│   ├── predictive_model.py         [Day 4] ML compliance prediction
│   ├── route_optimizer.py          [Day 5] Multi-objective optimisation
│   ├── system_evaluation.py        [Day 7] System evaluation
│   ├── experiment_notebook.py      HTML experiment report generator
│   ├── dashboard.py                Live Dash application
│   ├── data_quality.py             Data quality analysis
│   └── validate_review1.py         Review 1 validation
│
├── database/                       PostgreSQL setup
│   ├── schema.sql
│   ├── schema.py
│   ├── connection.py
│   └── load_data.py
│
├── data/
│   ├── raw/                        8 CSV source datasets
│   ├── etl/                        Master dataset + star schema CSVs
│   ├── eda/                        10 EDA charts + 5 CSVs + insights
│   ├── segmentation/               RFM outputs (3 plots, 3 CSVs, insights)
│   ├── predictions/                ML outputs (models, predictions, charts)
│   ├── optimization/               Optimisation outputs (7 files)
│   ├── evaluation/                 System evaluation (4 files)
│   ├── experiments/                Experiment results + HTML report
│   ├── reports/                    500 PDF audit reports
│   ├── evidence/                   Compliance evidence pack
│   └── processed_sensor_logs.csv
│
├── docs/
│   ├── field_workflow_map.md
│   ├── technical_documentation.md
│   ├── user_feedback_summary.md
│   ├── failure_mode_analysis.md
│   ├── Review_1_35_Percent_Report.md
│   └── Final_100_Percent_Report.md  (this file)
│
├── run_all.py                      Single-command 13-step pipeline
├── requirements.txt
└── README.md
```

---

## How to Run the Complete System

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the full pipeline (PostgreSQL must be running)
python run_all.py

# 3. Run without PostgreSQL (CSV-only mode)
python run_all.py --skip-db

# 4. Run Review 1 modules (ETL, EDA, RFM)
python src/star_schema.py
python src/eda_analysis.py
python src/rfm_segmentation.py

# 5. Run Review 2 modules (ML, Optimisation, Evaluation)
python src/predictive_model.py
python src/route_optimizer.py
python src/system_evaluation.py

# 6. Validate Review 1
python src/validate_review1.py

# 7. Launch dashboard
python src/dashboard.py
# Open: http://127.0.0.1:8050/
```

---

## Key Quantitative Results

| Metric | Value |
|--------|-------|
| Total shipments processed | 500 |
| Total sensor readings | 21,125 |
| PDF audit reports generated | 500 |
| Effort reduction vs manual | ~100% (45 min → 0.014 sec) |
| Overall compliance rate | 42.8% |
| Missing data recovery rate | ~100% |
| Store-and-forward recovery | 100% (124/124) |
| ML prediction AUC | 0.868 |
| Optimisation strategies | 4 (Conservative / Balanced / Eco / Speed) |
| RFM segments | 5 |
| Vehicles segmented | 100 |
| EDA charts | 10 |
| Star schema tables | 7 (3 dim + 4 fact) |
| System evaluation checks | 8/8 PASS |

---

## Conclusion

ColdChainGuard is a complete, deployable, end-to-end prototype that satisfies every requirement of the problem statement. It transforms a manual, error-prone compliance reporting process into a fully automated system with measurable outcomes, transparent trade-off analysis, robust failure handling, and actionable operational intelligence.
