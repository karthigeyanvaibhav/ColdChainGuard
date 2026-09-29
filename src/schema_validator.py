"""
src/schema_validator.py
ColdChainGuard - Input Dataset Schema Validator

Validates any input CSV dataset against the required ColdChainGuard schema.
Run standalone or import validate_dataset() in other scripts.

Usage:
  python src/schema_validator.py                     # validates data/raw/
  python src/schema_validator.py --data-dir data/input
  python src/schema_validator.py --data-dir data/test_dataset
"""

import os
import sys
import argparse
import pandas as pd
import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ─────────────────────────────────────────────────────────────────────────────
# SCHEMA DEFINITION
# ─────────────────────────────────────────────────────────────────────────────
REQUIRED_SCHEMA = {
    "vehicles": {
        "file": "vehicles.csv",
        "pk": "vehicle_id",
        "required_cols": ["vehicle_id", "vehicle_type", "capacity_kg", "active"],
        "numeric_cols": {"capacity_kg": (0, None)},
        "categorical_cols": {"vehicle_type": ["Refrigerated Van", "Refrigerated Truck"]},
    },
    "sensors": {
        "file": "sensors.csv",
        "pk": "sensor_id",
        "required_cols": ["sensor_id", "vehicle_id", "sensor_type", "installation_date", "status"],
        "fk": {"vehicle_id": "vehicles"},
        "date_cols": ["installation_date"],
    },
    "product_batches": {
        "file": "product_batches.csv",
        "pk": "batch_id",
        "required_cols": ["batch_id", "product_name", "product_type",
                          "min_temperature_c", "max_temperature_c", "quantity", "expiry_date"],
        "numeric_cols": {"min_temperature_c": (None, None), "max_temperature_c": (None, None),
                         "quantity": (1, None)},
        "categorical_cols": {"product_type": ["Frozen", "Chilled"]},
        "date_cols": ["expiry_date"],
    },
    "shipments": {
        "file": "shipments.csv",
        "pk": "shipment_id",
        "required_cols": ["shipment_id", "batch_id", "vehicle_id", "origin",
                          "destination", "departure_time", "arrival_time", "status"],
        "fk": {"batch_id": "product_batches", "vehicle_id": "vehicles"},
        "datetime_cols": ["departure_time", "arrival_time"],
    },
    "sensor_logs": {
        "file": "sensor_logs.csv",
        "pk": "log_id",
        "required_cols": ["log_id", "sensor_id", "shipment_id", "recorded_at",
                          "temperature_c", "battery_level"],
        "fk": {"sensor_id": "sensors", "shipment_id": "shipments"},
        "datetime_cols": ["recorded_at"],
        "numeric_cols": {"battery_level": (0, 100)},
        "nullable_cols": ["temperature_c", "signal_strength"],
    },
    "calibrations": {
        "file": "calibrations.csv",
        "pk": "calibration_id",
        "required_cols": ["calibration_id", "sensor_id", "calibration_date",
                          "expiry_date", "calibration_error", "status"],
        "fk": {"sensor_id": "sensors"},
        "date_cols": ["calibration_date", "expiry_date"],
        "nullable_cols": ["calibration_error"],
    },
    "handovers": {
        "file": "handovers.csv",
        "pk": "handover_id",
        "required_cols": ["handover_id", "shipment_id", "from_party", "to_party",
                          "location", "handover_time"],
        "fk": {"shipment_id": "shipments"},
        "datetime_cols": ["handover_time"],
    },
    "route_events": {
        "file": "route_events.csv",
        "pk": "event_id",
        "required_cols": ["event_id", "shipment_id", "event_type",
                          "location", "event_time"],
        "fk": {"shipment_id": "shipments"},
        "datetime_cols": ["event_time"],
        "nullable_cols": ["duration_minutes"],
    },
}

FK_TABLE_ORDER = ["vehicles", "sensors", "product_batches", "shipments",
                  "sensor_logs", "calibrations", "handovers", "route_events"]


# ─────────────────────────────────────────────────────────────────────────────
# VALIDATION FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def _check_file(schema, data_dir):
    path = os.path.join(data_dir, schema["file"])
    if not os.path.exists(path):
        return None, [f"File not found: {schema['file']}"]
    try:
        df = pd.read_csv(path)
        return df, []
    except Exception as e:
        return None, [f"Cannot read {schema['file']}: {e}"]


def _check_columns(df, schema):
    issues = []
    missing = [c for c in schema["required_cols"] if c not in df.columns]
    if missing:
        issues.append(f"Missing required columns: {missing}")
    return issues


def _check_pk(df, schema):
    issues = []
    pk = schema.get("pk")
    if pk and pk in df.columns:
        dupes = df[pk].duplicated().sum()
        if dupes:
            issues.append(f"Duplicate primary keys in '{pk}': {dupes} duplicates")
        nulls = df[pk].isna().sum()
        if nulls:
            issues.append(f"Null primary keys in '{pk}': {nulls} nulls")
    return issues


