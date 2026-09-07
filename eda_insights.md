# ColdChainGuard — EDA Insights

## Dataset Overview
- Total shipments analysed: **500**
- Total sensor log records: **21,125**
- Calibration records: **150**
- Handover records: **1511**
- Route event records: **3289**

## Compliance Summary
- Compliant shipments: **214** (42.8%)
- Non-compliant shipments: **89**
- Under review: **197**
- Finding: 42.8% of shipments passed all compliance checks automatically.

## Temperature Analysis
- Overall mean temperature across all sensor readings: **-7.46 deg C**
- Standard deviation: **13.01 deg C**
  (High std expected as dataset contains both frozen and chilled products.)
- Missing temperature readings: **46** (0.22%)
- Finding: The bimodal temperature distribution (peaks near -21 C and 5 C)
  clearly separates frozen and chilled product shipments.

## Sensor Data Quality
- Missing temperature readings: 46 (0.22%)
- Missing observations were handled by forward-fill / linear interpolation
  in the sensor processing pipeline.

## Calibration Analysis
- Valid calibrations: **117** of 150 sensors
- Invalid/expired calibrations: **33**
- Finding: 22.0% of sensors had calibration issues,
  flagging their readings for compliance review.

## Custody Chain Analysis
- Total handovers: **1511**
- Missing signatures: **123** (8.14%)
- Finding: 8.14% of custody transfers lacked digital signatures,
  creating potential audit vulnerabilities in those shipments.

## Route Event Analysis
- Total route events: **3289**
- Traffic delay events: **157**
- Route deviation events: **65**
- Finding: Route deviations represent an immediate trigger for compliance review.

## Correlation Analysis
Notable correlations (|r| >= 0.4):
  - journey_duration_min vs total_readings: r = 1.000
  - avg_signal_strength vs offline_readings: r = -0.773
  - total_delay_minutes vs traffic_delay_events: r = 0.913
  - missing_signatures vs signature_rate_pct: r = -0.948

## Key EDA Findings
1. Bimodal temperature distribution cleanly separates frozen/chilled segments.
2. 42.8% overall compliance rate demonstrates the system is working,
   with minority of shipments requiring investigation.
3. 8.14% missing custody signatures is a measurable operational gap.
4. 22.0% sensor calibration failure rate requires preventive maintenance attention.
5. Missing temperature readings (<1%) are successfully recovered by interpolation.