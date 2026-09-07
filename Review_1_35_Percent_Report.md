# ColdChainGuard — Review 1 (35%) Technical Report

**Project Title:** ColdChainGuard — Automated Cold-Chain Compliance Monitoring, Evidence Generation and Operational Decision Support System

**Review:** First 35% Milestone (Day 1 + Day 2 + Day 3)

**Date:** September 2026

**Implementation:** Python 3.13, Pandas, PostgreSQL, SQLAlchemy, Matplotlib

---

## 1. Problem Statement

An online grocer ships frozen (−25 °C to −18 °C) and chilled (2 °C to 8 °C) products together. Compliance reports are currently assembled **manually** from disconnected IoT devices and disconnected logs. This is slow, error-prone and creates audit risk.

ColdChainGuard automates that entire process: from raw sensor data to a signed-off PDF audit report, with a live compliance dashboard and dispatcher override management.

---

## 2. Review 1 Objective

Demonstrate completion of the first 35% milestone by delivering:

| Day | Weight | Topic |
|-----|--------|-------|
| Day 1 | 15% | Data Integration and Preprocessing (ETL) |
| Day 2 | 10% | Descriptive Statistics and Exploratory Data Analysis |
| Day 3 | 10% | Operational RFM-Based Asset Segmentation |
| **Total** | **35%** | **First milestone** |

---

## 3. First 35% Requirement Mapping

| Requirement | Implementation | Status |
|-------------|---------------|--------|
| Acquire, clean and integrate datasets | `data_generator.py` + `sensor_processor.py` + `database/load_data.py` | DONE |
| Produce analysis-ready master dataset | `star_schema.py` → `data/etl/master_shipments.csv` | DONE |
| Follow a star-schema design | 7 analytical tables (3 dim + 4 fact) in PostgreSQL | DONE |
| Technical documentation | `docs/technical_documentation.md` + this report | DONE |
| Cleaned/processed datasets | `data/raw/` (8 CSV files) + `data/processed_sensor_logs.csv` | DONE |
| Visualisations / dashboard | `src/dashboard.py` + `data/eda/plots/` (10 charts) | DONE |
| Python / SQL code | All source modules in `src/` + SQL in `src/star_schema.py` | DONE |
| Comprehensive EDA | `src/eda_analysis.py` — 13 analytical sections | DONE |
| Descriptive statistics | `data/eda/descriptive_statistics.csv` | DONE |
| Distributions, patterns, outliers | `data/eda/` — histograms, boxplots, outlier_analysis.csv | DONE |
| Correlation analysis | `data/eda/correlation_matrix.csv` + heatmap | DONE |
| EDA documentation | `data/eda/eda_insights.md` | DONE |
| Entity segmentation | `src/rfm_segmentation.py` — vehicle asset segmentation | DONE |
| RFM / behavioural analysis | Quintile-based RFM scoring on 100 vehicles | DONE |
| Segment visualisations | 3 plots in `data/segmentation/` | DONE |
| Segmentation report | `data/segmentation/rfm_insights.md` | DONE |

---

## 4. Day 1 — ETL and Data Preprocessing

### 4.1 Data Sources

The evaluation dataset was generated using `src/data_generator.py` with deliberate fault injection to simulate real-world cold-chain conditions.

| Dataset | Records | Injected Faults |
|---------|---------|----------------|
| `vehicles.csv` | 100 | — |
| `sensors.csv` | 150 | — |
| `product_batches.csv` | 500 | — |
| `shipments.csv` | 500 | — |
| `sensor_logs.csv` | 21,125 | 10% missing temp, 8% noisy, 8% offline |
| `calibrations.csv` | 150 | 10% expired, 10% calibration error |
| `handovers.csv` | 1,511 | 8% missing signatures |
| `route_events.csv` | 3,289 | Route deviations and delays |

### 4.2 Data Cleaning Pipeline

`src/sensor_processor.py` performs:

1. **Missing value handling** — Forward-fill, then linear interpolation for gaps ≤ 30 min
2. **Noise / outlier handling** — IQR-based outlier capping per sensor per shipment
3. **Calibration validity join** — Flags readings from sensors with invalid certs
4. **Evidence status tagging** — Normal / Interpolated / Capped / Recovered / Review

Result: `data/processed_sensor_logs.csv` — 21,125 records fully processed.

