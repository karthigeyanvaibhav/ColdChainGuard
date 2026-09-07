# ColdChainGuard — Field-Workflow Map

> **Deliverable:** Field-workflow map showing the complete data and decision flow from IoT sensor to audit-ready compliance report.

---

## End-to-End Workflow

```
┌──────────────────────────────────────────────────────────────────────────┐
│                     COLD-CHAIN PHYSICAL ENVIRONMENT                       │
│                                                                            │
│   Refrigerated Van / Truck                                                 │
│   ┌─────────────────────────────────────────────────────────────────┐     │
│   │  IoT Temperature Sensor (S001–S150)                              │     │
│   │  • Reads every 5 minutes                                         │     │
│   │  • Records: temperature_c, battery_level, signal_strength,      │     │
│   │             network_status, timestamp                            │     │
│   │                                                                  │     │
│   │  NORMAL:    → sends immediately over 4G/WiFi                    │     │
│   │  OFFLINE:   → buffers to local flash memory (store-and-forward) │     │
│   └────────────────────────┬────────────────────────────────────────┘     │
│                             │                                              │
│   Handover Points (2–4 per journey)                                        │
│   ┌─────────────────────────▼────────────────────────────────────────┐    │
│   │  Custody Transfer Record                                          │    │
│   │  from_party → to_party, location, timestamp, signature           │    │
│   └─────────────────────────┬────────────────────────────────────────┘    │
└─────────────────────────────┼──────────────────────────────────────────────┘
                              │
                    ┌─────────▼──────────┐
                    │   NETWORK LAYER     │
                    │   4G / WiFi / Batch │
                    │   forward on recon- │
                    │   nect if offline   │
                    └─────────┬──────────┘
                              │
┌─────────────────────────────▼──────────────────────────────────────────────┐
│                        DATA INGESTION                                       │
│                                                                             │
│   sensor_processor.py                                                       │
│   ┌─────────────────────────────────────────────────────────────────┐      │
│   │  1. Receive raw sensor_logs (CSV / DB insert)                    │      │
│   │  2. Detect MISSING observations → forward-fill / linear interp  │      │
│   │  3. Detect NOISY readings → IQR outlier capping                  │      │
│   │  4. Attach calibration validity (calibration_valid, error)       │      │
│   │  5. Tag evidence_status: Normal / Interpolated / Recovered /    │      │
│   │     Review / Offline                                             │      │
│   │  6. Write processed_sensor_logs.csv                              │      │
│   └─────────────────────────┬───────────────────────────────────────┘      │
└─────────────────────────────┼──────────────────────────────────────────────┘
                              │
┌─────────────────────────────▼──────────────────────────────────────────────┐
│                     POSTGRESQL DATABASE                                      │
│                                                                             │
│   Tables: vehicles, sensors, sensor_logs, calibrations, product_batches,   │
│            shipments, handovers, route_events, compliance_events,           │
│            dispatcher_overrides, plan_change_history, audit_reports         │
└─────────────────────────────┬──────────────────────────────────────────────┘
                              │
┌─────────────────────────────▼──────────────────────────────────────────────┐
│                      COMPLIANCE ENGINE                                       │
│                                                                             │
│   compliance_engine.py                                                      │
│   ┌─────────────────────────────────────────────────────────────────┐      │
│   │  Per Shipment:                                                    │      │
│   │                                                                   │      │
│   │  ① Temperature Check                                              │      │
│   │     • Excursion duration (minutes out of range)                   │      │
│   │     • Noise tolerance: ±0.5 °C                                    │      │
│   │     • Status: Compliant / Warning (≤5min) / Alert (≤15min) /     │      │
│   │              Critical (>15min)                                    │      │
│   │                                                                   │      │
│   │  ② Calibration Check                                              │      │
│   │     • Is sensor calibration certificate valid?                    │      │
│   │     • Is calibration within expiry date during shipment?          │      │
│   │     • Status: Valid / Review                                      │      │
│   │                                                                   │      │
│   │  ③ Custody / Handover Check                                       │      │
│   │     • Are all custody transfers signed?                           │      │
│   │     • Status: Complete / Review (if any Missing signature)        │      │
│   │                                                                   │      │
│   │  ④ Route Check                                                    │      │
│   │     • Route deviations: Deviation / Delayed / Normal              │      │
│   │     • Route reliability: High / Moderate / Low                    │      │
│   │                                                                   │      │
│   │  ⑤ Final Decision                                                 │      │
│   │     • Non-Compliant: Critical temp OR (calib+custody both Review) │      │
│   │     • Review: Alert/Warning temp OR calib issue OR custody issue  │      │
│   │               OR route deviation                                  │      │
│   │     • Compliant: All checks pass                                  │      │
│   └─────────────────────────┬───────────────────────────────────────┘      │
└─────────────────────────────┼──────────────────────────────────────────────┘
                              │
┌─────────────────────────────▼──────────────────────────────────────────────┐
│                      EVIDENCE PACK BUILDER                                   │
│                                                                             │
│   evidence_pack.py                                                          │
│   ┌─────────────────────────────────────────────────────────────────┐      │
│   │  JOIN: shipment + product_batch + vehicle + sensor_summary +    │      │
│   │        calibration_summary + custody_summary + route_summary    │      │
│   │                                                                  │      │
│   │  OUTPUT: compliance_evidence_pack.csv / .json                   │      │
│   │          One row per shipment, all evidence fields included      │      │
│   └─────────────────────────┬───────────────────────────────────────┘      │
└─────────────────────────────┼──────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              │                               │
┌─────────────▼─────────────┐   ┌────────────▼──────────────────────────────┐
│    AUDIT PDF REPORTS       │   │         LIVE DASHBOARD                     │
│                            │   │                                            │
│  audit_report.py           │   │  dashboard.py                             │
│  • One PDF per shipment    │   │  • KPI cards                              │
│  • 8 evidence sections:    │   │  • Compliance distribution pie             │
│    1. Shipment info        │   │  • Temperature / Sensor / Custody /       │
│    2. Product info         │   │    Route / Exception charts               │
│    3. Temperature evidence │   │  • Radar trade-off chart                  │
│    4. Calibration evidence │   │  • PDF download per shipment              │
│    5. Custody evidence     │   │  • Override form + history table          │
│    6. Route evidence       │   │  • 30-second auto-refresh                 │
│    7. Evidence completeness│   │  • CSV fallback if DB unavailable         │
│    8. Compliance decision  │   └────────────────────────────────────────────┘
└────────────────────────────┘
              │
┌─────────────▼──────────────────────────────────────────────────────────────┐
│                      DISPATCHER OVERRIDE                                     │
│                                                                             │
│   dispatcher_override.py / dashboard override form                          │
│   ┌─────────────────────────────────────────────────────────────────┐      │
│   │  Dispatcher can change route plan for any shipment              │      │
│   │  • Requires: shipment_id, new_plan, dispatcher_name, reason     │      │
│   │  • Creates immutable override record with UUID + timestamp      │      │
│   │  • Full audit history preserved in dispatcher_override_history  │      │
│   │  • Every plan change requires documented reason (≥5 chars)      │      │
│   └──────────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Summary

| Stage | Input | Process | Output |
|-------|-------|---------|--------|
| 1. Sensor | Physical temperature | IoT device reads every 5 min | Raw sensor_logs.csv |
| 2. Ingest | Raw sensor_logs | Handle missing/noisy, attach calibration | processed_sensor_logs.csv |
| 3. Store | processed_sensor_logs | PostgreSQL load | 12-table database |
| 4. Compliance | DB tables | Excursion calc, calibration, custody, route checks | compliance_results.csv |
| 5. Evidence | compliance_results | JOIN all 6 sources | compliance_evidence_pack.csv/.json |
| 6. Report | evidence_pack | ReportLab PDF generation | data/reports/SHP####_audit_report.pdf |
| 7. Dashboard | DB + CSVs | Dash live rendering | http://127.0.0.1:8050/ |
| 8. Override | Dashboard form | Validate + append to history | dispatcher_override_history.csv |

---

## Exception Paths

```
Missing temperature reading
  └─→ Forward-fill from previous valid reading
  └─→ Linear interpolation if gap ≤ 30 min
  └─→ evidence_status = "Interpolated"
  └─→ Flag in audit report

