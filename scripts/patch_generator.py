import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_file = os.path.join(PROJECT_ROOT, "src", "data_generator.py")

with open(src_file, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Keep everything up to and including line 824 (0-indexed: 823)
# Find the '# MAIN' section start
main_start = None
for i, line in enumerate(lines):
    if "# MAIN" in line and "==" in line and i > 820:
        main_start = i - 1  # include the blank line before
        break

if main_start is None:
    # fallback: look for def main
    for i, line in enumerate(lines):
        if line.strip().startswith("def main"):
            main_start = i - 2
            break

keep_lines = lines[:main_start]

new_tail = '''

# ==========================================================
# MAIN
# ==========================================================

def main(output_dir=None):
    """Generate all synthetic datasets and save to output_dir."""
    import os as _os
    if output_dir is None:
        _pr = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_dir = os.path.join(_pr, "data", "raw")
    if not _os.path.isabs(output_dir):
        _pr = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_dir = _os.path.join(_pr, output_dir)
    _os.makedirs(output_dir, exist_ok=True)

    print("=" * 60)
    print("COLDCHAINGUARD - DATA GENERATION")
    print("=" * 60)
    print(f"  NUM_VEHICLES : {NUM_VEHICLES}")
    print(f"  NUM_SENSORS  : {NUM_SENSORS}")
    print(f"  NUM_BATCHES  : {NUM_BATCHES}")
    print("=" * 60)

    vehicles_df    = generate_vehicles()
    sensors_df     = generate_sensors(vehicles_df)
    batches_df     = generate_product_batches()
    shipments_df   = generate_shipments(vehicles_df, sensors_df, batches_df)
    sensor_logs_df = generate_sensor_logs(shipments_df, sensors_df, batches_df)
    calibrations_df = generate_calibrations(sensors_df)
    handovers_df   = generate_handovers(shipments_df)
    route_events_df = generate_route_events(shipments_df)

    print("\\nGenerated Data")
    print("-" * 60)
    print(f"Vehicles       : {len(vehicles_df)}")
    print(f"Sensors        : {len(sensors_df)}")
    print(f"Product Batches: {len(batches_df)}")
    print(f"Shipments      : {len(shipments_df)}")
    print(f"Sensor Logs    : {len(sensor_logs_df)}")
    print(f"Calibrations   : {len(calibrations_df)}")
    print(f"Handovers      : {len(handovers_df)}")
    print(f"Route Events   : {len(route_events_df)}")

    vehicles_df.to_csv(_os.path.join(output_dir, "vehicles.csv"), index=False)
    sensors_df.to_csv(_os.path.join(output_dir, "sensors.csv"), index=False)
    batches_df.to_csv(_os.path.join(output_dir, "product_batches.csv"), index=False)
    shipments_df.to_csv(_os.path.join(output_dir, "shipments.csv"), index=False)
    sensor_logs_df.to_csv(_os.path.join(output_dir, "sensor_logs.csv"), index=False)
    calibrations_df.to_csv(_os.path.join(output_dir, "calibrations.csv"), index=False)
    handovers_df.to_csv(_os.path.join(output_dir, "handovers.csv"), index=False)
    route_events_df.to_csv(_os.path.join(output_dir, "route_events.csv"), index=False)

    print(f"\\nDataset saved to: {output_dir}/")
    for name, df in [
        ("vehicles.csv", vehicles_df), ("sensors.csv", sensors_df),
        ("product_batches.csv", batches_df), ("shipments.csv", shipments_df),
        ("sensor_logs.csv", sensor_logs_df), ("calibrations.csv", calibrations_df),
        ("handovers.csv", handovers_df), ("route_events.csv", route_events_df),
    ]:
        print(f"  {name:<25}: {len(df)} rows")

    return {
        "vehicles": len(vehicles_df), "sensors": len(sensors_df),
        "batches": len(batches_df), "shipments": len(shipments_df),
        "sensor_logs": len(sensor_logs_df), "calibrations": len(calibrations_df),
        "handovers": len(handovers_df), "route_events": len(route_events_df),
    }


if __name__ == "__main__":
    import argparse
    import os as _os2

    _PROJECT_ROOT = _os2.path.dirname(_os2.path.dirname(_os2.path.abspath(__file__)))

    parser = argparse.ArgumentParser(description="ColdChainGuard Synthetic Data Generator")
    parser.add_argument("--vehicles",   type=int,  default=NUM_VEHICLES,
                        help=f"Number of vehicles (default {NUM_VEHICLES})")
    parser.add_argument("--sensors",    type=int,  default=NUM_SENSORS,
                        help=f"Number of sensors (default {NUM_SENSORS})")
    parser.add_argument("--batches",    type=int,  default=NUM_BATCHES,
                        help=f"Number of batches/shipments (default {NUM_BATCHES})")
    parser.add_argument("--seed",       type=int,  default=RANDOM_SEED,
                        help=f"Random seed (default {RANDOM_SEED})")
    parser.add_argument("--output-dir", type=str,  default="data/raw",
                        help="Output directory (default: data/raw)")
    args = parser.parse_args()

    # Override module-level globals before calling generators
    NUM_VEHICLES = args.vehicles
    NUM_SENSORS  = args.sensors
    NUM_BATCHES  = args.batches
    random.seed(args.seed)
    np.random.seed(args.seed)

    odir = (_os2.path.join(_PROJECT_ROOT, args.output_dir)
            if not _os2.path.isabs(args.output_dir) else args.output_dir)

    main(output_dir=odir)
'''

with open(src_file, "w", encoding="utf-8") as f:
    f.writelines(keep_lines)
    f.write(new_tail)

print(f"[OK] data_generator.py patched. Total lines: {len(keep_lines) + len(new_tail.splitlines())}")
