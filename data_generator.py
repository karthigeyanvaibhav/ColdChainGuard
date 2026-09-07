import random
from datetime import date, timedelta

import numpy as np
import pandas as pd


# ==========================================================
# CONFIGURATION
# ==========================================================

RANDOM_SEED = 42

random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)


NUM_VEHICLES = 100
NUM_SENSORS = 150
NUM_BATCHES = 500


# ==========================================================
# 1. GENERATE VEHICLES
# ==========================================================

def generate_vehicles():

    vehicles = []

    for i in range(1, NUM_VEHICLES + 1):

        vehicle_id = f"V{i:03d}"

        vehicle_type = random.choice([
            "Refrigerated Van",
            "Refrigerated Truck"
        ])

        if vehicle_type == "Refrigerated Van":
            capacity = random.choice([500, 750, 1000, 1200])

        else:
            capacity = random.choice([1500, 2000, 2500, 3000])

        vehicles.append({
            "vehicle_id": vehicle_id,
            "vehicle_type": vehicle_type,
            "capacity_kg": capacity,
            "active": True
        })

    return pd.DataFrame(vehicles)


# ==========================================================
# 2. GENERATE SENSORS
# ==========================================================

def generate_sensors(vehicles_df):

    sensors = []

    start_date = date(2025, 1, 1)

    sensor_types = [
        "Temperature",
        "Temperature + Humidity"
    ]

    for i in range(1, NUM_SENSORS + 1):

        sensor_id = f"S{i:03d}"

        vehicle_id = random.choice(
            vehicles_df["vehicle_id"].tolist()
        )

        installation_date = (
            start_date +
            timedelta(days=random.randint(0, 500))
        )

        sensors.append({
            "sensor_id": sensor_id,
            "vehicle_id": vehicle_id,
            "sensor_type": random.choice(sensor_types),
            "installation_date": installation_date,
            "status": "Active"
        })

    return pd.DataFrame(sensors)


# ==========================================================
# 3. GENERATE PRODUCT BATCHES
# ==========================================================

def generate_product_batches():

    batches = []

    frozen_products = [
        "Frozen Peas",
        "Frozen Corn",
        "Frozen Mixed Vegetables",
        "Frozen French Fries",
        "Frozen Paneer"
    ]

    chilled_products = [
        "Fresh Milk",
        "Yogurt",
        "Fresh Paneer",
        "Cheese",
        "Fresh Cream"
    ]

    start_date = date(2026, 8, 1)

    for i in range(1, NUM_BATCHES + 1):

        batch_id = f"B{i:04d}"

        product_type = random.choice([
            "Frozen",
            "Chilled"
        ])

        if product_type == "Frozen":

            product_name = random.choice(
                frozen_products
            )

            min_temperature = -25.0
            max_temperature = -18.0

        else:

            product_name = random.choice(
                chilled_products
            )

            min_temperature = 2.0
            max_temperature = 8.0

        quantity = random.randint(20, 300)

        expiry_date = (
            start_date +
            timedelta(days=random.randint(3, 30))
        )

        batches.append({
            "batch_id": batch_id,
            "product_name": product_name,
            "product_type": product_type,
            "min_temperature_c": min_temperature,
            "max_temperature_c": max_temperature,
            "quantity": quantity,
            "expiry_date": expiry_date
        })

    return pd.DataFrame(batches)

# ==========================================================
# 4. GENERATE SHIPMENTS
# ==========================================================

