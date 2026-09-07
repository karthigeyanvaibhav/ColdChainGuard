import os
import sys
import pandas as pd

from sqlalchemy import text, inspect

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
# PATHS
# ==========================================================

RAW_DIR = os.path.join(
    PROJECT_ROOT,
    "data",
    "raw"
)

PROCESSED_DIR = os.path.join(
    PROJECT_ROOT,
    "data"
)


# ==========================================================
# FILE PATHS
# ==========================================================

FILES = {
    "vehicles": os.path.join(
        RAW_DIR,
        "vehicles.csv"
    ),

    "sensors": os.path.join(
        RAW_DIR,
        "sensors.csv"
    ),

    "product_batches": os.path.join(
        RAW_DIR,
        "product_batches.csv"
    ),

    "shipments": os.path.join(
        RAW_DIR,
        "shipments.csv"
    ),

    "sensor_logs": os.path.join(
        RAW_DIR,
        "sensor_logs.csv"
    ),

    "calibrations": os.path.join(
        RAW_DIR,
        "calibrations.csv"
    ),

    "handovers": os.path.join(
        RAW_DIR,
        "handovers.csv"
    ),

    "route_events": os.path.join(
        RAW_DIR,
        "route_events.csv"
    ),

    "compliance_results": os.path.join(
        PROCESSED_DIR,
        "compliance_results.csv"
    )
}


# ==========================================================
# TABLE LOAD ORDER
# ==========================================================
#
# This order is important because PostgreSQL foreign keys
# require parent records to exist before child records.
#
# ==========================================================

LOAD_ORDER = [
    "vehicles",
    "sensors",
    "product_batches",
    "shipments",
    "sensor_logs",
    "calibrations",
    "handovers",
    "route_events",
    "compliance_results"
]


# ==========================================================
# CHECK FILES
# ==========================================================

def check_files():

    print("\n" + "=" * 70)
    print("CHECKING DATA FILES")
    print("=" * 70)

    missing_files = []

    for table, filepath in FILES.items():

        if os.path.exists(filepath):

            print(
                f"[OK] {table:<20} "
                f"{filepath}"
            )

        else:

            print(
                f"[MISSING] {table:<20} "
                f"{filepath}"
            )

            missing_files.append(filepath)

    if missing_files:

        raise FileNotFoundError(
            "\nMissing required files. "
            "Please generate the data first."
        )


# ==========================================================
# CHECK DATABASE TABLES
# ==========================================================

def check_tables():

    print("\n" + "=" * 70)
    print("CHECKING POSTGRESQL TABLES")
    print("=" * 70)

    inspector = inspect(engine)

    existing_tables = inspector.get_table_names()

    required_tables = [
        "vehicles",
        "sensors",
        "product_batches",
        "shipments",
        "sensor_logs",
        "calibrations",
        "handovers",
        "route_events",
        "compliance_results"
    ]

    missing_tables = []

    for table in required_tables:

        if table in existing_tables:

            print(
                f"[OK] {table}"
            )

        else:

            print(
                f"[MISSING] {table}"
            )

            missing_tables.append(table)

    if missing_tables:

        raise RuntimeError(
            "\nRequired PostgreSQL tables are missing.\n"
            "Run database/schema.py first."
        )


# ==========================================================
# LOAD CSV
# ==========================================================

def load_csv(table_name):

    filepath = FILES[table_name]

    print(
        f"\nLoading {table_name}..."
    )

    df = pd.read_csv(filepath)

    print(
        f"CSV records: {len(df)}"
    )

    return df


# ==========================================================
# CLEAN VEHICLES
# ==========================================================

def prepare_vehicles(df):

    df = df[
        [
            "vehicle_id",
            "vehicle_type",
            "capacity_kg",
            "active"
        ]
    ].copy()

    df["vehicle_id"] = (
        df["vehicle_id"]
        .astype(str)
        .str.strip()
    )

    df["vehicle_type"] = (
        df["vehicle_type"]
        .astype(str)
        .str.strip()
    )

    df["capacity_kg"] = pd.to_numeric(
        df["capacity_kg"],
        errors="coerce"
    )

    df["active"] = df["active"].astype(bool)

    return df


# ==========================================================
# CLEAN SENSORS
# ==========================================================

def prepare_sensors(df):

    df = df[
        [
            "sensor_id",
            "vehicle_id",
            "sensor_type",
            "installation_date",
            "status"
        ]
    ].copy()

    df["sensor_id"] = (
        df["sensor_id"]
        .astype(str)
        .str.strip()
    )

    df["vehicle_id"] = (
        df["vehicle_id"]
        .astype(str)
        .str.strip()
    )

    df["installation_date"] = pd.to_datetime(
        df["installation_date"],
        errors="coerce"
    ).dt.date

    return df


# ==========================================================
# CLEAN PRODUCT BATCHES
# ==========================================================