### 4.3 Analytical Star-Schema Layer

> **Python, Pandas and PostgreSQL were used to implement the ETL workflow, with a dedicated analytical star-schema layer.**

The operational database is normalised for write performance. A separate analytical layer was built using `src/star_schema.py` to support EDA and segmentation queries without altering the operational schema.

```
                 dim_vehicle
                      |
dim_product ---- fact_shipments ---- dim_date
                      |
               fact_sensor_logs
                      |
              fact_route_events
                      |
               fact_handovers
```

**Star schema verification (live row counts):**

| Table | Rows | Description |
|-------|------|-------------|
| `dim_vehicle` | 100 | Vehicle registry dimension |
| `dim_product` | 500 | Product batch dimension |
| `dim_date` | 7 | Date dimension (departure/arrival dates) |
| `fact_shipments` | 500 | Central fact table joining all dimensions |
| `fact_sensor_logs` | 500 | Aggregated sensor metrics per shipment |
| `fact_route_events` | 500 | Aggregated route event metrics per shipment |
| `fact_handovers` | 500 | Aggregated custody metrics per shipment |

**Master analytical dataset:** `data/etl/master_shipments.csv` — 500 rows × 37 columns, joining all 7 analytical tables into one analysis-ready flat file.

### 4.4 ETL Outputs

```
data/etl/
  master_shipments.csv          500 rows x 37 columns
  etl_summary.csv               7 rows (one per analytical table)
  star_schema/
    dim_vehicle.csv
    dim_product.csv
    dim_date.csv
    fact_shipments.csv
    fact_sensor_logs.csv
    fact_route_events.csv
    fact_handovers.csv
```

---

## 5. Day 2 — Descriptive Statistics and EDA

### 5.1 Module

`src/eda_analysis.py` — 13 analytical sections, reads from PostgreSQL analytical layer.

### 5.2 Dataset Overview

| Dataset | Rows | Columns |
|---------|------|---------|
| Shipments (master/fact) | 500 | 39 |
| Sensor logs (raw) | 21,125 | varies |
| Calibrations | 150 | varies |
| Handovers | 1,511 | varies |
| Route events | 3,289 | varies |

### 5.3 Key Descriptive Statistics

| Metric | Value |
|--------|-------|
| Overall mean temperature | −7.46 °C |
| Temperature std deviation | 13.01 °C |
| Temperature range | −22.53 °C to 18.57 °C |
| Missing temperature readings | 46 (0.22%) |
| Compliant shipments | 214 (42.8%) |
| Non-compliant shipments | 89 (17.8%) |
| Under review | 197 (39.4%) |
| Valid sensor calibrations | 117 of 150 (78%) |
| Missing custody signatures | 123 of 1,511 (8.1%) |
| Mean journey duration | 208.2 minutes |
| Journey duration range | 60–360 minutes |

### 5.4 Key EDA Findings

1. **Bimodal temperature distribution** — Two clear peaks near −21 °C (frozen) and +5 °C (chilled) confirm the dataset accurately represents both product categories.
2. **42.8% compliance rate** — The majority of shipments are either compliant or under review; non-compliance is present at a realistic minority rate.
3. **8.1% missing custody signatures** — A measurable operational gap in the chain of custody.
4. **22% invalid/expired calibrations** — Sensor maintenance is a significant driver of compliance review.
5. **Outlier analysis** — `missing_signatures` (22.8% outliers) and `total_delay_minutes` (17.0% outliers) show high variance, indicating inconsistent operational conditions.
6. **Weak correlations** — No strong linear correlations between numerical variables (expected: compliance is driven by threshold-crossing, not continuous relationships).

### 5.5 EDA Outputs

**Charts (10 plots in `data/eda/plots/`):**

| Plot | Description |
|------|-------------|
| `temperature_distribution.png` | Histogram + boxplot by frozen/chilled category |
| `temperature_boxplot.png` | Standalone temperature boxplot |
| `missing_values.png` | Missing value rates for master and sensor datasets |
| `shipment_status.png` | Overall compliance + temperature status bar charts |
| `calibration_status.png` | Calibration validity + error distribution |
| `handover_status.png` | Signature status + handovers per shipment |
| `route_events.png` | Event type distribution + delay duration |
| `correlation_heatmap.png` | 14×14 correlation matrix heatmap |
| `product_type_distribution.png` | Frozen vs chilled pie + quantity boxplot |
| `journey_duration_distribution.png` | Journey duration histogram with mean/median |

