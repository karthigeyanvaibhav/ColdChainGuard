import os
import sys
import json
import pandas as pd

from sqlalchemy import text


# ==========================================================
# PROJECT ROOT
# ==========================================================

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

sys.path.append(PROJECT_ROOT)


from database.connection import engine


# ==========================================================
# OUTPUT DIRECTORY
# ==========================================================

OUTPUT_DIR = os.path.join(
    PROJECT_ROOT,
    "data",
    "evidence"
)

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


# ==========================================================
# LOAD COMPLETE EVIDENCE
# ==========================================================

def load_evidence_data():

    query = text("""
        SELECT

            -- =================================================
            -- SHIPMENT
            -- =================================================

            s.shipment_id,
            s.batch_id,
            s.vehicle_id,
            s.origin,
            s.destination,
            s.departure_time,
            s.arrival_time,
            s.status AS shipment_status,

            -- =================================================
            -- PRODUCT
            -- =================================================

            pb.product_name,
            pb.product_type,
            pb.min_temperature_c,
            pb.max_temperature_c,
            pb.quantity,
            pb.expiry_date,

            -- =================================================
            -- VEHICLE
            -- =================================================

            v.vehicle_type,
            v.capacity_kg,

            -- =================================================
            -- COMPLIANCE RESULT
            -- =================================================

            cr.temperature_status,
            cr.calibration_status,
            cr.custody_status,
            cr.route_status,

            cr.total_sensor_records,
            cr.excursion_records,
            cr.total_excursion_minutes,

            cr.overall_compliance,
            cr.compliance_reason

        FROM shipments s

        LEFT JOIN product_batches pb
            ON s.batch_id = pb.batch_id

        LEFT JOIN vehicles v
            ON s.vehicle_id = v.vehicle_id

        LEFT JOIN compliance_results cr
            ON s.shipment_id = cr.shipment_id

        ORDER BY s.shipment_id;
    """)

    with engine.connect() as conn:

        df = pd.read_sql(
            query,
            conn
        )

    return df


# ==========================================================
# SENSOR EVIDENCE
# ==========================================================

def get_sensor_evidence():

    query = text("""
        SELECT

            sl.shipment_id,

            COUNT(*) AS total_raw_sensor_records,

            COUNT(
                sl.temperature_c
            ) AS available_temperature_records,

            COUNT(*) -
            COUNT(sl.temperature_c)
            AS missing_temperature_records,

            SUM(
                CASE
                    WHEN sl.network_status = 'Offline'
                    THEN 1
                    ELSE 0
                END
            ) AS offline_observations,

            AVG(sl.temperature_c)
            AS raw_average_temperature,

            MIN(sl.temperature_c)
            AS raw_min_temperature,

            MAX(sl.temperature_c)
            AS raw_max_temperature,

            MIN(sl.battery_level)
            AS minimum_battery_level,

            MIN(sl.signal_strength)
            AS minimum_signal_strength

        FROM sensor_logs sl

        GROUP BY sl.shipment_id
        ORDER BY sl.shipment_id;
    """)

    with engine.connect() as conn:

        df = pd.read_sql(
            query,
            conn
        )

    return df


# ==========================================================
# CALIBRATION EVIDENCE
# ==========================================================

def get_calibration_evidence():

    query = text("""
        SELECT

            sl.shipment_id,

            COUNT(
                DISTINCT sl.sensor_id
            ) AS sensors_used,

            COUNT(
                DISTINCT CASE
                    WHEN c.status = 'Valid'
                    THEN sl.sensor_id
                END
            ) AS valid_calibration_sensors,

            COUNT(
                DISTINCT CASE
                    WHEN c.status != 'Valid'
                    THEN sl.sensor_id
                END
            ) AS invalid_calibration_sensors,

            MAX(
                c.calibration_error
            ) AS maximum_calibration_error,

            AVG(
                c.calibration_error
            ) AS average_calibration_error

        FROM sensor_logs sl

        LEFT JOIN calibrations c
            ON sl.sensor_id = c.sensor_id

        GROUP BY sl.shipment_id
        ORDER BY sl.shipment_id;
    """)

    with engine.connect() as conn:

        df = pd.read_sql(
            query,
            conn
        )

    return df


