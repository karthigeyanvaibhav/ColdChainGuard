import pandas as pd
import numpy as np


# ==========================================================
# CONFIGURATION
# ==========================================================

WARNING_MINUTES = 5
CRITICAL_MINUTES = 15

NOISE_TOLERANCE = 0.5


# ==========================================================
# LOAD DATA
# ==========================================================

def load_data():

    sensor_logs = pd.read_csv(
        "data/processed_sensor_logs.csv",
        parse_dates=["recorded_at"]
    )

    shipments = pd.read_csv(
        "data/raw/shipments.csv",
        parse_dates=[
            "departure_time",
            "arrival_time"
        ]
    )

    batches = pd.read_csv(
        "data/raw/product_batches.csv"
    )

    calibrations = pd.read_csv(
        "data/raw/calibrations.csv",
        parse_dates=[
            "calibration_date",
            "expiry_date"
        ]
    )

    handovers = pd.read_csv(
        "data/raw/handovers.csv",
        parse_dates=["handover_time"]
    )

    route_events = pd.read_csv(
        "data/raw/route_events.csv",
        parse_dates=["event_time"]
    )

    return (
        sensor_logs,
        shipments,
        batches,
        calibrations,
        handovers,
        route_events
    )


# ==========================================================
# TEMPERATURE COMPLIANCE
# ==========================================================

def calculate_temperature_compliance(sensor_logs):

    # Check whether temperature is available
    sensor_logs["temperature_available"] = (
        sensor_logs["temperature_c"].notna()
    )

    # Small tolerance to prevent tiny sensor fluctuations
    sensor_logs["within_range"] = (
        sensor_logs["temperature_c"]
        >=
        sensor_logs["min_temperature_c"]
        - NOISE_TOLERANCE
    ) & (
        sensor_logs["temperature_c"]
        <=
        sensor_logs["max_temperature_c"]
        + NOISE_TOLERANCE
    )

    # Out-of-range observation
    sensor_logs["temperature_excursion"] = (
        sensor_logs["temperature_available"]
        &
        ~sensor_logs["within_range"]
    )

    return sensor_logs


# ==========================================================
# CALCULATE EXCURSION DURATION
# ==========================================================

def calculate_excursion_duration(sensor_logs):

    sensor_logs = sensor_logs.sort_values(
        [
            "shipment_id",
            "sensor_id",
            "recorded_at"
        ]
    )

    sensor_logs["previous_time"] = (
        sensor_logs
        .groupby(
            [
                "shipment_id",
                "sensor_id"
            ]
        )["recorded_at"]
        .shift(1)
    )

    sensor_logs["interval_minutes"] = (
        (
            sensor_logs["recorded_at"]
            -
            sensor_logs["previous_time"]
        )
        .dt.total_seconds()
        / 60
    )

    # Prevent unrealistic gaps from being counted
    sensor_logs["interval_minutes"] = (
        sensor_logs["interval_minutes"]
        .clip(
            lower=0,
            upper=15
        )
        .fillna(0)
    )

    sensor_logs["excursion_minutes"] = np.where(
        sensor_logs["temperature_excursion"],
        sensor_logs["interval_minutes"],
        0
    )

    return sensor_logs


# ==========================================================
# SHIPMENT TEMPERATURE SUMMARY
# ==========================================================

def summarize_temperature(sensor_logs):

    temperature_summary = (
        sensor_logs
        .groupby("shipment_id")
        .agg(
            total_sensor_records=(
                "temperature_c",
                "count"
            ),

            excursion_records=(
                "temperature_excursion",
                "sum"
            ),

            total_excursion_minutes=(
                "excursion_minutes",
                "sum"
            ),

            max_temperature=(
                "temperature_c",
                "max"
            ),

            min_temperature=(
                "temperature_c",
                "min"
            ),

            average_temperature=(
                "temperature_c",
                "mean"
            ),

            review_records=(
                "evidence_status",
                lambda x: (x == "Review").sum()
            ),

            recovered_records=(
                "evidence_status",
                lambda x: (x == "Recovered").sum()
            )
        )
        .reset_index()
    )

    # ------------------------------------------------------
    # Temperature status
    # ------------------------------------------------------

    def temperature_status(minutes):

        if minutes == 0:
            return "Compliant"

        elif minutes <= WARNING_MINUTES:
            return "Warning"

        elif minutes <= CRITICAL_MINUTES:
            return "Alert"

        else:
            return "Critical"

    temperature_summary[
        "temperature_status"
    ] = temperature_summary[
        "total_excursion_minutes"
    ].apply(
        temperature_status
    )

    return temperature_summary