def generate_shipments(vehicles_df, sensors_df, batches_df):

    shipments = []

    locations = [
        "Chennai",
        "Bangalore",
        "Coimbatore",
        "Hyderabad",
        "Kochi",
        "Madurai",
        "Salem",
        "Pune",
        "Mumbai",
        "Bengaluru"
    ]

    start_date = pd.Timestamp("2026-08-01")

    # Only vehicles that have at least one sensor
    sensor_vehicles = sensors_df["vehicle_id"].unique().tolist()

    # Create available vehicle/day combinations
    available_slots = []

    for day in range(7):

        for vehicle_id in sensor_vehicles:

            available_slots.append({
                "vehicle_id": vehicle_id,
                "day": day
            })

    # Shuffle slots so shipments are distributed randomly
    random.shuffle(available_slots)

    for i in range(NUM_BATCHES):

        shipment_id = f"SHP{i + 1:04d}"

        batch = batches_df.iloc[i]

        batch_id = batch["batch_id"]

        # Select a unique vehicle/day combination
        slot = available_slots[i]

        vehicle_id = slot["vehicle_id"]
        day = slot["day"]

        # Origin
        origin = random.choice(locations)

        # Destination must be different
        destination = random.choice(locations)

        while destination == origin:
            destination = random.choice(locations)

        # Departure
        departure_time = (
            start_date
            + pd.Timedelta(days=day)
            + pd.Timedelta(hours=random.randint(5, 10))
            + pd.Timedelta(minutes=random.randint(0, 59))
        )

        # Journey duration
        journey_duration = random.randint(60, 360)

        arrival_time = (
            departure_time
            + pd.Timedelta(minutes=journey_duration)
        )

        shipments.append({
            "shipment_id": shipment_id,
            "batch_id": batch_id,
            "vehicle_id": vehicle_id,
            "origin": origin,
            "destination": destination,
            "departure_time": departure_time,
            "arrival_time": arrival_time,
            "status": "Completed"
        })

    return pd.DataFrame(shipments)

# ==========================================================
# 5. GENERATE SENSOR LOGS
# ==========================================================

def generate_sensor_logs(
    shipments_df,
    sensors_df,
    batches_df
):

    sensor_logs = []

    # Create quick lookup dictionaries
    sensor_lookup = (
        sensors_df
        .groupby("vehicle_id")["sensor_id"]
        .apply(list)
        .to_dict()
    )

    batch_lookup = (
        batches_df
        .set_index("batch_id")
        .to_dict("index")
    )

    log_id = 1

    for _, shipment in shipments_df.iterrows():

        shipment_id = shipment["shipment_id"]
        vehicle_id = shipment["vehicle_id"]
        batch_id = shipment["batch_id"]

        departure = pd.Timestamp(
            shipment["departure_time"]
        )

        arrival = pd.Timestamp(
            shipment["arrival_time"]
        )

        # Select a sensor installed on this vehicle
        available_sensors = sensor_lookup.get(
            vehicle_id,
            []
        )

        if not available_sensors:
            continue

        sensor_id = random.choice(
            available_sensors
        )

        # Product temperature requirements
        batch = batch_lookup[batch_id]

        product_type = batch["product_type"]

        min_temp = batch["min_temperature_c"]
        max_temp = batch["max_temperature_c"]

        # Generate reading timestamps
        timestamps = pd.date_range(
            start=departure,
            end=arrival,
            freq="5min"
        )

        # Decide whether this shipment contains
        # deliberately injected problems
        missing_case = random.random() < 0.10
        noisy_case = random.random() < 0.08
        network_case = random.random() < 0.08
        excursion_case = random.random() < 0.15

        # Choose locations for injected events
        missing_index = (
            random.randint(5, len(timestamps) - 5)
            if missing_case and len(timestamps) > 10
            else None
        )

        noisy_index = (
            random.randint(5, len(timestamps) - 5)
            if noisy_case and len(timestamps) > 10
            else None
        )

        excursion_start = (
            random.randint(5, len(timestamps) - 10)
            if excursion_case and len(timestamps) > 15
            else None
        )

        network_start = (
            random.randint(5, len(timestamps) - 10)
            if network_case and len(timestamps) > 15
            else None
        )

        for index, timestamp in enumerate(timestamps):

            # --------------------------------------------------
            # BASE TEMPERATURE
            # --------------------------------------------------

            if product_type == "Frozen":

                base_temperature = -21.0

            else:

                base_temperature = 5.0

            # Small natural sensor variation
            temperature = (
                base_temperature
                + np.random.normal(0, 0.4)
            )

            # --------------------------------------------------
            # TEMPERATURE EXCURSION
            # --------------------------------------------------

            if (
                excursion_start is not None
                and excursion_start <= index < excursion_start + 4
            ):

                if product_type == "Frozen":

                    temperature = random.uniform(
                        -17.5,
                        -15.0
                    )

                else:

                    temperature = random.uniform(
                        9.0,
                        12.0
                    )

            # --------------------------------------------------
            # NOISY SENSOR READING
            # --------------------------------------------------

            if index == noisy_index:

                if product_type == "Frozen":

                    temperature = random.uniform(
                        -8.0,
                        0.0
                    )

                else:

                    temperature = random.uniform(
                        -5.0,
                        20.0
                    )

            # --------------------------------------------------
            # MISSING OBSERVATION
            # --------------------------------------------------

            if index == missing_index:

                temperature = None

            # --------------------------------------------------
            # NETWORK STATUS
            # --------------------------------------------------

            if (
                network_start is not None
                and network_start <= index < network_start + 4
            ):

                network_status = "Offline"
                signal_strength = 0

            else:

                network_status = "Online"

                signal_strength = random.randint(
                    70,
                    100
                )

            # --------------------------------------------------
            # BATTERY
            # --------------------------------------------------

            battery_level = random.uniform(
                70,
                100
            )

            sensor_logs.append({
                "log_id": log_id,
                "sensor_id": sensor_id,
                "shipment_id": shipment_id,
                "recorded_at": timestamp,
                "temperature_c": temperature,
                "battery_level": round(
                    battery_level,
                    2
                ),
                "signal_strength": signal_strength,
                "network_status": network_status
            })

            log_id += 1

    return pd.DataFrame(sensor_logs)

