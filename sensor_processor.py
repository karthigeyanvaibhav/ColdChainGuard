import pandas as pd
import numpy as np


# ==========================================================
# CONFIGURATION
# ==========================================================

NOISE_JUMP_THRESHOLD = 5.0
MAX_GAP_MINUTES = 15


# ==========================================================
# LOAD DATA
# ==========================================================

def load_data():

    sensor_logs = pd.read_csv(
        "data/raw/sensor_logs.csv",
        parse_dates=["recorded_at"]
    )

    sensors = pd.read_csv(
        "data/raw/sensors.csv",
        parse_dates=["installation_date"]
    )

    calibrations = pd.read_csv(
        "data/raw/calibrations.csv",
        parse_dates=[
            "calibration_date",
            "expiry_date"
        ]
    )

    batches = pd.read_csv(
        "data/raw/product_batches.csv"
    )

    shipments = pd.read_csv(
        "data/raw/shipments.csv",
        parse_dates=[
            "departure_time",
            "arrival_time"
        ]
    )

    return (
        sensor_logs,
        sensors,
        calibrations,
        batches,
        shipments
    )


# ==========================================================
# ADD PRODUCT INFORMATION
# ==========================================================

def attach_product_information(
    sensor_logs,
    shipments,
    batches
):

    sensor_logs = sensor_logs.merge(
        shipments[
            [
                "shipment_id",
                "batch_id"
            ]
        ],
        on="shipment_id",
        how="left"
    )

    sensor_logs = sensor_logs.merge(
        batches[
            [
                "batch_id",
                "product_type",
                "min_temperature_c",
                "max_temperature_c"
            ]
        ],
        on="batch_id",
        how="left"
    )

    return sensor_logs


# ==========================================================
# CHECK CALIBRATION
# ==========================================================

def attach_calibration_information(
    sensor_logs,
    calibrations
):

    calibration_columns = [
        "sensor_id",
        "calibration_date",
        "expiry_date",
        "calibration_error",
        "status"
    ]

    sensor_logs = sensor_logs.merge(
        calibrations[calibration_columns],
        on="sensor_id",
        how="left"
    )

    sensor_logs["calibration_valid"] = (
        (sensor_logs["status"] == "Valid")
        &
        (
            sensor_logs["recorded_at"].dt.date
            <= sensor_logs["expiry_date"]
        )
    )

    return sensor_logs


# ==========================================================
# DETECT NOISE
# ==========================================================

def detect_noise(sensor_logs):

    sensor_logs = sensor_logs.sort_values(
        [
            "sensor_id",
            "shipment_id",
            "recorded_at"
        ]
    )

    sensor_logs["previous_temperature"] = (
        sensor_logs
        .groupby(
            [
                "sensor_id",
                "shipment_id"
            ]
        )["temperature_c"]
        .shift(1)
    )

    sensor_logs["temperature_jump"] = (
        sensor_logs["temperature_c"]
        -
        sensor_logs["previous_temperature"]
    ).abs()

    sensor_logs["noise_flag"] = (
        sensor_logs["temperature_jump"]
        >
        NOISE_JUMP_THRESHOLD
    )

    return sensor_logs


# ==========================================================
# DETECT MISSING VALUES
# ==========================================================

def detect_missing(sensor_logs):

    sensor_logs["missing_flag"] = (
        sensor_logs["temperature_c"]
        .isna()
    )

    return sensor_logs


# ==========================================================
# DETECT OFFLINE RECORDS
# ==========================================================

def detect_offline(sensor_logs):

    sensor_logs["offline_flag"] = (
        sensor_logs["network_status"]
        == "Offline"
    )

    return sensor_logs


# ==========================================================
# HANDLE MISSING VALUES
# ==========================================================

