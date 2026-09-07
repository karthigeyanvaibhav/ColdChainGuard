# ColdChainGuard — Technical Documentation

> **Version:** 2.0  
> **Last Updated:** September 2026  
> **Stack:** Python 3.13 · PostgreSQL · Dash 4 · Plotly 7 · ReportLab 5 · SQLAlchemy 2 · Pandas 3

---

## 1. System Architecture

ColdChainGuard is a single-machine deployable Python application with three runtime layers:

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Data Layer** | PostgreSQL 14+ / CSV files | Stores all raw and processed records |
| **Processing Layer** | Python 3.13 (pandas, numpy) | Sensor processing, compliance engine, evidence builder |
| **Presentation Layer** | Dash 4 + Plotly 7 | Live interactive dashboard + PDF reports |

The system is intentionally **non-microservice**: every component is a Python script that can be run standalone or in order via `run_all.py`.

---

## 2. Module Reference

### `src/data_generator.py`
Generates the complete synthetic evaluation dataset.

| Function | Description |
|----------|-------------|
| `generate_vehicles()` | 100 refrigerated vehicles (van/truck) |
| `generate_sensors(vehicles_df)` | 150 IoT sensors assigned to vehicles |
| `generate_product_batches()` | 500 batches — 50% Frozen (−25 to −18 °C), 50% Chilled (2 to 8 °C) |
| `generate_shipments(...)` | 500 shipments with origin/destination/timestamps |
| `generate_sensor_logs(...)` | ~50,000 readings at 5-min intervals with injected faults |
| `generate_calibrations(sensors_df)` | Calibration records — 10% expired, 10% high error |
| `generate_handovers(shipments_df)` | 2–4 custody transfers per shipment, 8% missing signatures |
| `generate_route_events(shipments_df)` | Checkpoints, delays, deviations per journey |

**Injected fault rates:**
- Missing temperature: 10% of shipments
- Noisy (spike) reading: 8% of shipments
- Network offline: 8% of shipments
- Temperature excursion: 15% of shipments

---

### `src/sensor_processor.py`
Cleans and enriches raw sensor logs.

**Processing pipeline:**
1. Load raw `sensor_logs.csv` and `calibrations.csv`
2. **Missing handling:** forward-fill, then linear interpolation for gaps ≤ 30 min
3. **Noise handling:** IQR outlier capping per sensor per shipment
4. **Calibration join:** attach `calibration_valid`, `calibration_error` per sensor
5. Tag `evidence_status`: Normal / Interpolated / Capped / Recovered / Review
6. Write `data/processed_sensor_logs.csv`

---

### `src/compliance_engine.py`
Calculates per-shipment compliance decisions.

**Key constants:**
```python
WARNING_MINUTES = 5    # excursion triggers Warning flag
CRITICAL_MINUTES = 15  # excursion triggers Critical flag / Non-Compliant
NOISE_TOLERANCE = 0.5  # ±0.5 °C tolerance to absorb sensor noise
```

**Decision logic:**
```
Non-Compliant  if temperature_status == "Critical"
Non-Compliant  if calibration == Review AND custody == Review
Review         if temperature_status in ["Alert", "Warning"]
Review         if calibration == Review
Review         if custody == Review
Review         if route_status == "Deviation"
Compliant      otherwise
```

**Output columns:** `overall_compliance`, `compliance_reason`, `temperature_status`, `calibration_status`, `custody_status`, `route_status`, `route_reliability`, `sensor_reliability`, `custody_evidence_quality`

---

### `src/evidence_pack.py`
Joins all evidence sources into one record per shipment.

**Source tables joined:**
1. `shipments` — shipment master
2. `product_batches` — product and temperature requirements
3. `vehicles` — vehicle type and capacity
4. `sensor_logs` (aggregated) — temperature statistics and excursion metrics
5. `calibrations` (aggregated) — calibration validity per sensor
6. `handovers` (aggregated) — custody chain completeness
7. `route_events` (aggregated) — delay and deviation totals

**Output:** `data/evidence/compliance_evidence_pack.csv` and `.json`

---

### `src/audit_report.py`
Generates per-shipment PDF audit reports using ReportLab.

