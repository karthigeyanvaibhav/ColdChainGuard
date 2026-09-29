# ColdChainGuard -- Day 9: Cohort & Retention Analysis

## Analogue Mapping

| Official Requirement | ColdChainGuard Implementation |
|----------------------|-------------------------------|
| Cohort & Retention (Day 9) | Vehicle Compliance-Retention Cohort Analysis |
| Customer cohorts by acquisition date | Vehicle cohorts by first-shipment quarter |
| Retention = customer re-purchases | Retention = vehicle had compliant shipment |
| Period = calendar month | Period = operational quarter |

**Rationale:** In retail, cohort analysis reveals whether recently acquired customers
retain buying behaviour over time. In ColdChainGuard, the analogous question is:
'Do vehicles first deployed in the same quarter maintain compliance performance?'
This reveals fleet quality trends, helps identify deteriorating cohorts early, and
supports targeted maintenance scheduling.

## Vehicle Compliance-Retention Cohort Matrix

Rows = quarter in which each vehicle made its first shipment.
Columns = operational quarter offset (Q+0 = debut quarter).
Cell value = fraction of cohort vehicles that had at least one COMPLIANT shipment.

| Cohort | Cohort Size | Q+0 |
|--------|-------------|---|
| 2026Q3 | 76 | 88% |

## Key Insights

- Mean first-quarter compliance retention: 88%
- Best-performing cohort (Q+0 retention): 2026Q3 (88%)
- Worst-performing cohort (Q+0 retention): 2026Q3 (88%)

## Sensor Calibration Survival

Rows = month sensors were installed. Columns = fraction with valid calibration
after 1, 3, 6, 12 months from installation.

| Cohort | Size | MM01 | MM03 | MM06 | MM12 |
|--------|------|---|---|---|---|
| 2025-01 | 8 | 100% | 100% | 100% | 100% |
| 2025-02 | 7 | 100% | 100% | 100% | 100% |
| 2025-03 | 12 | 100% | 100% | 100% | 100% |
| 2025-04 | 13 | 100% | 100% | 100% | 100% |
| 2025-05 | 13 | 100% | 100% | 100% | 100% |
| 2025-06 | 10 | 100% | 100% | 100% | 100% |
| 2025-07 | 7 | 100% | 100% | 100% | 100% |
| 2025-08 | 10 | 100% | 100% | 100% | 90% |
| 2025-09 | 5 | 100% | 100% | 100% | 100% |
| 2025-10 | 13 | 100% | 100% | 100% | 92% |
| 2025-11 | 6 | 100% | 100% | 100% | 100% |
| 2025-12 | 6 | 100% | 100% | 100% | 83% |
| 2026-01 | 7 | 100% | 100% | 100% | 86% |
| 2026-02 | 7 | 100% | 100% | 86% | 43% |
| 2026-03 | 13 | 100% | 100% | 77% | 0% |
| 2026-04 | 9 | 100% | 100% | 100% | 0% |
| 2026-05 | 4 | 100% | 75% | 75% | 0% |

## Outputs

- `vehicle_cohort_matrix.csv` — retention rates by cohort and quarter
- `sensor_survival_matrix.csv` — calibration survival by installation cohort
- `cohort_heatmap_vehicle.png` — vehicle retention heatmap
- `cohort_heatmap_sensor.png` — sensor survival heatmap

## Operational Use

1. Cohorts with declining Q+1/Q+2 retention → schedule proactive maintenance
2. Sensor cohorts with low M06 survival → accelerate recalibration programme
3. Compliance-retention trend across all cohorts → measure systemic improvement