# ==========================================================
# CUSTODY EVIDENCE
# ==========================================================

def get_custody_evidence():

    query = text("""
        SELECT

            shipment_id,

            COUNT(*) AS total_handovers,

            SUM(
                CASE
                    WHEN signature_status = 'Signed'
                    THEN 1
                    ELSE 0
                END
            ) AS signed_handovers,

            SUM(
                CASE
                    WHEN signature_status = 'Missing'
                    THEN 1
                    ELSE 0
                END
            ) AS missing_handover_signatures,

            STRING_AGG(
                location,
                ' -> '
                ORDER BY handover_time
            ) AS custody_locations

        FROM handovers

        GROUP BY shipment_id
        ORDER BY shipment_id;
    """)

    with engine.connect() as conn:

        df = pd.read_sql(
            query,
            conn
        )

    return df


# ==========================================================
# ROUTE EVIDENCE
# ==========================================================

def get_route_evidence():

    query = text("""
        SELECT

            shipment_id,

            COUNT(*) AS total_route_events,

            SUM(
                CASE
                    WHEN event_type = 'Traffic Delay'
                    THEN 1
                    ELSE 0
                END
            ) AS traffic_delay_events,

            SUM(
                CASE
                    WHEN event_type = 'Route Deviation'
                    THEN 1
                    ELSE 0
                END
            ) AS route_deviation_events,

            SUM(
                duration_minutes
            ) AS total_route_event_minutes,

            SUM(
                CASE
                    WHEN event_type = 'Traffic Delay'
                    THEN duration_minutes
                    ELSE 0
                END
            ) AS traffic_delay_minutes,

            SUM(
                CASE
                    WHEN event_type = 'Route Deviation'
                    THEN duration_minutes
                    ELSE 0
                END
            ) AS route_deviation_minutes

        FROM route_events

        GROUP BY shipment_id
        ORDER BY shipment_id;
    """)

    with engine.connect() as conn:

        df = pd.read_sql(
            query,
            conn
        )

    return df


# ==========================================================
# CREATE EVIDENCE PACK
# ==========================================================

