# ColdChainGuard

> **Automated Cold-Chain Compliance Evidence System**  
> An end-to-end prototype that joins sensor logs, calibration records, custody handovers and route events into complete audit-ready compliance packs — eliminating manual report assembly for online grocers shipping frozen and chilled items.

---

## Problem Statement

An online grocer ships frozen (−25 °C to −18 °C) and chilled (2 °C to 8 °C) products together. Compliance reports are currently assembled **manually** from disconnected IoT devices and disconnected logs. This is slow, error-prone and creates audit risk.

**ColdChainGuard** automates that entire process: from raw sensor data to a signed-off PDF audit report, with a live compliance dashboard and dispatcher override management.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     DATA GENERATION                          │
│  data_generator.py → vehicles, sensors, batches, shipments, │
│  sensor_logs, calibrations, handovers, route_events          │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                   PostgreSQL DATABASE                        │
│  database/schema.sql  |  database/load_data.py              │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                 SENSOR PROCESSING                            │
│  sensor_processor.py → handle missing/noisy obs,            │
│  store-and-forward fallback, interpolation                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                 COMPLIANCE ENGINE                            │
│  compliance_engine.py → temperature excursion duration,      │
│  calibration validity, custody chain, route deviations       │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                 EVIDENCE PACK                                │
│  evidence_pack.py → joins all 6 evidence sources per        │
│  shipment into compliance_evidence_pack.csv / .json         │
└──────────────────────┬──────────────────────────────────────┘
                       │
              ┌────────┴────────┐
              │                 │
┌─────────────▼──────┐  ┌───────▼───────────────────────────┐
│   AUDIT REPORTS    │  │       LIVE DASHBOARD               │
│   audit_report.py  │  │       dashboard.py                 │
│   → PDF per shipmt │  │       → KPIs, charts, override UI  │
└────────────────────┘  └───────────────────────────────────┘
```

---

## Dataset

| File | Records | Description |
|------|---------|-------------|
| `sensor_logs.csv` | ~50,000 | Raw IoT temperature readings every 5 min |
| `calibrations.csv` | 150 | Sensor calibration certificates |
| `handovers.csv` | ~1,500 | Custody transfer signatures |
| `route_events.csv` | ~3,000 | Checkpoints, delays, deviations |
| `product_batches.csv` | 500 | Frozen & chilled product batches |
| `shipments.csv` | 500 | Shipment master records |

---

## Key Features

- ✅ **Automated compliance scoring** — temperature excursion detection, calibration validity, custody chain completeness, route reliability
- ✅ **Missing & noisy observation handling** — interpolation, outlier capping, evidence status tagging
- ✅ **Store-and-forward / fallback** — offline sensor readings are retained and processed on reconnect
- ✅ **Alert threshold tuning** — Warning (5 min), Critical (15 min) thresholds with configurable noise tolerance
- ✅ **Dispatcher override** — Interactive UI form + full audit history of every plan change with reason
- ✅ **Trade-off analysis** — Cost × Time × Emissions × Reliability radar chart across 3 strategies
- ✅ **Automated audit PDF reports** — per-shipment ReportLab PDFs with 8 evidence sections
- ✅ **Live Dash dashboard** — CSV fallback if PostgreSQL is down, 30-second auto-refresh
- ✅ **Failure mode analysis** — 4 edge/failure case tests with PASS/FAIL results
- ✅ **Experiment HTML report** — baseline vs automated comparison with measured results

---

## Quick Start

### 1. Prerequisites

- Python 3.10+
- PostgreSQL 14+ (optional — dashboard falls back to CSV if DB is unavailable)

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Database (Optional)

Edit `.env` to match your PostgreSQL credentials:
```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=coldchainguard
DB_USER=postgres
DB_PASSWORD=yourpassword
```

Create the database:
```sql
CREATE DATABASE coldchainguard;
\c coldchainguard
\i database/schema.sql
```

### 4. Run the Full Pipeline

```bash
# With PostgreSQL (full pipeline)
python run_all.py

# Without PostgreSQL (CSV-only mode)
python run_all.py --skip-db
```

### 5. Open the Dashboard

```
http://127.0.0.1:8050/
```

### 6. View Experiment Report

```
data/experiments/experiment_report.html
```

---

## Running Individual Modules

```bash
# Generate synthetic data
python src/data_generator.py