**CSVs (5 files in `data/eda/`):**

| File | Description |
|------|-------------|
| `dataset_summary.csv` | Row/column counts per dataset |
| `missing_values.csv` | Missing value rates per column |
| `descriptive_statistics.csv` | Full describe() output for 17 numerical variables |
| `outlier_analysis.csv` | IQR-based outlier counts per variable |
| `correlation_matrix.csv` | 14×14 Pearson correlation matrix |

**Insights:** `data/eda/eda_insights.md` — auto-generated from live data.

---

## 6. Day 3 — Operational RFM-Based Asset Segmentation

### 6.1 Methodology

**Module:** `src/rfm_segmentation.py`

**Segmentation entity:** Vehicle (`vehicle_id`)

**RFM Definitions:**

| Dimension | Definition | Source |
|-----------|-----------|--------|
| R — Recency | Days since vehicle's most recent shipment | `shipments.departure_time` |
| F — Frequency | Number of shipments handled | COUNT per `vehicle_id` |
| M — Volume | Total product quantity transported | SUM of `product_batches.quantity` |

> **Adaptation note on M:** Standard RFM uses monetary transaction value. ColdChainGuard does not record per-shipment revenue. M is therefore adapted to *transported product volume* (sum of `batch_quantity` across all shipments per vehicle). This is a documented and valid adaptation for asset/operational segmentation in cold-chain logistics.

**Scoring method:** Quintile-based (5 levels, n=100 supports quintiles)

- R scoring: Lower recency days → higher score (Score 5 = most recently active)
- F scoring: Higher frequency → higher score
- M scoring: Higher volume → higher score
- RFM_score = R_score + F_score + M_score (range: 3–15)

**Segment thresholds (proportional):**

| Segment | RFM Score Range |
|---------|----------------|
| Champions | 13–15 |
| Loyal Assets | 10–12 |
| Active Assets | 7–9 |
| At-Risk Assets | 4–6 |
| Low-Activity Assets | 3 |

### 6.2 Results

**Fleet of 100 vehicles segmented** (76 with shipments, 24 inactive):

| Segment | Vehicles | % of Fleet |
|---------|----------|-----------|
| Champions | 18 | 18.0% |
| Loyal Assets | 35 | 35.0% |
| Active Assets | 22 | 22.0% |
| At-Risk Assets | 5 | 5.0% |
| Low-Activity Assets | 20 | 20.0% |

**Key findings:**
- **Loyal Assets** is the largest segment (35%) — the fleet backbone
- **20% of vehicles are Low-Activity** — these 20 vehicles had zero shipments in the dataset and require operational investigation
- **18% are Champions** — highest R+F+M scores, priority for preventive maintenance
- The RFM score range of 3–15 was fully utilised, confirming good distributional spread

### 6.3 Cold-Chain Operational Implications

1. **Champions** — Prioritise for preventive maintenance and compliance certificate renewal
2. **Loyal Assets** — Standard monitoring; watch for frequency drops indicating mechanical issues
3. **Active Assets** — Normal operational utilisation; standard compliance monitoring
4. **At-Risk Assets** — Investigate for maintenance backlog or route reassignment
5. **Low-Activity Assets** — Verify calibration certificate validity before reactivation; idle vehicles may have expired certs

### 6.4 Segmentation Outputs

```
data/segmentation/
  rfm_vehicle_segments.csv        100 rows (all vehicles with RFM scores)
  rfm_summary.csv                 5 rows (per-segment statistics)
  rfm_segment_distribution.csv    5 rows (count and percentage)
  rfm_segment_distribution.png   Bar chart of vehicle count per segment
  rfm_scatter.png                 Frequency vs Volume scatter (coloured by segment)
  rfm_scores.png                  R/F/M score distribution bar charts
  rfm_insights.md                 Auto-generated operational insights
```

---

## 7. Key Features / Modules Completed

