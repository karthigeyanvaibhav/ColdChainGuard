"""
src/star_schema.py
ColdChainGuard - Day 1: Analytical Star-Schema ETL Layer

Purpose:
  The operational PostgreSQL database is normalised for write performance.
  This script adds a SEPARATE ANALYTICAL LAYER of dimension + fact tables
  optimised for read/analytical queries (EDA, RFM, reporting).

  Analytical tables created:
    dim_vehicle, dim_product, dim_date
    fact_shipments, fact_sensor_logs, fact_route_events, fact_handovers

  On each run: tables are created if absent; UPSERT avoids duplicates.
  Exports master CSV to data/etl/ and star schema CSVs to data/etl/star_schema/
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import pandas as pd
from sqlalchemy import create_engine, text

DB_URL = "postgresql+psycopg://postgres:1322@localhost:5432/coldchainguard"
engine = create_engine(DB_URL, pool_pre_ping=True)

ETL_DIR  = os.path.join(PROJECT_ROOT, "data", "etl")
STAR_DIR = os.path.join(ETL_DIR, "star_schema")
os.makedirs(ETL_DIR, exist_ok=True)
os.makedirs(STAR_DIR, exist_ok=True)


# ==========================================================
# HELPER — run a single SQL statement in its own transaction
# ==========================================================
def exec_sql(sql, params=None):
    with engine.begin() as conn:
        if params:
            conn.execute(text(sql), params)
        else:
            conn.execute(text(sql))


def scalar_sql(sql):
    with engine.connect() as conn:
        return conn.execute(text(sql)).scalar()


def read_sql(sql):
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn)


# ==========================================================
# DDL — one statement per call
# ==========================================================
DDL_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS dim_vehicle (
        vehicle_key  SERIAL PRIMARY KEY,
        vehicle_id   VARCHAR(20) UNIQUE NOT NULL,
        vehicle_type VARCHAR(30),
        capacity_kg  NUMERIC(10,2),
        active       BOOLEAN
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dim_product (
        product_key       SERIAL PRIMARY KEY,
        batch_id          VARCHAR(30) UNIQUE NOT NULL,
        product_name      VARCHAR(100),
        product_type      VARCHAR(20),
        min_temperature_c NUMERIC(5,2),
        max_temperature_c NUMERIC(5,2),
        quantity          INTEGER,
        expiry_date       DATE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dim_date (
        date_key    INTEGER PRIMARY KEY,
        full_date   DATE UNIQUE NOT NULL,
        year        INTEGER,
        month       INTEGER,
        day         INTEGER,
        quarter     INTEGER,
        day_of_week VARCHAR(12),
        week_number INTEGER
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS fact_shipments (
        shipment_key             SERIAL PRIMARY KEY,
        shipment_id              VARCHAR(30) UNIQUE NOT NULL,
        vehicle_key              INTEGER REFERENCES dim_vehicle(vehicle_key),
        product_key              INTEGER REFERENCES dim_product(product_key),
        departure_date_key       INTEGER REFERENCES dim_date(date_key),
        arrival_date_key         INTEGER REFERENCES dim_date(date_key),
        origin                   VARCHAR(100),
        destination              VARCHAR(100),
        journey_duration_min     NUMERIC(10,2),
        status                   VARCHAR(30),
        overall_compliance       VARCHAR(30),
        temperature_status       VARCHAR(30),
        sensor_reliability       VARCHAR(30),
        custody_evidence_quality VARCHAR(30),
        route_reliability        VARCHAR(30)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS fact_sensor_logs (
        sensor_log_key       SERIAL PRIMARY KEY,
        shipment_id          VARCHAR(30) UNIQUE NOT NULL,
        shipment_key         INTEGER REFERENCES fact_shipments(shipment_key),
        total_readings       INTEGER,
        missing_readings     INTEGER,
        offline_readings     INTEGER,
        avg_temperature_c    NUMERIC(7,3),
        min_temperature_c    NUMERIC(7,3),
        max_temperature_c    NUMERIC(7,3),
        stddev_temperature_c NUMERIC(7,3),
        avg_battery_level    NUMERIC(6,2),
        avg_signal_strength  NUMERIC(6,2)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS fact_route_events (
        route_event_key         SERIAL PRIMARY KEY,
        shipment_id             VARCHAR(30) UNIQUE NOT NULL,
        shipment_key            INTEGER REFERENCES fact_shipments(shipment_key),
        total_events            INTEGER,
        checkpoint_events       INTEGER,
        cold_storage_stops      INTEGER,
        rest_stop_events        INTEGER,
        traffic_delay_events    INTEGER,
        route_deviation_events  INTEGER,
        total_delay_minutes     INTEGER,
        total_deviation_minutes INTEGER
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS fact_handovers (
        handover_key      SERIAL PRIMARY KEY,
        shipment_id       VARCHAR(30) UNIQUE NOT NULL,
        shipment_key      INTEGER REFERENCES fact_shipments(shipment_key),
        total_handovers   INTEGER,
        signed_handovers  INTEGER,
        missing_signatures INTEGER,
        signature_rate_pct NUMERIC(5,2)
    )
    """,
]