def generate_calibrations(sensors_df):

    calibrations = []

    calibration_id = 1

    for _, sensor in sensors_df.iterrows():

        sensor_id = sensor["sensor_id"]

        installation_date = pd.Timestamp(
            sensor["installation_date"]
        )

        # --------------------------------------------------
        # Make calibration valid for the shipment period
        # --------------------------------------------------

        calibration_date = pd.Timestamp(
            "2026-01-01"
        ) + pd.Timedelta(
            days=random.randint(0, 60)
        )

        expiry_date = (
            calibration_date
            + pd.Timedelta(days=365)
        )

        calibration_error = round(
            random.uniform(0.05, 0.40),
            3
        )

        status = "Valid"

        # --------------------------------------------------
        # Controlled failure cases
        # --------------------------------------------------

        failure_probability = random.random()

        # 10% expired
        if failure_probability < 0.10:

            expiry_date = pd.Timestamp(
                "2026-07-15"
            )

            status = "Expired"

        # 10% high calibration error
        elif failure_probability < 0.20:

            calibration_error = round(
                random.uniform(0.60, 1.20),
                3
            )

            status = "Calibration Error"

        calibrations.append({
            "calibration_id": calibration_id,
            "sensor_id": sensor_id,
            "calibration_date": calibration_date.date(),
            "expiry_date": expiry_date.date(),
            "calibration_error": calibration_error,
            "status": status
        })

        calibration_id += 1

    return pd.DataFrame(calibrations)

    # ==========================================================
# 7. GENERATE HANDOVER RECORDS
# ==========================================================