| Module | File | Purpose |
|--------|------|---------|
| Data generation | `src/data_generator.py` | 8 synthetic datasets with injected faults |
| Sensor processing | `src/sensor_processor.py` | Missing/noisy/offline handling |
| Compliance engine | `src/compliance_engine.py` | Temperature/calibration/custody/route checks |
| Evidence pack | `src/evidence_pack.py` | Multi-source evidence JOIN |
| Audit reports | `src/audit_report.py` | 500 PDF reports generated |
| Star schema ETL | `src/star_schema.py` | Analytical layer (3 dim + 4 fact tables) |
| EDA analysis | `src/eda_analysis.py` | 13 sections, 10 charts, 5 CSVs |
| RFM segmentation | `src/rfm_segmentation.py` | Vehicle asset segmentation (5 segments) |
| Dashboard | `src/dashboard.py` | Live Dash app with override form |
| Validation | `src/validate_review1.py` | Review 1 PASS/FAIL report |

---

## 8. Current Working Functionality

- ✅ PostgreSQL database with 13 operational tables
- ✅ Analytical star schema with 7 dimension/fact tables
- ✅ 500 compliance records calculated automatically
- ✅ 500 PDF audit reports generated
- ✅ Live dashboard at http://127.0.0.1:8050/
- ✅ 10 EDA visualisation charts
- ✅ RFM segmentation for all 100 fleet vehicles
- ✅ Review 1 validation: **PASS (all 38 checks)**

---

## 9. Quantitative Results

| Metric | Value |
|--------|-------|
| Total shipments processed | 500 |
| Total sensor readings | 21,125 |
| Overall compliance rate | 42.8% |
| Missing temperature readings | 46 (0.22%) |
| Missing signatures | 123 (8.1% of handovers) |
| Invalid calibrations | 33 (22% of sensors) |
| Store-and-forward recovery rate | 100% (124/124 offline readings) |
| Baseline effort reduction | ~100% (45 min manual → 0.014 sec automated) |
| Star schema tables | 7 (3 dim + 4 fact) |
| EDA plots | 10 |
| RFM segments | 5 |
| Vehicles segmented | 100 |
| Review 1 validation checks | 38 PASS / 0 FAIL |

---

## 10. Output References

| Output | Location |
|--------|----------|
| Raw datasets | `data/raw/*.csv` (8 files) |
| Processed sensor logs | `data/processed_sensor_logs.csv` |
| Compliance results | `data/compliance_results.csv` |
| Master analytical dataset | `data/etl/master_shipments.csv` |
| Star schema CSVs | `data/etl/star_schema/` (7 files) |
| EDA charts | `data/eda/plots/` (10 PNGs) |
| EDA CSVs | `data/eda/` (5 CSVs) |
| EDA insights | `data/eda/eda_insights.md` |
| RFM dataset | `data/segmentation/rfm_vehicle_segments.csv` |
| RFM plots | `data/segmentation/` (3 PNGs) |
| RFM insights | `data/segmentation/rfm_insights.md` |
| Audit PDF reports | `data/reports/` (500 PDFs) |
| Experiment HTML report | `data/experiments/experiment_report.html` |

---

## 11. Pending Work (Remaining 65%)

| Day | Topic | Weight |
|-----|-------|--------|
| Day 4 | Predictive Analytics / Forecasting | ~15% |
| Day 5 | Optimisation / Decision Support | ~15% |
| Day 6 | System Integration / Deployment | ~15% |
| Day 7 | Evaluation, Testing, Final Report | ~20% |

---

## 12. Next Steps

1. Add predictive models for temperature excursion risk
2. Integrate RFM segment data into the live dashboard
3. Add EDA tab to dashboard with embedded plots
4. Implement route optimisation module
5. Prepare final technical report

---

## 13. Conclusion

ColdChainGuard demonstrates a complete, automated cold-chain compliance system that fully satisfies the first 35% milestone requirements:

- **Day 1 (15%):** A robust ETL pipeline transforms 8 raw datasets through cleaning and integration into an analytical star-schema layer (7 tables), producing a 500-row × 37-column master dataset.
- **Day 2 (10%):** A comprehensive EDA module analyses all key variables across 13 sections, producing 10 publication-quality charts and auto-generated data-driven insights.
- **Day 3 (10%):** An operational RFM segmentation system classifies all 100 fleet vehicles into 5 actionable segments based on Recency, Frequency and Volume (adapted for cold-chain), with full visualisations and operational recommendations.

All 38 Review 1 validation checks pass.