def create_schema():
    print("[Step 1] Creating analytical schema tables...")
    for stmt in DDL_STATEMENTS:
        exec_sql(stmt)
    print(f"         {len(DDL_STATEMENTS)} tables created/verified.")


# ==========================================================
# POPULATE dim_vehicle
# ==========================================================
def populate_dim_vehicle():
    print("[Step 2] Populating dim_vehicle...")
    exec_sql("""
        INSERT INTO dim_vehicle (vehicle_id, vehicle_type, capacity_kg, active)
        SELECT vehicle_id, vehicle_type, capacity_kg, active
        FROM vehicles
        ON CONFLICT (vehicle_id) DO NOTHING
    """)
    n = scalar_sql("SELECT COUNT(*) FROM dim_vehicle")
    print(f"         dim_vehicle: {n} rows")


# ==========================================================
# POPULATE dim_product
# ==========================================================
def populate_dim_product():
    print("[Step 3] Populating dim_product...")
    exec_sql("""
        INSERT INTO dim_product
            (batch_id, product_name, product_type, min_temperature_c,
             max_temperature_c, quantity, expiry_date)
        SELECT batch_id, product_name, product_type, min_temperature_c,
               max_temperature_c, quantity, expiry_date
        FROM product_batches
        ON CONFLICT (batch_id) DO NOTHING
    """)
    n = scalar_sql("SELECT COUNT(*) FROM dim_product")
    print(f"         dim_product: {n} rows")


# ==========================================================
# POPULATE dim_date
# ==========================================================
def populate_dim_date():
    print("[Step 4] Populating dim_date...")
    dates_df = read_sql("""
        SELECT DISTINCT DATE(departure_time) AS d FROM shipments
        WHERE departure_time IS NOT NULL
        UNION
        SELECT DISTINCT DATE(arrival_time)   AS d FROM shipments
        WHERE arrival_time IS NOT NULL
    """)
    inserted = 0
    for d in dates_df["d"].dropna():
        date_key = int(d.strftime("%Y%m%d"))
        exec_sql("""
            INSERT INTO dim_date
                (date_key, full_date, year, month, day, quarter, day_of_week, week_number)
            VALUES (:dk, :fd, :yr, :mo, :dy, :qr, :dow, :wk)
            ON CONFLICT (date_key) DO NOTHING
        """, {
            "dk": date_key, "fd": d.isoformat(),
            "yr": d.year, "mo": d.month, "dy": d.day,
            "qr": (d.month - 1) // 3 + 1,
            "dow": d.strftime("%A"),
            "wk": int(d.strftime("%W")),
        })
        inserted += 1
    n = scalar_sql("SELECT COUNT(*) FROM dim_date")
    print(f"         dim_date: {n} rows ({inserted} dates processed)")


# ==========================================================
# POPULATE fact_shipments
# ==========================================================
def populate_fact_shipments():
    print("[Step 5] Populating fact_shipments...")
    exec_sql("""
        INSERT INTO fact_shipments
            (shipment_id, vehicle_key, product_key,
             departure_date_key, arrival_date_key,
             origin, destination, journey_duration_min, status,
             overall_compliance, temperature_status, sensor_reliability,
             custody_evidence_quality, route_reliability)
        SELECT
            s.shipment_id,
            dv.vehicle_key,
            dp.product_key,
            CAST(TO_CHAR(s.departure_time, 'YYYYMMDD') AS INTEGER),
            CAST(TO_CHAR(s.arrival_time,   'YYYYMMDD') AS INTEGER),
            s.origin,
            s.destination,
            EXTRACT(EPOCH FROM (s.arrival_time - s.departure_time)) / 60.0,
            s.status,
            cr.overall_compliance,
            cr.temperature_status,
            cr.calibration_status,
            cr.custody_status,
            cr.route_status
        FROM shipments s
        JOIN dim_vehicle dv ON dv.vehicle_id = s.vehicle_id
        JOIN dim_product dp ON dp.batch_id   = s.batch_id
        LEFT JOIN compliance_results cr ON cr.shipment_id = s.shipment_id
        ON CONFLICT (shipment_id) DO NOTHING
    """)
    n = scalar_sql("SELECT COUNT(*) FROM fact_shipments")
    print(f"         fact_shipments: {n} rows")