def create_evidence_pack():

    print("=" * 70)
    print("COLDCHAINGUARD - AUTOMATED COMPLIANCE EVIDENCE PACK")
    print("=" * 70)

    # ------------------------------------------------------
    # Load evidence
    # ------------------------------------------------------

    print("\nLoading shipment evidence...")

    main_df = load_evidence_data()

    print(
        f"Shipments loaded: {len(main_df)}"
    )

    # ------------------------------------------------------
    # Sensor evidence
    # ------------------------------------------------------

    print(
        "Loading sensor evidence..."
    )

    sensor_df = get_sensor_evidence()

    # ------------------------------------------------------
    # Calibration evidence
    # ------------------------------------------------------

    print(
        "Loading calibration evidence..."
    )

    calibration_df = get_calibration_evidence()

    # ------------------------------------------------------
    # Custody evidence
    # ------------------------------------------------------

    print(
        "Loading custody evidence..."
    )

    custody_df = get_custody_evidence()

    # ------------------------------------------------------
    # Route evidence
    # ------------------------------------------------------

    print(
        "Loading route evidence..."
    )

    route_df = get_route_evidence()

    # ------------------------------------------------------
    # Merge evidence
    # ------------------------------------------------------

    evidence = main_df.merge(
        sensor_df,
        on="shipment_id",
        how="left"
    )

    evidence = evidence.merge(
        calibration_df,
        on="shipment_id",
        how="left"
    )

    evidence = evidence.merge(
        custody_df,
        on="shipment_id",
        how="left"
    )

    evidence = evidence.merge(
        route_df,
        on="shipment_id",
        how="left"
    )

    # ------------------------------------------------------
    # Fill missing values
    # ------------------------------------------------------

    numeric_columns = [
        "total_raw_sensor_records",
        "available_temperature_records",
        "missing_temperature_records",
        "offline_observations",
        "minimum_battery_level",
        "minimum_signal_strength",
        "sensors_used",
        "valid_calibration_sensors",
        "invalid_calibration_sensors",
        "maximum_calibration_error",
        "average_calibration_error",
        "total_handovers",
        "signed_handovers",
        "missing_handover_signatures",
        "total_route_events",
        "traffic_delay_events",
        "route_deviation_events",
        "total_route_event_minutes",
        "traffic_delay_minutes",
        "route_deviation_minutes"
    ]

    for column in numeric_columns:

        if column in evidence.columns:

            evidence[column] = (
                pd.to_numeric(
                    evidence[column],
                    errors="coerce"
                )
                .fillna(0)
            )

    # ------------------------------------------------------
    # Evidence completeness
    # ------------------------------------------------------

    evidence["evidence_completeness"] = (
        (
            evidence["total_raw_sensor_records"] > 0
        ).astype(int)

        +

        (
            evidence["sensors_used"] > 0
        ).astype(int)

        +

        (
            evidence["total_handovers"] > 0
        ).astype(int)

        +

        (
            evidence["total_route_events"] > 0
        ).astype(int)
    )

    evidence["evidence_completeness_percent"] = (
        evidence["evidence_completeness"]
        / 4
        * 100
    )

    # ------------------------------------------------------
    # Sensor reliability
    # ------------------------------------------------------

    def sensor_reliability(row):

        if row["invalid_calibration_sensors"] > 0:

            return "Review"

        if row["missing_temperature_records"] > 0:

            return "Partial"

        if row["offline_observations"] > 0:

            return "Partial"

        return "Reliable"

    evidence["sensor_reliability"] = (
        evidence.apply(
            sensor_reliability,
            axis=1
        )
    )

    # ------------------------------------------------------
    # Custody evidence quality
    # ------------------------------------------------------

    def custody_evidence_quality(row):

        if row["missing_handover_signatures"] > 0:

            return "Incomplete"

        if row["total_handovers"] == 0:

            return "Unavailable"

        return "Complete"

    evidence["custody_evidence_quality"] = (
        evidence.apply(
            custody_evidence_quality,
            axis=1
        )
    )

    # ------------------------------------------------------
    # Route reliability
    # ------------------------------------------------------

    def route_reliability(row):

        if row["route_deviation_events"] > 0:

            return "Low"

        if row["traffic_delay_events"] > 0:

            return "Moderate"

        return "High"

    evidence["route_reliability"] = (
        evidence.apply(
            route_reliability,
            axis=1
        )
    )

    # ------------------------------------------------------
    # Audit conclusion
    # ------------------------------------------------------

    def audit_conclusion(row):

        status = row["overall_compliance"]

        if status == "Compliant":

            return (
                "Shipment passed the automated "
                "compliance checks."
            )

        if status == "Review":

            return (
                "Shipment requires auditor review "
                "because one or more evidence "
                "sources contain exceptions."
            )

        return (
            "Shipment is non-compliant based on "
            "critical compliance evidence."
        )

    evidence["audit_conclusion"] = (
        evidence.apply(
            audit_conclusion,
            axis=1
        )
    )

    # ------------------------------------------------------
    # Reorder columns
    # ------------------------------------------------------

    preferred_columns = [

        # Shipment
        "shipment_id",
        "batch_id",
        "vehicle_id",
        "origin",
        "destination",
        "departure_time",
        "arrival_time",
        "shipment_status",

        # Product
        "product_name",
        "product_type",
        "min_temperature_c",
        "max_temperature_c",
        "quantity",
        "expiry_date",

        # Vehicle
        "vehicle_type",
        "capacity_kg",

        # Sensor
        "total_raw_sensor_records",
        "available_temperature_records",
        "missing_temperature_records",
        "offline_observations",
        "raw_average_temperature",
        "raw_min_temperature",
        "raw_max_temperature",
        "minimum_battery_level",
        "minimum_signal_strength",
        "sensor_reliability",

        # Temperature compliance
        "total_sensor_records",
        "excursion_records",
        "total_excursion_minutes",
        "temperature_status",

        # Calibration
        "sensors_used",
        "valid_calibration_sensors",
        "invalid_calibration_sensors",
        "maximum_calibration_error",
        "average_calibration_error",
        "calibration_status",

        # Custody
        "total_handovers",
        "signed_handovers",
        "missing_handover_signatures",
        "custody_locations",
        "custody_evidence_quality",
        "custody_status",

        # Route
        "total_route_events",
        "traffic_delay_events",
        "traffic_delay_minutes",
        "route_deviation_events",
        "route_deviation_minutes",
        "total_route_event_minutes",
        "route_reliability",
        "route_status",

        # Final
        "overall_compliance",
        "compliance_reason",
        "audit_conclusion",

        # Evidence completeness
        "evidence_completeness",
        "evidence_completeness_percent"
    ]

    # Only select columns that actually exist
    preferred_columns = [
        column
        for column in preferred_columns
        if column in evidence.columns
    ]

    evidence = evidence[
        preferred_columns
    ]

    return evidence


