-- =========================================================
-- COLDCHAINGUARD DATABASE SCHEMA
-- Automated Cold-Chain Compliance Evidence System
-- =========================================================


-- =========================================================
-- 1. VEHICLES
-- =========================================================

CREATE TABLE vehicles (
    vehicle_id VARCHAR(20) PRIMARY KEY,
    vehicle_type VARCHAR(30) NOT NULL,
    capacity_kg NUMERIC(10,2) NOT NULL,
    active BOOLEAN DEFAULT TRUE
);


-- =========================================================
-- 2. SENSORS
-- =========================================================

CREATE TABLE sensors (
    sensor_id VARCHAR(20) PRIMARY KEY,
    vehicle_id VARCHAR(20) NOT NULL,
    sensor_type VARCHAR(30) NOT NULL,
    installation_date DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'Active',

    CONSTRAINT fk_sensor_vehicle
        FOREIGN KEY (vehicle_id)
        REFERENCES vehicles(vehicle_id)
);


-- =========================================================
-- 3. SENSOR LOGS
-- =========================================================

CREATE TABLE sensor_logs (
    log_id BIGSERIAL PRIMARY KEY,
    sensor_id VARCHAR(20) NOT NULL,
    recorded_at TIMESTAMP NOT NULL,
    temperature_c NUMERIC(6,2),
    battery_level NUMERIC(5,2),
    signal_strength INTEGER,
    network_status VARCHAR(20) NOT NULL,

    CONSTRAINT fk_sensor_log_sensor
        FOREIGN KEY (sensor_id)
        REFERENCES sensors(sensor_id)
);


-- =========================================================
-- 4. CALIBRATION RECORDS
-- =========================================================

CREATE TABLE calibrations (
    calibration_id BIGSERIAL PRIMARY KEY,
    sensor_id VARCHAR(20) NOT NULL,
    calibration_date DATE NOT NULL,
    expiry_date DATE NOT NULL,
    calibration_error NUMERIC(6,3),
    status VARCHAR(20) NOT NULL,

    CONSTRAINT fk_calibration_sensor
        FOREIGN KEY (sensor_id)
        REFERENCES sensors(sensor_id)
);


-- =========================================================
-- 5. PRODUCT BATCHES
-- =========================================================

CREATE TABLE product_batches (
    batch_id VARCHAR(30) PRIMARY KEY,
    product_name VARCHAR(100) NOT NULL,
    product_type VARCHAR(20) NOT NULL,
    min_temperature_c NUMERIC(5,2) NOT NULL,
    max_temperature_c NUMERIC(5,2) NOT NULL,
    quantity INTEGER NOT NULL,
    expiry_date DATE NOT NULL
);


-- =========================================================
-- 6. SHIPMENTS
-- =========================================================

CREATE TABLE shipments (
    shipment_id VARCHAR(30) PRIMARY KEY,
    batch_id VARCHAR(30) NOT NULL,
    vehicle_id VARCHAR(20) NOT NULL,
    origin VARCHAR(100) NOT NULL,
    destination VARCHAR(100) NOT NULL,
    departure_time TIMESTAMP NOT NULL,
    arrival_time TIMESTAMP,
    status VARCHAR(30) DEFAULT 'In Transit',

    CONSTRAINT fk_shipment_batch
        FOREIGN KEY (batch_id)
        REFERENCES product_batches(batch_id),

    CONSTRAINT fk_shipment_vehicle
        FOREIGN KEY (vehicle_id)
        REFERENCES vehicles(vehicle_id)
);


-- =========================================================
-- 7. HANDOVER / CUSTODY RECORDS
-- =========================================================

CREATE TABLE handovers (
    handover_id BIGSERIAL PRIMARY KEY,
    shipment_id VARCHAR(30) NOT NULL,
    from_party VARCHAR(100) NOT NULL,
    to_party VARCHAR(100) NOT NULL,
    location VARCHAR(100) NOT NULL,
    handover_time TIMESTAMP NOT NULL,
    signature_status VARCHAR(20) NOT NULL,

    CONSTRAINT fk_handover_shipment
        FOREIGN KEY (shipment_id)
        REFERENCES shipments(shipment_id)
);


-- =========================================================
-- 8. ROUTE EVENTS
-- =========================================================

CREATE TABLE route_events (
    event_id BIGSERIAL PRIMARY KEY,
    shipment_id VARCHAR(30) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    location VARCHAR(100),
    event_time TIMESTAMP NOT NULL,
    duration_minutes INTEGER DEFAULT 0,

    CONSTRAINT fk_route_shipment
        FOREIGN KEY (shipment_id)
        REFERENCES shipments(shipment_id)
);


-- =========================================================
-- 9. COMPLIANCE EVENTS
-- =========================================================

CREATE TABLE compliance_events (
    compliance_event_id BIGSERIAL PRIMARY KEY,
    shipment_id VARCHAR(30) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    description TEXT NOT NULL,
    detected_at TIMESTAMP NOT NULL,
    automated_decision VARCHAR(30) NOT NULL,
    status VARCHAR(30) DEFAULT 'Open',

    CONSTRAINT fk_compliance_shipment
        FOREIGN KEY (shipment_id)
        REFERENCES shipments(shipment_id)
);


-- =========================================================
-- 10. DISPATCHER OVERRIDES
-- =========================================================

CREATE TABLE dispatcher_overrides (
    override_id BIGSERIAL PRIMARY KEY,
    shipment_id VARCHAR(30) NOT NULL,
    compliance_event_id BIGINT,
    dispatcher VARCHAR(100) NOT NULL,
    original_decision VARCHAR(30) NOT NULL,
    new_decision VARCHAR(30) NOT NULL,
    reason TEXT NOT NULL,
    override_time TIMESTAMP NOT NULL,

    CONSTRAINT fk_override_shipment
        FOREIGN KEY (shipment_id)
        REFERENCES shipments(shipment_id),

    CONSTRAINT fk_override_event
        FOREIGN KEY (compliance_event_id)
        REFERENCES compliance_events(compliance_event_id)
);


-- =========================================================
-- 11. PLAN CHANGE HISTORY
-- =========================================================

CREATE TABLE plan_change_history (
    change_id BIGSERIAL PRIMARY KEY,
    shipment_id VARCHAR(30) NOT NULL,
    changed_by VARCHAR(100) NOT NULL,
    change_type VARCHAR(50) NOT NULL,
    previous_value TEXT,
    new_value TEXT,
    reason TEXT NOT NULL,
    changed_at TIMESTAMP NOT NULL,

    CONSTRAINT fk_plan_change_shipment
        FOREIGN KEY (shipment_id)
        REFERENCES shipments(shipment_id)
);


-- =========================================================
-- 12. AUDIT REPORTS
-- =========================================================

CREATE TABLE audit_reports (
    report_id BIGSERIAL PRIMARY KEY,
    shipment_id VARCHAR(30) NOT NULL,
    generated_at TIMESTAMP NOT NULL,
    final_decision VARCHAR(30) NOT NULL,
    evidence_completeness NUMERIC(5,2),
    report_file_path TEXT,

    CONSTRAINT fk_report_shipment
        FOREIGN KEY (shipment_id)
        REFERENCES shipments(shipment_id)
);