Sensor offline (store-and-forward)
  └─→ Device buffers readings to local memory
  └─→ On reconnect: batch-forward all buffered readings
  └─→ Processing pipeline handles them identically to live readings
  └─→ evidence_status = "Recovered"

Noisy / spike reading
  └─→ IQR-based outlier detection per sensor per shipment
  └─→ Values clipped to [Q1 - 1.5×IQR, Q3 + 1.5×IQR]
  └─→ evidence_status = "Capped"
  └─→ Original value preserved in raw_temperature field

Invalid calibration
  └─→ calibration_valid = False for that sensor
  └─→ All readings from that sensor tagged evidence_status = "Review"
  └─→ sensor_reliability = "Review" in compliance decision

Missing handover signature
  └─→ custody_evidence_quality = "Incomplete"
  └─→ Flags for compliance review
  └─→ Included in audit report as unresolved custody gap
```

---

## Actors and Responsibilities

| Actor | Role | System Interaction |
|-------|------|--------------------|
| IoT Sensor | Capture temperature data | Writes sensor_logs |
| Delivery Driver | Signs custody handovers | Creates handover records |
| Dispatcher | Monitors shipments, approves overrides | Uses dashboard override form |
| Compliance Officer | Reviews flagged shipments | Downloads PDF audit reports |
| System (ColdChainGuard) | Automated evidence assembly | Runs full pipeline automatically |