# ==========================================================
# SAVE CSV
# ==========================================================

def save_csv(evidence):

    output_path = os.path.join(
        OUTPUT_DIR,
        "compliance_evidence_pack.csv"
    )

    evidence.to_csv(
        output_path,
        index=False
    )

    print(
        f"\nCSV saved:\n{output_path}"
    )


# ==========================================================
# SAVE JSON
# ==========================================================

def save_json(evidence):

    output_path = os.path.join(
        OUTPUT_DIR,
        "compliance_evidence_pack.json"
    )

    records = evidence.copy()

    # Convert timestamps to strings
    for column in records.columns:

        if pd.api.types.is_datetime64_any_dtype(
            records[column]
        ):

            records[column] = (
                records[column]
                .dt.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            )

    # Convert NaN to None
    records = records.where(
        pd.notnull(records),
        None
    )

    data = records.to_dict(
        orient="records"
    )

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            indent=4,
            default=str
        )

    print(
        f"JSON saved:\n{output_path}"
    )


# ==========================================================
# DISPLAY SUMMARY
# ==========================================================

def display_summary(evidence):

    print("\n")
    print("=" * 70)
    print("EVIDENCE PACK SUMMARY")
    print("=" * 70)

    print(
        f"\nTotal shipments : "
        f"{len(evidence)}"
    )

    print("\nOverall Compliance")
    print("-" * 40)

    print(
        evidence[
            "overall_compliance"
        ].value_counts()
    )

    print("\nSensor Reliability")
    print("-" * 40)

    print(
        evidence[
            "sensor_reliability"
        ].value_counts()
    )

    print("\nCustody Evidence")
    print("-" * 40)

    print(
        evidence[
            "custody_evidence_quality"
        ].value_counts()
    )

    print("\nRoute Reliability")
    print("-" * 40)

    print(
        evidence[
            "route_reliability"
        ].value_counts()
    )

    print("\nEvidence Completeness")
    print("-" * 40)

    print(
        evidence[
            "evidence_completeness_percent"
        ].value_counts()
        .sort_index()
    )


# ==========================================================
# MAIN
# ==========================================================

def main():

    try:

        evidence = create_evidence_pack()

        display_summary(
            evidence
        )

        save_csv(
            evidence
        )

        save_json(
            evidence
        )

        print("\n")
        print("=" * 70)
        print("EVIDENCE PACK GENERATED SUCCESSFULLY")
        print("=" * 70)

    except Exception as e:

        print("\n")
        print("=" * 70)
        print("EVIDENCE PACK GENERATION FAILED")
        print("=" * 70)

        print(
            f"\nError: {e}"
        )

        raise


# ==========================================================
# RUN
# ==========================================================

if __name__ == "__main__":

    main()