def generate_handovers(shipments_df):

    handovers = []

    parties = [
        "Warehouse",
        "Transporter",
        "Distribution Center",
        "Retail Store",
        "Delivery Partner"
    ]

    locations = [
        "Chennai Warehouse",
        "Bangalore DC",
        "Coimbatore Hub",
        "Hyderabad DC",
        "Kochi Hub",
        "Madurai Store",
        "Salem Hub",
        "Pune DC"
    ]

    handover_id = 1

    for _, shipment in shipments_df.iterrows():

        shipment_id = shipment["shipment_id"]

        departure = pd.Timestamp(
            shipment["departure_time"]
        )

        arrival = pd.Timestamp(
            shipment["arrival_time"]
        )

        # Most shipments have 2–4 custody transfers
        number_of_handovers = random.randint(2, 4)

        total_minutes = int(
            (arrival - departure).total_seconds() / 60
        )

        # Generate increasing handover times
        possible_minutes = list(
            range(
                10,
                max(11, total_minutes - 10)
            )
        )

        if len(possible_minutes) < number_of_handovers:
            number_of_handovers = len(possible_minutes)

        handover_minutes = sorted(
            random.sample(
                possible_minutes,
                number_of_handovers
            )
        )

        previous_party = "Warehouse"

        for i, minutes in enumerate(handover_minutes):

            from_party = previous_party

            if i == number_of_handovers - 1:
                to_party = "Retail Store"
            else:
                to_party = random.choice([
                    "Transporter",
                    "Distribution Center",
                    "Delivery Partner"
                ])

            location = random.choice(locations)

            handover_time = (
                departure
                + pd.Timedelta(minutes=minutes)
            )

            # Normally signed
            signature_status = "Signed"

            # Inject missing custody evidence
            if random.random() < 0.08:
                signature_status = "Missing"

            handovers.append({
                "handover_id": handover_id,
                "shipment_id": shipment_id,
                "from_party": from_party,
                "to_party": to_party,
                "location": location,
                "handover_time": handover_time,
                "signature_status": signature_status
            })

            previous_party = to_party
            handover_id += 1

    return pd.DataFrame(handovers)

# ==========================================================
# 8. GENERATE ROUTE EVENTS
# ==========================================================

def generate_route_events(shipments_df):

    route_events = []

    event_id = 1

    event_types = [
        "Checkpoint",
        "Cold Storage Stop",
        "Rest Stop",
        "Traffic Delay",
        "Route Deviation"
    ]

    for _, shipment in shipments_df.iterrows():

        shipment_id = shipment["shipment_id"]

        departure = pd.Timestamp(
            shipment["departure_time"]
        )

        arrival = pd.Timestamp(
            shipment["arrival_time"]
        )

        total_minutes = int(
            (arrival - departure).total_seconds()
            / 60
        )

        # --------------------------------------------------
        # Every shipment gets Departure
        # --------------------------------------------------

        route_events.append({
            "event_id": event_id,
            "shipment_id": shipment_id,
            "event_type": "Departure",
            "location": shipment["origin"],
            "event_time": departure,
            "duration_minutes": 0
        })

        event_id += 1

        # --------------------------------------------------
        # Normal route events
        # --------------------------------------------------

        number_of_events = random.randint(3, 6)

        for _ in range(number_of_events):

            event_time = (
                departure
                +
                pd.Timedelta(
                    minutes=random.randint(
                        10,
                        max(10, total_minutes - 10)
                    )
                )
            )

            probability = random.random()

            # ----------------------------------------------
            # Controlled event distribution
            # ----------------------------------------------

            if probability < 0.60:

                event_type = "Checkpoint"

                duration = 0

            elif probability < 0.75:

                event_type = "Cold Storage Stop"

                duration = random.randint(
                    5,
                    20
                )

            elif probability < 0.90:

                event_type = "Rest Stop"

                duration = random.randint(
                    10,
                    40
                )

            elif probability < 0.97:

                event_type = "Traffic Delay"

                duration = random.randint(
                    10,
                    60
                )

            else:

                event_type = "Route Deviation"

                duration = random.randint(
                    15,
                    90
                )

            locations = [
                "City Entry",
                "Highway Checkpoint",
                "Cold Storage Facility",
                "Fuel Station",
                "Rest Area",
                "Distribution Center"
            ]

            location = random.choice(
                locations
            )

            route_events.append({
                "event_id": event_id,
                "shipment_id": shipment_id,
                "event_type": event_type,
                "location": location,
                "event_time": event_time,
                "duration_minutes": duration
            })

            event_id += 1

        # --------------------------------------------------
        # Every shipment gets Arrival
        # --------------------------------------------------

        route_events.append({
            "event_id": event_id,
            "shipment_id": shipment_id,
            "event_type": "Arrival",
            "location": shipment["destination"],
            "event_time": arrival,
            "duration_minutes": 0
        })

        event_id += 1

    return pd.DataFrame(route_events)