**8 report sections:**
1. Shipment Information
2. Product Information
3. Temperature Evidence
4. Calibration Evidence
5. Custody / Handover Evidence
6. Route Evidence
7. Evidence Completeness
8. Final Compliance Decision

**Output:** `data/reports/{shipment_id}_audit_report.pdf`

---

### `src/dashboard.py`
Live Dash 4 dashboard with auto-refresh and interactive override form.

**Key features:**
- **DB fallback:** Tries PostgreSQL; falls back to `compliance_results.csv` if unavailable
- **Auto-refresh:** `dcc.Interval` component refreshes data every 30 seconds
- **Radar chart:** 4-axis Plotly Scatterpolar showing Cost, Time, Emissions, Reliability
- **Override form:** Validates and writes to `dispatcher_override_history.csv` via callback
- **PDF download:** Flask route `/reports/<filename>` serves PDFs from `data/reports/`

**URL:** `http://127.0.0.1:8050/`

---

### `src/dispatcher_override.py`
Programmatic dispatcher override with full audit history.

| Function | Description |
|----------|-------------|
| `validate_override(...)` | Checks required fields and reason length |
| `apply_override(...)` | Finds shipment, records history, updates compliance |
| `save_data(...)` | Persists updated compliance + override history CSVs |
| `display_history(...)` | Prints override log to console |
| `run_demo(...)` | Demonstrates 3 overrides on first 3 shipments |

**Override record schema:**
```
override_id, shipment_id, timestamp, dispatcher,
previous_plan, new_plan, reason, override_status
```

---

### `src/store_and_forward.py`
Demonstrates offline sensor buffering and replay.

**Behaviour:**
- Identifies sensor readings with `network_status = "Offline"`
- Simulates local buffer accumulation
- Replays buffered readings through the processing pipeline on reconnect
- Measures: offline_records, forwarded_records, evidence_gap (should be 0)

---

### `src/threshold_tuning.py`
Evaluates 3 alert threshold configurations.

| Config | Warning | Critical |
|--------|---------|----------|
| Conservative | 3 min | 10 min |
| Standard (deployed) | 5 min | 15 min |
| Relaxed | 10 min | 30 min |

**Output:** `data/experiments/threshold_tuning_results.csv`, `threshold_comparison.png`

---

### `src/tradeoff_experiment.py`
Evaluates Cost × Time × Emissions × Reliability trade-off across 3 routing strategies.

**Strategies:** Standard, Express, Eco

**Scoring:** Each dimension scored 0–100. Overall = weighted average.

**Output:** `data/experiments/tradeoff_summary.csv`, `tradeoff_results.csv`, `cost_time_emissions_reliability.png`

---

### `src/baseline_experiment.py`
Compares manual vs automated compliance report assembly.

**Metrics measured:**
- Time to produce one report (baseline: 45 min, automated: ~2 min)
- Processing throughput (reports/hour)
- Error detection rate

**Output:** `data/experiments/baseline_results.csv`, `processing_time_comparison.png`

---

### `src/failure_tests.py`
Tests 4 core edge/failure cases.

| Case | Test Method | Pass Criterion |
|------|-------------|----------------|
| Missing temperature | Check interpolation in processed logs | Interpolated records > 0 |
| Invalid calibration | Check calibration status flags | invalid_calibration_sensors detected |
| Missing handover signature | Check signature_status | Missing signatures counted |
| Offline sensor | Check offline records in processed data | offline records present in pipeline |

---

### `src/experiment_notebook.py`
Generates `data/experiments/experiment_report.html` — a self-contained HTML experiment report with 8 sections, metric cards, styled tables, and analysis text. No Jupyter required.

---

### `src/data_quality.py`
Data quality assessment utilities.

- `assess_completeness(df)` — null rate per column
- `assess_temperature_range(df)` — readings within spec per shipment
- `generate_quality_report(df)` — summary statistics

---

## 3. Database Schema

### Tables (12 total)