# ==========================================================
# CALIBRATION SUMMARY
# ==========================================================

def summarize_calibration(
    sensor_logs,
    calibrations
):

    calibration_summary = (
        sensor_logs[
            [
                "shipment_id",
                "sensor_id",
                "calibration_valid",
                "calibration_error"
            ]
        ]
        .drop_duplicates()
        .groupby("shipment_id")
        .agg(
            sensors_used=(
                "sensor_id",
                "nunique"
            ),

            invalid_calibration_sensors=(
                "calibration_valid",
                lambda x: (~x).sum()
            ),

            max_calibration_error=(
                "calibration_error",
                "max"
            )
        )
        .reset_index()
    )

    calibration_summary[
        "calibration_status"
    ] = np.where(
        calibration_summary[
            "invalid_calibration_sensors"
        ] > 0,
        "Review",
        "Valid"
    )

    return calibration_summary


# ==========================================================
# CUSTODY / HANDOVER SUMMARY
# ==========================================================

def summarize_handovers(handovers):

    custody_summary = (
        handovers
        .groupby("shipment_id")
        .agg(
            total_handovers=(
                "handover_id",
                "count"
            ),

            missing_signatures=(
                "signature_status",
                lambda x: (x == "Missing").sum()
            )
        )
        .reset_index()
    )

    custody_summary[
        "custody_status"
    ] = np.where(
        custody_summary[
            "missing_signatures"
        ] > 0,
        "Review",
        "Complete"
    )

    return custody_summary


# ==========================================================
# ROUTE SUMMARY
# ==========================================================

def summarize_routes(route_events):

    route_summary = (
        route_events
        .groupby("shipment_id")
        .agg(
            traffic_delays=(
                "event_type",
                lambda x: (
                    x == "Traffic Delay"
                ).sum()
            ),

            route_deviations=(
                "event_type",
                lambda x: (
                    x == "Route Deviation"
                ).sum()
            ),

            total_delay_minutes=(
                "duration_minutes",
                "sum"
            )
        )
        .reset_index()
    )

    def route_status(row):

        if row["route_deviations"] > 0:
            return "Deviation"

        elif row["traffic_delays"] > 0:
            return "Delayed"

        return "Normal"

    route_summary[
        "route_status"
    ] = route_summary.apply(
        route_status,
        axis=1
    )

    return route_summary


# ==========================================================
# FINAL COMPLIANCE DECISION
# ==========================================================