def recover_missing_temperatures(
    sensor_logs
):

    sensor_logs["temperature_original"] = (
        sensor_logs["temperature_c"]
    )

    sensor_logs["processing_method"] = "Original"

    sensor_logs["evidence_status"] = "Reliable"

    missing_mask = (
        sensor_logs["temperature_c"]
        .isna()
    )

    # Interpolation within the same shipment
    sensor_logs["temperature_c"] = (
        sensor_logs
        .groupby(
            [
                "sensor_id",
                "shipment_id"
            ]
        )["temperature_c"]
        .transform(
            lambda x: x.interpolate(
                limit=2
            )
        )
    )

    recovered_mask = (
        missing_mask
        &
        sensor_logs["temperature_c"].notna()
    )

    sensor_logs.loc[
        recovered_mask,
        "processing_method"
    ] = "Interpolated"

    sensor_logs.loc[
        recovered_mask,
        "evidence_status"
    ] = "Recovered"

    # Remaining missing values
    remaining_missing = (
        sensor_logs["temperature_c"]
        .isna()
    )

    sensor_logs.loc[
        remaining_missing,
        "processing_method"
    ] = "Unavailable"

    sensor_logs.loc[
        remaining_missing,
        "evidence_status"
    ] = "Incomplete"

    return sensor_logs


# ==========================================================
# FINAL EVIDENCE CLASSIFICATION
# ==========================================================

def classify_evidence(sensor_logs):

    # ------------------------------------------------------
    # Create individual reason flags
    # ------------------------------------------------------

    sensor_logs["calibration_issue"] = (
        ~sensor_logs["calibration_valid"]
    )

    sensor_logs["noise_issue"] = (
        sensor_logs["noise_flag"]
    )

    sensor_logs["missing_issue"] = (
        sensor_logs["missing_flag"]
    )

    sensor_logs["offline_issue"] = (
        sensor_logs["offline_flag"]
    )

    # ------------------------------------------------------
    # Create human-readable reason
    # ------------------------------------------------------

    def build_reason(row):

        reasons = []

        if row["calibration_issue"]:
            reasons.append("Invalid calibration")

        if row["noise_issue"]:
            reasons.append("Noise detected")

        if row["missing_issue"]:
            reasons.append("Missing observation")

        if row["offline_issue"]:
            reasons.append("Network offline")

        if not reasons:
            return "No issue"

        return "; ".join(reasons)

    sensor_logs["evidence_reason"] = (
        sensor_logs.apply(
            build_reason,
            axis=1
        )
    )

    # ------------------------------------------------------
    # Final evidence status
    # ------------------------------------------------------

    sensor_logs["evidence_status"] = "Reliable"

    # Successfully recovered readings
    recovered_mask = (
        sensor_logs["processing_method"]
        == "Interpolated"
    )

    sensor_logs.loc[
        recovered_mask,
        "evidence_status"
    ] = "Recovered"

    # Any quality issue → Review
    issue_mask = (
        sensor_logs["calibration_issue"]
        |
        sensor_logs["noise_issue"]
        |
        sensor_logs["offline_issue"]
    )

    sensor_logs.loc[
        issue_mask,
        "evidence_status"
    ] = "Review"

    # Still-missing values
    incomplete_mask = (
        sensor_logs["temperature_c"]
        .isna()
    )

    sensor_logs.loc[
        incomplete_mask,
        "evidence_status"
    ] = "Incomplete"

    return sensor_logs


# ==========================================================
# MAIN
# ==========================================================

def main():

    print("=" * 60)
    print("COLDCHAINGUARD - SENSOR PROCESSING")
    print("=" * 60)

    (
        sensor_logs,
        sensors,
        calibrations,
        batches,
        shipments
    ) = load_data()

    sensor_logs = attach_product_information(
        sensor_logs,
        shipments,
        batches
    )

    sensor_logs = attach_calibration_information(
        sensor_logs,
        calibrations
    )

    sensor_logs = detect_missing(
        sensor_logs
    )

    sensor_logs = detect_offline(
        sensor_logs
    )

    sensor_logs = detect_noise(
        sensor_logs
    )

    sensor_logs = recover_missing_temperatures(
        sensor_logs
    )

    sensor_logs = classify_evidence(
        sensor_logs
    )

    print("\nProcessing Results")
    print("-" * 60)

    print(
        "Total records:",
        len(sensor_logs)
    )

    print(
        "\nEvidence status:"
    )

    print(
        sensor_logs[
            "evidence_status"
        ].value_counts()
    )

    print(
        "\nProcessing method:"
    )

    print(
        sensor_logs[
            "processing_method"
        ].value_counts()
    )

    # Save processed evidence
    sensor_logs.to_csv(
        "data/processed_sensor_logs.csv",
        index=False
    )

    print(
        "\nSaved:"
        " data/processed_sensor_logs.csv"
    )


if __name__ == "__main__":
    main()