```sql
vehicles (vehicle_id PK, vehicle_type, capacity_kg, active)
sensors (sensor_id PK, vehicle_id FK, sensor_type, installation_date, status)
sensor_logs (log_id PK BIGSERIAL, sensor_id FK, recorded_at, temperature_c, battery_level, signal_strength, network_status)
calibrations (calibration_id PK, sensor_id FK, calibration_date, expiry_date, calibration_error, status)
product_batches (batch_id PK, product_name, product_type, min_temperature_c, max_temperature_c, quantity, expiry_date)
shipments (shipment_id PK, batch_id FK, vehicle_id FK, origin, destination, departure_time, arrival_time, status)
handovers (handover_id PK, shipment_id FK, from_party, to_party, location, handover_time, signature_status)
route_events (event_id PK, shipment_id FK, event_type, location, event_time, duration_minutes)
compliance_events (compliance_event_id PK, shipment_id FK, event_type, severity, description, detected_at, automated_decision, status)
dispatcher_overrides (override_id PK, shipment_id FK, compliance_event_id FK, dispatcher, original_decision, new_decision, reason, override_time)
plan_change_history (change_id PK, shipment_id FK, changed_by, change_type, previous_value, new_value, reason, changed_at)
audit_reports (report_id PK, shipment_id FK, generated_at, final_decision, evidence_completeness, report_file_path)
```

---

## 4. Configuration

### Environment Variables (`.env`)

```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=coldchainguard
DB_USER=postgres
DB_PASSWORD=your_password
```

Override DB password without editing `.env`:
```bash
set COLDCHAINGUARD_DB_PASSWORD=mypassword   # Windows
export COLDCHAINGUARD_DB_PASSWORD=mypassword # Linux/Mac
```

### Compliance Thresholds (`compliance_engine.py`)

```python
WARNING_MINUTES = 5    # change to tune Warning threshold
CRITICAL_MINUTES = 15  # change to tune Critical threshold
NOISE_TOLERANCE = 0.5  # ±°C tolerance
```

---

## 5. Deployment

### Local Deployment (Single Machine)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up PostgreSQL (optional)
createdb coldchainguard
psql coldchainguard < database/schema.sql

# 3. Run full pipeline
python run_all.py

# 4. Or run without PostgreSQL
python run_all.py --skip-db

# 5. Launch dashboard
python src/dashboard.py
```

### Production Notes

- Dashboard is a **development server** (`debug=True`). For production, deploy with Gunicorn:
  ```bash
  gunicorn src.dashboard:server -b 0.0.0.0:8050
  ```
- PDFs are served via Flask's `send_from_directory` — safe for local use, add authentication for production.
- All data is local CSV/PostgreSQL — no cloud dependencies.

---

## 6. Data Files Reference

| File | Location | Description |
|------|----------|-------------|
| `sensor_logs.csv` | `data/raw/` | Raw IoT readings |
| `calibrations.csv` | `data/raw/` | Sensor calibration certs |
| `handovers.csv` | `data/raw/` | Custody transfer records |
| `route_events.csv` | `data/raw/` | Route checkpoints and events |
| `product_batches.csv` | `data/raw/` | Product temperature specs |
| `shipments.csv` | `data/raw/` | Shipment master |
| `vehicles.csv` | `data/raw/` | Fleet registry |
| `sensors.csv` | `data/raw/` | Sensor registry |
| `processed_sensor_logs.csv` | `data/` | Cleaned, enriched sensor data |
| `compliance_results.csv` | `data/` | Per-shipment compliance decisions |
| `compliance_evidence_pack.csv` | `data/evidence/` | Full joined evidence |
| `compliance_evidence_pack.json` | `data/evidence/` | JSON version of evidence pack |
| `SHP####_audit_report.pdf` | `data/reports/` | Per-shipment PDF reports |
| `experiment_report.html` | `data/experiments/` | HTML experiment analysis |
| `tradeoff_summary.csv` | `data/experiments/` | Trade-off scores |
| `baseline_results.csv` | `data/experiments/` | Baseline measurements |
| `threshold_tuning_results.csv` | `data/experiments/` | Threshold comparison |
| `store_and_forward_metrics.csv` | `data/experiments/` | S&F buffer metrics |
| `failure_mode_results.csv` | `data/experiments/` | Edge case test results |
| `dispatcher_override_history.csv` | `data/experiments/` | Override audit log |