def prepare_product_batches(df):

    df = df[
        [
            "batch_id",
            "product_name",
            "product_type",
            "min_temperature_c",
            "max_temperature_c",
            "quantity",
            "expiry_date"
        ]
    ].copy()

    df["batch_id"] = (
        df["batch_id"]
        .astype(str)
        .str.strip()
    )

    df["min_temperature_c"] = pd.to_numeric(
        df["min_temperature_c"],
        errors="coerce"
    )

    df["max_temperature_c"] = pd.to_numeric(
        df["max_temperature_c"],
        errors="coerce"
    )

    df["quantity"] = pd.to_numeric(
        df["quantity"],
        errors="coerce"
    ).astype("Int64")

    df["expiry_date"] = pd.to_datetime(
        df["expiry_date"],
        errors="coerce"
    ).dt.date

    return df


# ==========================================================
# CLEAN SHIPMENTS
# ==========================================================

def prepare_shipments(df):

    df = df[
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

    df["shipment_id"] = (
        df["shipment_id"]
        .astype(str)
        .str.strip()
    )

    df["batch_id"] = (
        df["batch_id"]
        .astype(str)
        .str.strip()
    )

    df["vehicle_id"] = (
        df["vehicle_id"]
        .astype(str)
        .str.strip()
    )

    df["departure_time"] = pd.to_datetime(
        df["departure_time"],
        errors="coerce"
    )

    df["arrival_time"] = pd.to_datetime(
        df["arrival_time"],
        errors="coerce"
    )

    return df


# ==========================================================
# CLEAN SENSOR LOGS
# ==========================================================

def prepare_sensor_logs(df):

    df = df[
        [
            "log_id",
            "sensor_id",
            "shipment_id",
            "recorded_at",
            "temperature_c",
            "battery_level",
            "signal_strength",
            "network_status"
        ]
    ].copy()

    df["log_id"] = pd.to_numeric(
        df["log_id"],
        errors="coerce"
    ).astype("Int64")

    df["sensor_id"] = (
        df["sensor_id"]
        .astype(str)
        .str.strip()
    )

    df["shipment_id"] = (
        df["shipment_id"]
        .astype(str)
        .str.strip()
    )

    df["recorded_at"] = pd.to_datetime(
        df["recorded_at"],
        errors="coerce"
    )

    df["temperature_c"] = pd.to_numeric(
        df["temperature_c"],
        errors="coerce"
    )

    df["battery_level"] = pd.to_numeric(
        df["battery_level"],
        errors="coerce"
    )

    df["signal_strength"] = pd.to_numeric(
        df["signal_strength"],
        errors="coerce"
    )

    return df


# ==========================================================
# CLEAN CALIBRATIONS
# ==========================================================

def prepare_calibrations(df):

    df = df[
        [
            "calibration_id",
            "sensor_id",
            "calibration_date",
            "expiry_date",
            "calibration_error",
            "status"
        ]
    ].copy()

    df["calibration_id"] = pd.to_numeric(
        df["calibration_id"],
        errors="coerce"
    ).astype("Int64")

    df["sensor_id"] = (
        df["sensor_id"]
        .astype(str)
        .str.strip()
    )

    df["calibration_date"] = pd.to_datetime(
        df["calibration_date"],
        errors="coerce"
    ).dt.date

    df["expiry_date"] = pd.to_datetime(
        df["expiry_date"],
        errors="coerce"
    ).dt.date

    df["calibration_error"] = pd.to_numeric(
        df["calibration_error"],
        errors="coerce"
    )

    return df


# ==========================================================
# CLEAN HANDOVERS
# ==========================================================

def prepare_handovers(df):

    df = df[
        [
            "handover_id",
            "shipment_id",
            "from_party",
            "to_party",
            "location",
            "handover_time",
            "signature_status"
        ]
    ].copy()

    df["handover_id"] = pd.to_numeric(
        df["handover_id"],
        errors="coerce"
    ).astype("Int64")

    df["shipment_id"] = (
        df["shipment_id"]
        .astype(str)
        .str.strip()
    )

    df["handover_time"] = pd.to_datetime(
        df["handover_time"],
        errors="coerce"
    )

    return df


# ==========================================================
# CLEAN ROUTE EVENTS
# ==========================================================

def prepare_route_events(df):

    df = df[
        [
            "event_id",
            "shipment_id",
            "event_type",
            "location",
            "event_time",
            "duration_minutes"
        ]
    ].copy()

    df["event_id"] = pd.to_numeric(
        df["event_id"],
        errors="coerce"
    ).astype("Int64")

    df["shipment_id"] = (
        df["shipment_id"]
        .astype(str)
        .str.strip()
    )

    df["event_time"] = pd.to_datetime(
        df["event_time"],
        errors="coerce"
    )

    df["duration_minutes"] = pd.to_numeric(
        df["duration_minutes"],
        errors="coerce"
    ).fillna(0)

    return df


# ==========================================================
# CLEAN COMPLIANCE RESULTS
# ==========================================================

def prepare_compliance_results(df):

    # Only insert columns that belong to our PostgreSQL
    # compliance_results table.

    columns = [
        "shipment_id",
        "temperature_status",
        "calibration_status",
        "custody_status",
        "route_status",
        "total_sensor_records",
        "excursion_records",
        "total_excursion_minutes",
        "invalid_calibration_sensors",
        "missing_signatures",
        "traffic_delays",
        "route_deviations",
        "total_delay_minutes",
        "overall_compliance",
        "compliance_reason"
    ]

    df = df[columns].copy()

    df["shipment_id"] = (
        df["shipment_id"]
        .astype(str)
        .str.strip()
    )

    numeric_columns = [
        "total_sensor_records",
        "excursion_records",
        "total_excursion_minutes",
        "invalid_calibration_sensors",
        "missing_signatures",
        "traffic_delays",
        "route_deviations",
        "total_delay_minutes"
    ]

    for column in numeric_columns:

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    return df


# ==========================================================
# CHECK IF TABLE HAS DATA
# ==========================================================

def table_has_data(table_name):

    query = text(
        f"""
        SELECT EXISTS (
            SELECT 1
            FROM {table_name}
            LIMIT 1
        );
        """
    )

    with engine.connect() as conn:

        result = conn.execute(query).scalar()

    return result


# ==========================================================
# LOAD DATAFRAME INTO POSTGRESQL
# ==========================================================

def insert_dataframe(
    df,
    table_name
):

    if df.empty:

        print(
            f"[WARNING] {table_name} "
            "contains no records."
        )

        return

    if table_has_data(table_name):

        raise RuntimeError(
            f"\nTable '{table_name}' already "
            "contains data.\n"
            "The loader will not insert duplicate "
            "records automatically."
        )

    df.to_sql(
        table_name,
        con=engine,
        if_exists="append",
        index=False,
        method="multi",
        chunksize=1000
    )

    print(
        f"[OK] Inserted {len(df):,} records "
        f"into {table_name}"
    )


# ==========================================================
# VERIFY ROW COUNT
# ==========================================================

def get_row_count(table_name):

    query = text(
        f"""
        SELECT COUNT(*)
        FROM {table_name};
        """
    )

    with engine.connect() as conn:

        count = conn.execute(
            query
        ).scalar()

    return count


# ==========================================================
# LOAD ALL DATA
# ==========================================================

def load_all_data():

    print("\n")
    print("=" * 70)
    print("COLDCHAINGUARD - POSTGRESQL DATA LOADER")
    print("=" * 70)

    # ------------------------------------------------------
    # Check files
    # ------------------------------------------------------

    check_files()

    # ------------------------------------------------------
    # Check database
    # ------------------------------------------------------

    check_tables()

    # ------------------------------------------------------
    # Load vehicles
    # ------------------------------------------------------

    df = load_csv("vehicles")

    df = prepare_vehicles(df)

    insert_dataframe(
        df,
        "vehicles"
    )

    # ------------------------------------------------------
    # Load sensors
    # ------------------------------------------------------

    df = load_csv("sensors")

    df = prepare_sensors(df)

    insert_dataframe(
        df,
        "sensors"
    )

    # ------------------------------------------------------
    # Load product batches
    # ------------------------------------------------------

    df = load_csv("product_batches")

    df = prepare_product_batches(df)

    insert_dataframe(
        df,
        "product_batches"
    )

    # ------------------------------------------------------
    # Load shipments
    # ------------------------------------------------------

    df = load_csv("shipments")

    df = prepare_shipments(df)

    insert_dataframe(
        df,
        "shipments"
    )

    # ------------------------------------------------------
    # Load sensor logs
    # ------------------------------------------------------

    df = load_csv("sensor_logs")

    df = prepare_sensor_logs(df)

    insert_dataframe(
        df,
        "sensor_logs"
    )

    # ------------------------------------------------------
    # Load calibrations
    # ------------------------------------------------------

    df = load_csv("calibrations")

    df = prepare_calibrations(df)

    insert_dataframe(
        df,
        "calibrations"
    )

    # ------------------------------------------------------
    # Load handovers
    # ------------------------------------------------------

    df = load_csv("handovers")

    df = prepare_handovers(df)

    insert_dataframe(
        df,
        "handovers"
    )

    # ------------------------------------------------------
    # Load route events
    # ------------------------------------------------------

    df = load_csv("route_events")

    df = prepare_route_events(df)

    insert_dataframe(
        df,
        "route_events"
    )

    # ------------------------------------------------------
    # Load compliance results
    # ------------------------------------------------------

    df = load_csv("compliance_results")

    df = prepare_compliance_results(df)

    insert_dataframe(
        df,
        "compliance_results"
    )

    # ------------------------------------------------------
    # Final verification
    # ------------------------------------------------------

    print("\n")
    print("=" * 70)
    print("POSTGRESQL ROW COUNT VERIFICATION")
    print("=" * 70)

    for table_name in LOAD_ORDER:

        count = get_row_count(
            table_name
        )

        print(
            f"{table_name:<25} : "
            f"{count:,}"
        )

    print("\n")
    print("=" * 70)
    print("DATA LOADING COMPLETED SUCCESSFULLY")
    print("=" * 70)


# ==========================================================
# MAIN
# ==========================================================

if __name__ == "__main__":

    try:

        load_all_data()

    except Exception as e:

        print("\n")
        print("=" * 70)
        print("DATA LOADING FAILED")
        print("=" * 70)

        print(
            f"\nError: {e}"
        )

        raise