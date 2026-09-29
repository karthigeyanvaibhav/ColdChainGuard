"""
scripts/reset_database.py
ColdChainGuard - Safe Database Reset Tool

WARNING: This TRUNCATES all data in the ColdChainGuard PostgreSQL database.
Requires --confirm flag to prevent accidental execution.

Usage:
  python scripts/reset_database.py --confirm
  python scripts/reset_database.py --confirm --tables operational   (only operational tables)
  python scripts/reset_database.py --confirm --tables analytical    (only analytical tables)
  python scripts/reset_database.py --confirm --tables all           (default: all tables)
"""

import sys
import os
import argparse

# ---------------------------------------------------------------------------
# Connect
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import create_engine, text, inspect

DB_URL = "postgresql+psycopg://postgres:1322@localhost:5432/coldchainguard"
engine = create_engine(DB_URL, pool_pre_ping=True)

# Truncate order (children before parents, using CASCADE for safety)
ANALYTICAL_TABLES = [
    "fact_handovers", "fact_route_events", "fact_sensor_logs",
    "fact_shipments", "dim_date", "dim_product", "dim_vehicle",
]
OPERATIONAL_TABLES = [
    "compliance_results", "route_events", "handovers", "calibrations",
    "sensor_logs", "shipments", "product_batches", "sensors", "vehicles",
]


def get_existing_tables():
    ins = inspect(engine)
    return set(ins.get_table_names())


def get_count(table):
    try:
        with engine.connect() as c:
            return c.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
    except Exception:
        return None


def print_counts(tables, label=""):
    existing = get_existing_tables()
    if label:
        print(f"\n{label}")
    for t in tables:
        if t in existing:
            n = get_count(t)
            print(f"  {t:<30}: {n if n is not None else 'N/A'} rows")
        else:
            print(f"  {t:<30}: [TABLE NOT FOUND]")


def reset_tables(tables):
    existing = get_existing_tables()
    with engine.begin() as conn:
        for t in tables:
            if t in existing:
                try:
                    conn.execute(text(f"TRUNCATE TABLE {t} CASCADE"))
                    print(f"  [OK]   Truncated {t}")
                except Exception as e:
                    print(f"  [WARN] Could not truncate {t}: {e}")
            else:
                print(f"  [SKIP] Table not found: {t}")


def main():
    parser = argparse.ArgumentParser(
        description="ColdChainGuard Safe Database Reset"
    )
    parser.add_argument(
        "--confirm", action="store_true",
        help="Required safety flag to execute the reset"
    )
    parser.add_argument(
        "--tables", choices=["all", "operational", "analytical"], default="all",
        help="Which tables to truncate (default: all)"
    )
    args = parser.parse_args()

    if not args.confirm:
        print("=" * 60)
        print("COLDCHAINGUARD DATABASE RESET")
        print("=" * 60)
        print("\nSafety check: pass --confirm to execute the database reset.")
        print("Example:")
        print("  python scripts/reset_database.py --confirm")
        print("  python scripts/reset_database.py --confirm --tables operational")
        print("\nThis will TRUNCATE all data. Run database/load_data.py afterward to reload.")
        sys.exit(0)

    if args.tables == "all":
        tables_to_reset = ANALYTICAL_TABLES + OPERATIONAL_TABLES
    elif args.tables == "analytical":
        tables_to_reset = ANALYTICAL_TABLES
    else:
        tables_to_reset = OPERATIONAL_TABLES

    print("=" * 60)
    print("COLDCHAINGUARD DATABASE RESET")
    print("=" * 60)
    print(f"Scope: {args.tables} tables")

    print_counts(tables_to_reset, label="BEFORE:")

    print("\nTruncating tables...")
    reset_tables(tables_to_reset)

    print_counts(tables_to_reset, label="AFTER:")

    print("\n" + "=" * 60)
    print("Database reset complete.")
    print("To reload original data: python database/load_data.py")
    print("To generate new data:    python src/data_generator.py --vehicles N --batches N")
    print("=" * 60)


if __name__ == "__main__":
    main()