# ==========================================================
# POPULATE fact_sensor_logs
# ==========================================================
def populate_fact_sensor_logs():
    print("[Step 6] Populating fact_sensor_logs...")
    exec_sql("""
        INSERT INTO fact_sensor_logs
            (shipment_id, shipment_key, total_readings, missing_readings,
             offline_readings, avg_temperature_c, min_temperature_c,
             max_temperature_c, stddev_temperature_c,
             avg_battery_level, avg_signal_strength)
        SELECT
            sl.shipment_id,
            fs.shipment_key,
            COUNT(*)                                        AS total_readings,
            SUM(CASE WHEN sl.temperature_c IS NULL THEN 1 ELSE 0 END),
            SUM(CASE WHEN sl.network_status = 'Offline'    THEN 1 ELSE 0 END),
            ROUND(AVG(sl.temperature_c)::NUMERIC,    3),
            ROUND(MIN(sl.temperature_c)::NUMERIC,    3),
            ROUND(MAX(sl.temperature_c)::NUMERIC,    3),
            ROUND(STDDEV(sl.temperature_c)::NUMERIC, 3),
            ROUND(AVG(sl.battery_level)::NUMERIC,    2),
            ROUND(AVG(sl.signal_strength)::NUMERIC,  2)
        FROM sensor_logs sl
        JOIN fact_shipments fs ON fs.shipment_id = sl.shipment_id
        GROUP BY sl.shipment_id, fs.shipment_key
        ON CONFLICT (shipment_id) DO NOTHING
    """)
    n = scalar_sql("SELECT COUNT(*) FROM fact_sensor_logs")
    print(f"         fact_sensor_logs: {n} rows")


# ==========================================================
# POPULATE fact_route_events
# ==========================================================
def populate_fact_route_events():
    print("[Step 7] Populating fact_route_events...")
    exec_sql("""
        INSERT INTO fact_route_events
            (shipment_id, shipment_key, total_events, checkpoint_events,
             cold_storage_stops, rest_stop_events, traffic_delay_events,
             route_deviation_events, total_delay_minutes, total_deviation_minutes)
        SELECT
            re.shipment_id,
            fs.shipment_key,
            COUNT(*),
            SUM(CASE WHEN re.event_type = 'Checkpoint'        THEN 1 ELSE 0 END),
            SUM(CASE WHEN re.event_type = 'Cold Storage Stop'  THEN 1 ELSE 0 END),
            SUM(CASE WHEN re.event_type = 'Rest Stop'          THEN 1 ELSE 0 END),
            SUM(CASE WHEN re.event_type = 'Traffic Delay'      THEN 1 ELSE 0 END),
            SUM(CASE WHEN re.event_type = 'Route Deviation'    THEN 1 ELSE 0 END),
            SUM(CASE WHEN re.event_type = 'Traffic Delay'
                     THEN re.duration_minutes ELSE 0 END),
            SUM(CASE WHEN re.event_type = 'Route Deviation'
                     THEN re.duration_minutes ELSE 0 END)
        FROM route_events re
        JOIN fact_shipments fs ON fs.shipment_id = re.shipment_id
        GROUP BY re.shipment_id, fs.shipment_key
        ON CONFLICT (shipment_id) DO NOTHING
    """)
    n = scalar_sql("SELECT COUNT(*) FROM fact_route_events")
    print(f"         fact_route_events: {n} rows")


# ==========================================================
# POPULATE fact_handovers
# ==========================================================
def populate_fact_handovers():
    print("[Step 8] Populating fact_handovers...")
    exec_sql("""
        INSERT INTO fact_handovers
            (shipment_id, shipment_key, total_handovers,
             signed_handovers, missing_signatures, signature_rate_pct)
        SELECT
            h.shipment_id,
            fs.shipment_key,
            COUNT(*),
            SUM(CASE WHEN h.signature_status = 'Signed'  THEN 1 ELSE 0 END),
            SUM(CASE WHEN h.signature_status = 'Missing' THEN 1 ELSE 0 END),
            ROUND(
                100.0 * SUM(CASE WHEN h.signature_status = 'Signed' THEN 1 ELSE 0 END)
                / NULLIF(COUNT(*), 0), 2
            )
        FROM handovers h
        JOIN fact_shipments fs ON fs.shipment_id = h.shipment_id
        GROUP BY h.shipment_id, fs.shipment_key
        ON CONFLICT (shipment_id) DO NOTHING
    """)
    n = scalar_sql("SELECT COUNT(*) FROM fact_handovers")
    print(f"         fact_handovers: {n} rows")