# ==========================================================
# MAIN
# ==========================================================

def main():

    print("=" * 60)
    print("COLDCHAINGUARD - DATA GENERATION")
    print("=" * 60)

    # Generate vehicles
    vehicles_df = generate_vehicles()

    # Generate sensors
    sensors_df = generate_sensors(vehicles_df)

    # Generate product batches
    batches_df = generate_product_batches()

    # Generate shipments
    shipments_df = generate_shipments(
    vehicles_df,
    sensors_df,
    batches_df
    )

    # Generate sensor logs
    sensor_logs_df = generate_sensor_logs(
    shipments_df,
    sensors_df,
    batches_df
    )

    # Generate calibration records
    calibrations_df = generate_calibrations(
    sensors_df
    )

    # Generate handovers
    handovers_df = generate_handovers(
    shipments_df
    )

    # Generate route events
    route_events_df = generate_route_events(
    shipments_df
    )

    print("\nGenerated Data")
    print("-" * 60)

    print(f"Vehicles       : {len(vehicles_df)}")
    print(f"Sensors        : {len(sensors_df)}")
    print(f"Product Batches: {len(batches_df)}")
    print(f"Shipments      : {len(shipments_df)}")
    print(f"Sensor Logs    : {len(sensor_logs_df)}")
    print(f"Calibrations   : {len(calibrations_df)}")
    print(f"Handovers      : {len(handovers_df)}")
    print(f"Route Events   : {len(route_events_df)}")

    # Display samples
    print("\nVehicle Sample:")
    print(vehicles_df.head())

    print("\nSensor Sample:")
    print(sensors_df.head())

    print("\nProduct Batch Sample:")
    print(batches_df.head())

    print("\nShipment Sample:")
    print(shipments_df.head())

    print("\nSensor Log Sample:")
    print(sensor_logs_df.head())

    print("\nCalibration Sample:")
    print(calibrations_df.head())

    print("\nHandover Sample:")
    print(handovers_df.head())

    print("\nRoute Event Sample:")
    print(route_events_df.head())

    # Save datasets
    vehicles_df.to_csv(
        "data/raw/vehicles.csv",
        index=False
    )

    sensors_df.to_csv(
        "data/raw/sensors.csv",
        index=False
    )

    batches_df.to_csv(
        "data/raw/product_batches.csv",
        index=False
    )

    shipments_df.to_csv(
        "data/raw/shipments.csv",
        index=False
    )

    sensor_logs_df.to_csv(
        "data/raw/sensor_logs.csv",
        index=False
    )

    calibrations_df.to_csv(
        "data/raw/calibrations.csv",
        index=False
    )

    handovers_df.to_csv(
    "data/raw/handovers.csv",
    index=False
    )

    route_events_df.to_csv(
        "data/raw/route_events.csv",
        index=False
    )

    print("\nFiles saved successfully:")
    print("data/raw/vehicles.csv")
    print("data/raw/sensors.csv")
    print("data/raw/product_batches.csv")
    print("data/raw/shipments.csv")
    print("data/raw/sensor_logs.csv")
    print("data/raw/calibrations.csv")
    print("data/raw/handovers.csv")
    print("data/raw/route_events.csv")

if __name__ == "__main__":
    main()