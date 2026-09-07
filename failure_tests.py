import os
import pandas as pd


# ==========================================================
# PROJECT PATHS
# ==========================================================

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

PROCESSED_SENSOR_FILE = os.path.join(
    PROJECT_ROOT,
    "data",
    "processed_sensor_logs.csv"
)

CALIBRATION_FILE = os.path.join(
    PROJECT_ROOT,
    "data",
    "raw",
    "calibrations.csv"
)

HANDOVER_FILE = os.path.join(
    PROJECT_ROOT,
    "data",
    "raw",
    "handovers.csv"
)

SENSOR_FILE = os.path.join(
    PROJECT_ROOT,
    "data",
    "raw",
    "sensor_logs.csv"
)

RESULT_DIR = os.path.join(
    PROJECT_ROOT,
    "data",
    "experiments"
)

os.makedirs(
    RESULT_DIR,
    exist_ok=True
)


# ==========================================================
# LOAD DATA
# ==========================================================

def load_data():

    print("=" * 70)
    print("LOADING FAILURE TEST DATA")
    print("=" * 70)

    sensor_logs = pd.read_csv(
        PROCESSED_SENSOR_FILE
    )

    calibrations = pd.read_csv(
        CALIBRATION_FILE
    )

    handovers = pd.read_csv(
        HANDOVER_FILE
    )

    raw_sensor_logs = pd.read_csv(
        SENSOR_FILE
    )

    print(
        f"\nProcessed sensor records : "
        f"{len(sensor_logs)}"
    )

    print(
        f"Calibration records      : "
        f"{len(calibrations)}"
    )

    print(
        f"Handover records         : "
        f"{len(handovers)}"
    )

    return (
        sensor_logs,
        calibrations,
        handovers,
        raw_sensor_logs
    )


# ==========================================================
# CASE 1
# MISSING TEMPERATURE OBSERVATION
# ==========================================================

def test_missing_temperature(sensor_logs):

    print("\n")
    print("=" * 70)
    print("FAILURE CASE 1 - MISSING TEMPERATURE")
    print("=" * 70)

    missing = sensor_logs[
        sensor_logs["temperature_c"].isna()
    ]

    print(
        f"\nMissing temperature records found: "
        f"{len(missing)}"
    )

    if len(missing) == 0:

        print(
            "No missing observations available."
        )

        return {
            "case": "Missing Temperature",
            "detected": False,
            "recovery": "Not required",
            "result": "PASS"
        }

    recovered = sensor_logs[
        (
            sensor_logs["processing_method"]
            .astype(str)
            .str.contains(
                "Interpolated",
                case=False,
                na=False
            )
        )
    ]

    print(
        f"Interpolated records: "
        f"{len(recovered)}"
    )

    if len(recovered) > 0:

        print(
            "Result: Missing observations "
            "were recovered through interpolation."
        )

        return {
            "case": "Missing Temperature",
            "detected": True,
            "recovery": "Interpolation",
            "result": "PASS"
        }

    print(
        "Result: Missing observations detected "
        "but recovery was not observed."
    )

    return {
        "case": "Missing Temperature",
        "detected": True,
        "recovery": "Not recovered",
        "result": "REVIEW"
    }


# ==========================================================
# CASE 2
# INVALID CALIBRATION
# ==========================================================

def test_invalid_calibration(
    sensor_logs,
    calibrations
):

    print("\n")
    print("=" * 70)
    print("FAILURE CASE 2 - INVALID CALIBRATION")
    print("=" * 70)

    invalid = calibrations[
        calibrations["status"] != "Valid"
    ]

    print(
        f"\nInvalid calibration records: "
        f"{len(invalid)}"
    )

    invalid_sensors = set(
        invalid["sensor_id"]
    )

    affected_logs = sensor_logs[
        sensor_logs["sensor_id"].isin(
            invalid_sensors
        )
    ]

    print(
        f"Sensor observations affected: "
        f"{len(affected_logs)}"
    )

    review_records = sensor_logs[
        (
            sensor_logs["evidence_status"]
            .astype(str)
            .str.lower()
            == "review"
        )
    ]

    affected_review = review_records[
        review_records["sensor_id"].isin(
            invalid_sensors
        )
    ]

    print(
        f"Observations classified for review: "
        f"{len(affected_review)}"
    )

    if len(invalid) > 0:

        print(
            "Result: Invalid calibration "
            "conditions were detected."
        )

        return {
            "case": "Invalid Calibration",
            "detected": True,
            "affected_records": len(affected_logs),
            "result": "PASS"
        }

    return {
        "case": "Invalid Calibration",
        "detected": False,
        "affected_records": 0,
        "result": "REVIEW"
    }


