import pandas as pd


# ==========================================================
# DATA QUALITY ANALYSIS
# ==========================================================

def load_data():

    data = {}

    files = {
        "vehicles": "data/raw/vehicles.csv",
        "sensors": "data/raw/sensors.csv",
        "product_batches": "data/raw/product_batches.csv",
        "shipments": "data/raw/shipments.csv",
        "sensor_logs": "data/raw/sensor_logs.csv",
        "calibrations": "data/raw/calibrations.csv",
        "handovers": "data/raw/handovers.csv",
        "route_events": "data/raw/route_events.csv"
    }

    for name, path in files.items():

        data[name] = pd.read_csv(path)

    return data


# ==========================================================
# SENSOR DATA QUALITY
# ==========================================================

def analyze_sensor_logs(sensor_logs):

    print("\n" + "=" * 60)
    print("SENSOR DATA QUALITY")
    print("=" * 60)

    total = len(sensor_logs)

    missing_temperature = (
        sensor_logs["temperature_c"]
        .isna()
        .sum()
    )

    offline_records = (
        sensor_logs["network_status"]
        .eq("Offline")
        .sum()
    )

    print(f"Total sensor records : {total}")
    print(
        f"Missing temperatures: "
        f"{missing_temperature}"
    )
    print(
        f"Offline observations: "
        f"{offline_records}"
    )

    print("\nMissing percentage:")

    print(
        round(
            missing_temperature / total * 100,
            2
        ),
        "%"
    )

    print("\nNetwork status:")

    print(
        sensor_logs["network_status"]
        .value_counts()
    )


# ==========================================================
# TEMPERATURE ANALYSIS
# ==========================================================

def analyze_temperature(sensor_logs):

    print("\n" + "=" * 60)
    print("TEMPERATURE ANALYSIS")
    print("=" * 60)

    valid_temperatures = (
        sensor_logs["temperature_c"]
        .dropna()
    )

    print(
        valid_temperatures.describe()
    )


# ==========================================================
# CALIBRATION ANALYSIS
# ==========================================================

def analyze_calibrations(calibrations):

    print("\n" + "=" * 60)
    print("CALIBRATION ANALYSIS")
    print("=" * 60)

    print(
        calibrations["status"]
        .value_counts()
    )

    print("\nCalibration error:")

    print(
        calibrations[
            "calibration_error"
        ].describe()
    )


# ==========================================================
# HANDOVER ANALYSIS
# ==========================================================

def analyze_handovers(handovers):

    print("\n" + "=" * 60)
    print("HANDOVER ANALYSIS")
    print("=" * 60)

    print(
        handovers[
            "signature_status"
        ].value_counts()
    )

    missing_signatures = (
        handovers[
            "signature_status"
        ]
        .eq("Missing")
        .sum()
    )

    print(
        f"\nMissing signatures: "
        f"{missing_signatures}"
    )


# ==========================================================
# ROUTE ANALYSIS
# ==========================================================

def analyze_routes(route_events):

    print("\n" + "=" * 60)
    print("ROUTE EVENT ANALYSIS")
    print("=" * 60)

    print(
        route_events[
            "event_type"
        ].value_counts()
    )

    delays = route_events[
        route_events["event_type"]
        == "Traffic Delay"
    ]

    print(
        f"\nTraffic delay events: "
        f"{len(delays)}"
    )

    print(
        f"Total delay minutes: "
        f"{delays['duration_minutes'].sum()}"
    )


# ==========================================================
# REFERENTIAL INTEGRITY
# ==========================================================

def check_relationships(data):

    print("\n" + "=" * 60)
    print("RELATIONSHIP VALIDATION")
    print("=" * 60)

    shipments = data["shipments"]
    batches = data["product_batches"]
    vehicles = data["vehicles"]
    sensors = data["sensors"]
    sensor_logs = data["sensor_logs"]

    # Invalid batch references
    invalid_batches = (
        ~shipments["batch_id"]
        .isin(batches["batch_id"])
    ).sum()

    # Invalid vehicle references
    invalid_vehicles = (
        ~shipments["vehicle_id"]
        .isin(vehicles["vehicle_id"])
    ).sum()

    # Invalid sensor references
    invalid_sensors = (
        ~sensor_logs["sensor_id"]
        .isin(sensors["sensor_id"])
    ).sum()

    # Invalid shipment references
    invalid_shipments = (
        ~sensor_logs["shipment_id"]
        .isin(shipments["shipment_id"])
    ).sum()

    print(
        f"Invalid batch references   : "
        f"{invalid_batches}"
    )

    print(
        f"Invalid vehicle references : "
        f"{invalid_vehicles}"
    )

    print(
        f"Invalid sensor references  : "
        f"{invalid_sensors}"
    )

    print(
        f"Invalid shipment references: "
        f"{invalid_shipments}"
    )


# ==========================================================
# MAIN
# ==========================================================

def main():

    data = load_data()

    analyze_sensor_logs(
        data["sensor_logs"]
    )

    analyze_temperature(
        data["sensor_logs"]
    )

    analyze_calibrations(
        data["calibrations"]
    )

    analyze_handovers(
        data["handovers"]
    )

    analyze_routes(
        data["route_events"]
    )

    check_relationships(data)


if __name__ == "__main__":
    main()