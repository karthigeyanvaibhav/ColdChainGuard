import sys
import os

sys.path.append(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

from database.connection import engine
from sqlalchemy import text


# ==========================================================
# CREATE TABLES
# ==========================================================

def create_tables():

    with engine.begin() as conn:

        # --------------------------------------------------
        # Vehicles
        # --------------------------------------------------

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS vehicles (
                vehicle_id VARCHAR(20) PRIMARY KEY,
                vehicle_type VARCHAR(50),
                capacity_kg FLOAT,
                active BOOLEAN
            );
        """))

        # --------------------------------------------------
        # Sensors
        # --------------------------------------------------

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS sensors (
                sensor_id VARCHAR(20) PRIMARY KEY,
                vehicle_id VARCHAR(20),
                sensor_type VARCHAR(50),
                installation_date DATE,
                status VARCHAR(30),

                FOREIGN KEY (vehicle_id)
                REFERENCES vehicles(vehicle_id)
            );
        """))

        # --------------------------------------------------
        # Product Batches
        # --------------------------------------------------

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS product_batches (
                batch_id VARCHAR(20) PRIMARY KEY,
                product_name VARCHAR(100),
                product_type VARCHAR(30),
                min_temperature_c FLOAT,
                max_temperature_c FLOAT,
                quantity INTEGER,
                expiry_date DATE
            );
        """))

        # --------------------------------------------------
        # Shipments
        # --------------------------------------------------

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS shipments (
                shipment_id VARCHAR(20) PRIMARY KEY,
                batch_id VARCHAR(20),
                vehicle_id VARCHAR(20),
                origin VARCHAR(100),
                destination VARCHAR(100),
                departure_time TIMESTAMP,
                arrival_time TIMESTAMP,
                status VARCHAR(30),

                FOREIGN KEY (batch_id)
                REFERENCES product_batches(batch_id),

                FOREIGN KEY (vehicle_id)
                REFERENCES vehicles(vehicle_id)
            );
        """))

        # --------------------------------------------------
        # Sensor Logs
        # --------------------------------------------------

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS sensor_logs (
                log_id BIGINT PRIMARY KEY,
                sensor_id VARCHAR(20),
                shipment_id VARCHAR(20),
                recorded_at TIMESTAMP,
                temperature_c FLOAT,
                battery_level FLOAT,
                signal_strength FLOAT,
                network_status VARCHAR(30),

                FOREIGN KEY (sensor_id)
                REFERENCES sensors(sensor_id),

                FOREIGN KEY (shipment_id)
                REFERENCES shipments(shipment_id)
            );
        """))

        # --------------------------------------------------
        # Calibrations
        # --------------------------------------------------

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS calibrations (
                calibration_id INTEGER PRIMARY KEY,
                sensor_id VARCHAR(20),
                calibration_date DATE,
                expiry_date DATE,
                calibration_error FLOAT,
                status VARCHAR(30),

                FOREIGN KEY (sensor_id)
                REFERENCES sensors(sensor_id)
            );
        """))

        # --------------------------------------------------
        # Handovers
        # --------------------------------------------------

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS handovers (
                handover_id INTEGER PRIMARY KEY,
                shipment_id VARCHAR(20),
                from_party VARCHAR(100),
                to_party VARCHAR(100),
                location VARCHAR(100),
                handover_time TIMESTAMP,
                signature_status VARCHAR(30),

                FOREIGN KEY (shipment_id)
                REFERENCES shipments(shipment_id)
            );
        """))

        # --------------------------------------------------
        # Route Events
        # --------------------------------------------------

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS route_events (
                event_id INTEGER PRIMARY KEY,
                shipment_id VARCHAR(20),
                event_type VARCHAR(50),
                location VARCHAR(100),
                event_time TIMESTAMP,
                duration_minutes INTEGER,

                FOREIGN KEY (shipment_id)
                REFERENCES shipments(shipment_id)
            );
        """))

        # --------------------------------------------------
        # Compliance Results
        # --------------------------------------------------

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS compliance_results (
                shipment_id VARCHAR(20) PRIMARY KEY,

                temperature_status VARCHAR(30),
                calibration_status VARCHAR(30),
                custody_status VARCHAR(30),
                route_status VARCHAR(30),

                total_sensor_records INTEGER,
                excursion_records INTEGER,
                total_excursion_minutes FLOAT,

                invalid_calibration_sensors INTEGER,
                missing_signatures INTEGER,

                traffic_delays INTEGER,
                route_deviations INTEGER,
                total_delay_minutes FLOAT,

                overall_compliance VARCHAR(30),
                compliance_reason TEXT,

                FOREIGN KEY (shipment_id)
                REFERENCES shipments(shipment_id)
            );
        """))

    print("PostgreSQL tables created successfully!")


if __name__ == "__main__":
    create_tables()