def create_final_decision(
    shipments,
    temperature_summary,
    calibration_summary,
    custody_summary,
    route_summary
):

    result = shipments[
        [
            "shipment_id",
            "batch_id",
            "vehicle_id",
            "origin",
            "destination",
            "departure_time",
            "arrival_time",
            "status"
        ]
    ].copy()

    # ------------------------------------------------------
    # Join all evidence
    # ------------------------------------------------------

    result = result.merge(
        temperature_summary,
        on="shipment_id",
        how="left"
    )

    result = result.merge(
        calibration_summary,
        on="shipment_id",
        how="left"
    )

    result = result.merge(
        custody_summary,
        on="shipment_id",
        how="left"
    )

    result = result.merge(
        route_summary,
        on="shipment_id",
        how="left"
    )

    # ------------------------------------------------------
    # Fill missing evidence
    # ------------------------------------------------------

    result["missing_signatures"] = (
        result["missing_signatures"]
        .fillna(0)
    )

    result["route_deviations"] = (
        result["route_deviations"]
        .fillna(0)
    )

    result["traffic_delays"] = (
        result["traffic_delays"]
        .fillna(0)
    )

    result["total_delay_minutes"] = (
        result["total_delay_minutes"]
        .fillna(0)
    )

    result["invalid_calibration_sensors"] = (
        result[
            "invalid_calibration_sensors"
        ]
        .fillna(0)
    )

    # ------------------------------------------------------
    # Overall compliance
    # ------------------------------------------------------

    def final_status(row):

        # Critical temperature excursion
        if row["temperature_status"] == "Critical":
            return "Non-Compliant"

        # Major custody/calibration problems
        if (
            row["calibration_status"] == "Review"
            and
            row["custody_status"] == "Review"
        ):
            return "Non-Compliant"

        # Temperature alert
        if row["temperature_status"] in [
            "Alert",
            "Warning"
        ]:
            return "Review"

        # Calibration problem
        if row["calibration_status"] == "Review":
            return "Review"

        # Missing custody evidence
        if row["custody_status"] == "Review":
            return "Review"

        # Route deviation
        if row["route_status"] == "Deviation":
            return "Review"

        return "Compliant"

    result[
        "overall_compliance"
    ] = result.apply(
        final_status,
        axis=1
    )

    # ------------------------------------------------------
    # Explanation
    # ------------------------------------------------------

    def build_reason(row):

        reasons = []

        if row["temperature_status"] != "Compliant":
            reasons.append(
                f"Temperature: "
                f"{row['temperature_status']}"
            )

        if row["calibration_status"] == "Review":
            reasons.append(
                "Calibration issue"
            )

        if row["custody_status"] == "Review":
            reasons.append(
                "Missing custody signature"
            )

        if row["route_status"] == "Deviation":
            reasons.append(
                "Route deviation"
            )

        if row["route_status"] == "Delayed":
            reasons.append(
                "Traffic delay"
            )

        if not reasons:
            return "All compliance checks passed"

        return "; ".join(reasons)

    result[
        "compliance_reason"
    ] = result.apply(
        build_reason,
        axis=1
    )

    return result


# ==========================================================
# MAIN
# ==========================================================

def main():

    print("=" * 70)
    print("COLDCHAINGUARD - COMPLIANCE ENGINE")
    print("=" * 70)

    (
        sensor_logs,
        shipments,
        batches,
        calibrations,
        handovers,
        route_events
    ) = load_data()

    # ------------------------------------------------------
    # Temperature
    # ------------------------------------------------------

    sensor_logs = calculate_temperature_compliance(
        sensor_logs
    )

    sensor_logs = calculate_excursion_duration(
        sensor_logs
    )

    temperature_summary = summarize_temperature(
        sensor_logs
    )

    # ------------------------------------------------------
    # Calibration
    # ------------------------------------------------------

    calibration_summary = summarize_calibration(
        sensor_logs,
        calibrations
    )

    # ------------------------------------------------------
    # Custody
    # ------------------------------------------------------

    custody_summary = summarize_handovers(
        handovers
    )

    # ------------------------------------------------------
    # Route
    # ------------------------------------------------------

    route_summary = summarize_routes(
        route_events
    )

    # ------------------------------------------------------
    # Final decision
    # ------------------------------------------------------

    result = create_final_decision(
        shipments,
        temperature_summary,
        calibration_summary,
        custody_summary,
        route_summary
    )

    # ------------------------------------------------------
    # Display results
    # ------------------------------------------------------

    print("\nOVERALL COMPLIANCE")
    print("-" * 70)

    print(
        result[
            "overall_compliance"
        ].value_counts()
    )

    print("\nTEMPERATURE STATUS")
    print("-" * 70)

    print(
        result[
            "temperature_status"
        ].value_counts()
    )

    print("\nCALIBRATION STATUS")
    print("-" * 70)

    print(
        result[
            "calibration_status"
        ].value_counts()
    )

    print("\nCUSTODY STATUS")
    print("-" * 70)

    print(
        result[
            "custody_status"
        ].value_counts()
    )

    print("\nROUTE STATUS")
    print("-" * 70)

    print(
        result[
            "route_status"
        ].value_counts()
    )

    # ------------------------------------------------------
    # Save
    # ------------------------------------------------------

    result.to_csv(
        "data/compliance_results.csv",
        index=False
    )

    print(
        "\nSaved: "
        "data/compliance_results.csv"
    )


if __name__ == "__main__":
    main()