# ==========================================================
# EXPORT MASTER CSV DATASETS
# ==========================================================
def export_master_datasets():
    print("[Step 9] Exporting master analytical datasets...")

    master = read_sql("""
        SELECT
            fs.shipment_id,
            dv.vehicle_id,
            dv.vehicle_type,
            dv.capacity_kg,
            dp.product_name,
            dp.product_type,
            dp.min_temperature_c  AS product_min_temp,
            dp.max_temperature_c  AS product_max_temp,
            dp.quantity           AS batch_quantity,
            dp.expiry_date,
            dd.full_date          AS departure_date,
            fs.origin,
            fs.destination,
            fs.journey_duration_min,
            fs.status             AS shipment_status,
            fs.overall_compliance,
            fs.temperature_status,
            fs.sensor_reliability,
            fs.custody_evidence_quality,
            fs.route_reliability,
            fsl.total_readings,
            fsl.missing_readings,
            fsl.offline_readings,
            fsl.avg_temperature_c,
            fsl.min_temperature_c  AS obs_min_temp,
            fsl.max_temperature_c  AS obs_max_temp,
            fsl.stddev_temperature_c,
            fsl.avg_battery_level,
            fsl.avg_signal_strength,
            fre.total_events,
            fre.traffic_delay_events,
            fre.route_deviation_events,
            fre.total_delay_minutes,
            fh.total_handovers,
            fh.signed_handovers,
            fh.missing_signatures,
            fh.signature_rate_pct
        FROM fact_shipments fs
        JOIN dim_vehicle  dv  ON dv.vehicle_key  = fs.vehicle_key
        JOIN dim_product  dp  ON dp.product_key  = fs.product_key
        LEFT JOIN dim_date dd ON dd.date_key      = fs.departure_date_key
        LEFT JOIN fact_sensor_logs  fsl ON fsl.shipment_id = fs.shipment_id
        LEFT JOIN fact_route_events fre ON fre.shipment_id = fs.shipment_id
        LEFT JOIN fact_handovers    fh  ON fh.shipment_id  = fs.shipment_id
        ORDER BY fs.shipment_id
    """)
    master.to_csv(os.path.join(ETL_DIR, "master_shipments.csv"), index=False)
    print(f"         master_shipments.csv: {len(master)} rows, {len(master.columns)} columns")

    # ETL summary
    tables = ["dim_vehicle", "dim_product", "dim_date",
              "fact_shipments", "fact_sensor_logs",
              "fact_route_events", "fact_handovers"]
    rows = [{"table": t, "rows": scalar_sql(f"SELECT COUNT(*) FROM {t}")} for t in tables]
    etl_summary = pd.DataFrame(rows)
    etl_summary.to_csv(os.path.join(ETL_DIR, "etl_summary.csv"), index=False)

    # Per-table CSVs
    for tbl in tables:
        df = read_sql(f"SELECT * FROM {tbl}")
        df.to_csv(os.path.join(STAR_DIR, f"{tbl}.csv"), index=False)

    print(f"         Star schema CSVs exported to data/etl/star_schema/")


# ==========================================================
# VERIFICATION SUMMARY
# ==========================================================
def print_verification():
    print("")
    print("=" * 60)
    print("STAR SCHEMA VERIFICATION SUMMARY")
    print("=" * 60)
    tables = ["dim_vehicle", "dim_product", "dim_date",
              "fact_shipments", "fact_sensor_logs",
              "fact_route_events", "fact_handovers"]
    all_ok = True
    for t in tables:
        n = scalar_sql(f"SELECT COUNT(*) FROM {t}")
        status = "[OK]   " if n > 0 else "[EMPTY]"
        if n == 0:
            all_ok = False
        print(f"  {status}  {t:<25} {n:>6} rows")
    print("")
    if all_ok:
        print("  ALL ANALYTICAL TABLES POPULATED SUCCESSFULLY")
    else:
        print("  WARNING: Some tables are empty")
    print("=" * 60)


# ==========================================================
# MAIN
# ==========================================================
def main():
    print("=" * 60)
    print("COLDCHAINGUARD - DAY 1 STAR SCHEMA ETL")
    print("=" * 60)
    print("")
    print("Purpose: Build analytical star-schema layer from")
    print("         operational tables for EDA and segmentation.")
    print("")

    create_schema()
    populate_dim_vehicle()
    populate_dim_product()
    populate_dim_date()
    populate_fact_shipments()
    populate_fact_sensor_logs()
    populate_fact_route_events()
    populate_fact_handovers()
    export_master_datasets()
    print_verification()

    print("")
    print("ETL outputs saved to: data/etl/")
    print("Star schema CSVs:     data/etl/star_schema/")
    print("")
    print("DAY 1 ETL COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