# Process sensor logs (handle missing/noisy)
python src/sensor_processor.py

# Run compliance engine
python src/compliance_engine.py

# Build evidence pack (requires DB)
python src/evidence_pack.py

# Run experiments
python src/tradeoff_experiment.py
python src/threshold_tuning.py
python src/baseline_experiment.py

# Run failure tests
python src/failure_tests.py

# Generate audit PDFs (all shipments)
python src/audit_report.py

# Generate experiment HTML report
python src/experiment_notebook.py

# Launch dashboard
python src/dashboard.py
```

---

## Project Deliverables

| Deliverable | File/Location | Status |
|-------------|--------------|--------|
| Field-Workflow Map | `docs/field_workflow_map.md` | ✅ |
| Data Generation Script | `src/data_generator.py` | ✅ |
| Functional Application (Dashboard) | `src/dashboard.py` | ✅ |
| Experiment Notebook | `src/experiment_notebook.py` → `data/experiments/experiment_report.html` | ✅ |
| Failure Mode Analysis | `docs/failure_mode_analysis.md` | ✅ |
| User Feedback Summary | `docs/user_feedback_summary.md` | ✅ |
| Technical Documentation | `docs/technical_documentation.md` | ✅ |
| Audit Reports (PDF) | `data/reports/*.pdf` | ✅ |
| Trade-off Experiment | `data/experiments/tradeoff_summary.csv` | ✅ |
| Baseline Comparison | `data/experiments/baseline_results.csv` | ✅ |

---

## Trade-off Dimensions

| Dimension | Measured As |
|-----------|-------------|
| **Cost** | Estimated fuel/time cost per shipment (lower = better) |
| **Time** | Average delay minutes added per shipment |
| **Emissions** | CO₂ kg estimated from route duration |
| **Reliability** | Compliance pass rate (%) |

Three routing strategies are compared: **Standard**, **Express**, **Eco**.

---

## Compliance Thresholds

| Level | Temperature Excursion | Action |
|-------|----------------------|--------|
| Compliant | 0 min | Auto-approved |
| Warning | 1–5 min | Flagged for review |
| Alert | 6–15 min | Manual verification required |
| Critical | > 15 min | Non-Compliant — escalated |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.13 |
| Database | PostgreSQL + SQLAlchemy |
| Dashboard | Dash 4 + Plotly 7 |
| PDF Reports | ReportLab 5 |
| Data | Pandas 3 + NumPy 2 |
| Deployment | Local (single-machine) |

---

## Folder Structure

```
ColdChainGuard/
├── .env                          # DB credentials
├── requirements.txt              # Pinned dependencies
├── run_all.py                    # Single-command pipeline runner
├── README.md                     # This file
│
├── src/                          # All Python source modules
│   ├── data_generator.py
│   ├── sensor_processor.py
│   ├── compliance_engine.py
│   ├── evidence_pack.py
│   ├── audit_report.py
│   ├── dashboard.py
│   ├── dispatcher_override.py
│   ├── store_and_forward.py
│   ├── threshold_tuning.py
│   ├── tradeoff_experiment.py
│   ├── baseline_experiment.py
│   ├── failure_tests.py
│   ├── data_quality.py
│   └── experiment_notebook.py    # [NEW] HTML experiment report
│
├── database/
│   ├── schema.sql
│   ├── schema.py
│   ├── connection.py
│   └── load_data.py
│
├── data/
│   ├── raw/                      # Generated CSVs
│   ├── evidence/                 # Evidence pack JSON/CSV
│   ├── experiments/              # Experiment results + HTML report
│   └── reports/                  # Per-shipment PDF audit reports
│
├── data/etl/                     # [REVIEW 1] Analytical master datasets
│   ├── master_shipments.csv      #   500 rows x 37 columns (star schema join)
│   ├── etl_summary.csv           #   Row counts per analytical table
│   └── star_schema/              #   Per-table CSVs (7 files)
│
├── data/eda/                     # [REVIEW 1] EDA outputs
│   ├── plots/                    #   10 matplotlib charts
│   ├── dataset_summary.csv
│   ├── missing_values.csv
│   ├── descriptive_statistics.csv
│   ├── outlier_analysis.csv
│   ├── correlation_matrix.csv
│   └── eda_insights.md
│
├── data/segmentation/            # [REVIEW 1] RFM segmentation outputs
│   ├── rfm_vehicle_segments.csv  #   100 vehicles with RFM scores
│   ├── rfm_summary.csv           #   Per-segment statistics
│   ├── rfm_segment_distribution.csv
│   ├── rfm_segment_distribution.png
│   ├── rfm_scatter.png
│   ├── rfm_scores.png
│   └── rfm_insights.md
│
└── docs/                         # Documentation deliverables
    ├── field_workflow_map.md
    ├── technical_documentation.md
    ├── user_feedback_summary.md
    ├── failure_mode_analysis.md
    └── Review_1_35_Percent_Report.md  # [REVIEW 1] Full milestone report
```

---

## Review 1 — 35% Completion

This section documents the first 35% milestone deliverables.

### Day 1 — Data Integration and Preprocessing (15%)

**ETL pipeline** implemented in Python using Pandas and PostgreSQL (not Power Query).

- **Raw data:** 8 CSV datasets (100 vehicles, 150 sensors, 500 batches, 500 shipments, 21,125 sensor logs, 150 calibrations, 1,511 handovers, 3,289 route events)
- **Cleaning:** `src/sensor_processor.py` handles missing readings (interpolation), noisy readings (IQR capping), offline sensors (store-and-forward)
- **Analytical star-schema layer:** `src/star_schema.py` creates 7 analytical tables (3 dimension + 4 fact) from the operational tables

| Analytical Table | Rows | Description |
|-----------------|------|-------------|
| `dim_vehicle` | 100 | Vehicle type, capacity |
| `dim_product` | 500 | Product name, type, temperature limits |
| `dim_date` | 7 | Date attributes for departure/arrival |
| `fact_shipments` | 500 | Central fact with compliance status |
| `fact_sensor_logs` | 500 | Aggregated sensor metrics per shipment |
| `fact_route_events` | 500 | Aggregated route metrics per shipment |
| `fact_handovers` | 500 | Aggregated custody metrics per shipment |

- **Master dataset:** `data/etl/master_shipments.csv` — 500 rows × 37 columns

Run: `python src/star_schema.py`

---

### Day 2 — Descriptive Statistics and EDA (10%)

`src/eda_analysis.py` — 13 analysis sections from live PostgreSQL data.

**Key statistics from actual data:**

| Metric | Value |
|--------|-------|
| Mean temperature | −7.46 °C (bimodal: frozen ~−21 °C, chilled ~+5 °C) |
| Compliant shipments | 42.8% (214/500) |
| Missing temp readings | 0.22% (46 / 21,125) |
| Missing custody signatures | 8.1% (123 / 1,511) |
| Invalid calibrations | 22% (33 / 150) |
| Mean journey duration | 208 min (range 60–360 min) |

**Outputs:** 10 professional plots in `data/eda/plots/`, 5 CSVs, `eda_insights.md`

Run: `python src/eda_analysis.py`

---

### Day 3 — Operational RFM-Based Asset Segmentation (10%)

`src/rfm_segmentation.py` — Vehicle asset segmentation using adapted RFM.

**Entity:** Vehicle | **R:** Days since last shipment | **F:** Shipment count | **M:** Total product volume transported

> M is adapted from monetary value to transported product volume, as ColdChainGuard does not record per-shipment revenue. This is documented and methodologically sound for logistics asset segmentation.

**Results (100 vehicles, quintile scoring):**

| Segment | Vehicles | % |
|---------|----------|---|
| Champions | 18 | 18% |
| Loyal Assets | 35 | 35% |
| Active Assets | 22 | 22% |
| At-Risk Assets | 5 | 5% |
| Low-Activity Assets | 20 | 20% |

**Outputs:** `data/segmentation/` — 3 CSVs, 3 plots, `rfm_insights.md`

Run: `python src/rfm_segmentation.py`

---

### Review 1 Validation

```bash
python src/validate_review1.py
```

Expected output:
```
DAY 1 -- ETL & PREPROCESSING         PASS
DAY 2 -- EDA                          PASS
DAY 3 -- RFM SEGMENTATION             PASS
FIRST 35% REQUIREMENT                 PASS
```

Full milestone report: [`docs/Review_1_35_Percent_Report.md`](docs/Review_1_35_Percent_Report.md)