# ==========================================================
# CASE 3
# MISSING HANDOVER SIGNATURE
# ==========================================================

def test_missing_handover(handovers):

    print("\n")
    print("=" * 70)
    print("FAILURE CASE 3 - MISSING HANDOVER SIGNATURE")
    print("=" * 70)

    missing = handovers[
        handovers["signature_status"]
        .astype(str)
        .str.lower()
        == "missing"
    ]

    print(
        f"\nMissing signatures: "
        f"{len(missing)}"
    )

    affected_shipments = (
        missing["shipment_id"]
        .nunique()
    )

    print(
        f"Affected shipments: "
        f"{affected_shipments}"
    )

    if len(missing) > 0:

        print(
            "Result: Missing custody signatures "
            "were detected."
        )

        return {
            "case": "Missing Handover Signature",
            "detected": True,
            "affected_shipments":
                affected_shipments,
            "result": "PASS"
        }

    return {
        "case": "Missing Handover Signature",
        "detected": False,
        "affected_shipments": 0,
        "result": "REVIEW"
    }


# ==========================================================
# CASE 4
# OFFLINE / STORE-AND-FORWARD
# ==========================================================

def test_offline_sensor(
    raw_sensor_logs,
    processed_sensor_logs
):

    print("\n")
    print("=" * 70)
    print("FAILURE CASE 4 - OFFLINE SENSOR")
    print("=" * 70)

    offline = raw_sensor_logs[
        raw_sensor_logs["network_status"]
        .astype(str)
        .str.lower()
        == "offline"
    ]

    print(
        f"\nOffline observations: "
        f"{len(offline)}"
    )

    if len(offline) == 0:

        print(
            "No offline observations found."
        )

        return {
            "case": "Offline Sensor",
            "detected": False,
            "result": "REVIEW"
        }

    offline_ids = set(
        offline["log_id"]
    )

    recovered = processed_sensor_logs[
        processed_sensor_logs["log_id"]
        .isin(offline_ids)
    ]

    print(
        f"Offline records represented "
        f"in processed data: {len(recovered)}"
    )

    if len(recovered) > 0:

        print(
            "Result: Offline observations "
            "were retained in the processing pipeline."
        )

        return {
            "case": "Offline Sensor",
            "detected": True,
            "processed_records":
                len(recovered),
            "result": "PASS"
        }

    return {
        "case": "Offline Sensor",
        "detected": True,
        "processed_records": 0,
        "result": "REVIEW"
    }


# ==========================================================
# SAVE FAILURE RESULTS
# ==========================================================

def save_results(results):

    output = pd.DataFrame(
        results
    )

    output_file = os.path.join(
        RESULT_DIR,
        "failure_mode_results.csv"
    )

    output.to_csv(
        output_file,
        index=False
    )

    print("\n")
    print("=" * 70)
    print("FAILURE MODE SUMMARY")
    print("=" * 70)

    print(
        output.to_string(
            index=False
        )
    )

    print(
        f"\nResults saved to:\n{output_file}"
    )


# ==========================================================
# MAIN
# ==========================================================

def main():

    (
        sensor_logs,
        calibrations,
        handovers,
        raw_sensor_logs
    ) = load_data()

    results = []

    results.append(
        test_missing_temperature(
            sensor_logs
        )
    )

    results.append(
        test_invalid_calibration(
            sensor_logs,
            calibrations
        )
    )

    results.append(
        test_missing_handover(
            handovers
        )
    )

    results.append(
        test_offline_sensor(
            raw_sensor_logs,
            sensor_logs
        )
    )

    save_results(
        results
    )

    print("\n")
    print("=" * 70)
    print(
        "FAILURE MODE TESTING COMPLETED"
    )
    print("=" * 70)


# ==========================================================
# RUN
# ==========================================================

if __name__ == "__main__":
    main()