def _check_fk(df, schema, loaded):
    issues = []
    for col, parent_table in schema.get("fk", {}).items():
        if col not in df.columns:
            continue
        if parent_table not in loaded:
            continue
        parent_df = loaded[parent_table]
        parent_pk = REQUIRED_SCHEMA[parent_table]["pk"]
        if parent_pk not in parent_df.columns:
            continue
        parent_vals = set(parent_df[parent_pk].dropna().astype(str))
        child_vals  = set(df[col].dropna().astype(str))
        orphans = child_vals - parent_vals
        if orphans:
            sample = list(orphans)[:5]
            issues.append(
                f"FK '{col}' -> '{parent_table}.{parent_pk}': "
                f"{len(orphans)} orphan values. Sample: {sample}"
            )
    return issues


def _check_numerics(df, schema):
    issues = []
    for col, (lo, hi) in schema.get("numeric_cols", {}).items():
        if col not in df.columns:
            continue
        s = pd.to_numeric(df[col], errors="coerce")
        bad = s.isna() & df[col].notna()
        if bad.sum():
            issues.append(f"Column '{col}': {bad.sum()} non-numeric values")
        if lo is not None:
            below = (s < lo).sum()
            if below:
                issues.append(f"Column '{col}': {below} values below minimum {lo}")
        if hi is not None:
            above = (s > hi).sum()
            if above:
                issues.append(f"Column '{col}': {above} values above maximum {hi}")
    return issues


def _check_categoricals(df, schema):
    issues = []
    for col, valid_vals in schema.get("categorical_cols", {}).items():
        if col not in df.columns:
            continue
        invalid = ~df[col].isin(valid_vals) & df[col].notna()
        if invalid.sum():
            bad_sample = df.loc[invalid, col].unique()[:5].tolist()
            issues.append(
                f"Column '{col}': {invalid.sum()} invalid values "
                f"(expected one of {valid_vals}). Sample: {bad_sample}"
            )
    return issues


def _check_dates(df, schema):
    issues = []
    for col in schema.get("date_cols", []) + schema.get("datetime_cols", []):
        if col not in df.columns:
            continue
        parsed = pd.to_datetime(df[col], errors="coerce")
        bad = parsed.isna() & df[col].notna()
        if bad.sum():
            issues.append(f"Column '{col}': {bad.sum()} invalid date values")
    return issues


# ─────────────────────────────────────────────────────────────────────────────
# MAIN VALIDATION
# ─────────────────────────────────────────────────────────────────────────────

def validate_dataset(data_dir):
    """
    Validate all CSVs in data_dir against the ColdChainGuard schema.
    Returns: dict of {table_name: {status, issues, row_count}}
    """
    results = {}
    loaded  = {}  # for FK checks

    for table in FK_TABLE_ORDER:
        schema = REQUIRED_SCHEMA[table]
        issues = []

        # 1. File existence + load
        df, file_issues = _check_file(schema, data_dir)
        issues.extend(file_issues)
        if df is None:
            results[table] = {"status": "FAIL", "issues": issues, "row_count": 0}
            continue

        # 2. Row count
        if len(df) == 0:
            issues.append("File is empty (0 rows)")
            results[table] = {"status": "FAIL", "issues": issues, "row_count": 0}
            continue

        # 3. Required columns
        issues.extend(_check_columns(df, schema))

        # 4. Primary key
        issues.extend(_check_pk(df, schema))

        # 5. Foreign keys (against already-loaded parents)
        issues.extend(_check_fk(df, schema, loaded))

        # 6. Numerics
        issues.extend(_check_numerics(df, schema))

        # 7. Categoricals
        issues.extend(_check_categoricals(df, schema))

        # 8. Dates
        issues.extend(_check_dates(df, schema))

        loaded[table] = df
        status = "FAIL" if issues else "PASS"
        results[table] = {
            "status": status,
            "issues": issues,
            "row_count": len(df),
            "columns": list(df.columns),
        }

    return results


def print_validation_report(results, data_dir):
    print("=" * 70)
    print("COLDCHAINGUARD SCHEMA VALIDATION REPORT")
    print(f"Data directory: {data_dir}")
    print("=" * 70)

    total = len(results)
    passed = sum(1 for r in results.values() if r["status"] == "PASS")
    warnings = 0

    for table, r in results.items():
        status_str = f"[{r['status']}]"
        print(f"\n  {status_str:<8} {table:<25} ({r['row_count']:,} rows)")
        for issue in r.get("issues", []):
            print(f"           ! {issue}")

    print("\n" + "=" * 70)
    print(f"  RESULT: {passed}/{total} tables valid")
    if passed == total:
        print("  STATUS: DATASET IS VALID - safe to load into pipeline")
    else:
        failed = [t for t, r in results.items() if r["status"] == "FAIL"]
        print(f"  STATUS: VALIDATION FAILED - fix issues in: {failed}")
    print("=" * 70)

    return passed == total


def main():
    parser = argparse.ArgumentParser(
        description="ColdChainGuard Input Dataset Schema Validator"
    )
    parser.add_argument(
        "--data-dir", type=str, default="data/raw",
        help="Directory containing CSV input files (default: data/raw)"
    )
    args = parser.parse_args()

    data_dir = os.path.join(PROJECT_ROOT, args.data_dir) \
        if not os.path.isabs(args.data_dir) else args.data_dir

    results = validate_dataset(data_dir)
    ok = print_validation_report(results, data_dir)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
