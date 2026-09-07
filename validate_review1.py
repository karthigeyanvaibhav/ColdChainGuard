"""
src/validate_review1.py
ColdChainGuard - Review 1 (35%) Completion Validator

Checks all deliverables for Day 1, Day 2, and Day 3 and prints
a PASS/FAIL report for the first 35% milestone submission.
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from sqlalchemy import create_engine, text, inspect

DB_URL = "postgresql+psycopg://postgres:1322@localhost:5432/coldchainguard"

ETL_DIR = os.path.join(PROJECT_ROOT, "data", "etl")
EDA_DIR = os.path.join(PROJECT_ROOT, "data", "eda")
SEG_DIR = os.path.join(PROJECT_ROOT, "data", "segmentation")
PLOT_DIR = os.path.join(EDA_DIR, "plots")
STAR_DIR = os.path.join(ETL_DIR, "star_schema")
DOC_DIR  = os.path.join(PROJECT_ROOT, "docs")
SRC_DIR  = os.path.join(PROJECT_ROOT, "src")


# ==========================================================
# HELPERS
# ==========================================================
def check_file(path, label):
    exists = os.path.isfile(path)
    return exists, label, path


def check_dir_nonempty(path, label):
    if not os.path.isdir(path):
        return False, label, path
    files = [f for f in os.listdir(path) if not f.startswith(".")]
    return len(files) > 0, label, path


def check_db_table(engine, table, label):
    try:
        tables = inspect(engine).get_table_names()
        if table not in tables:
            return False, label, f"table: {table} (missing)"
        with engine.connect() as conn:
            n = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
        return n > 0, label, f"table: {table} ({n} rows)"
    except Exception as e:
        return False, label, f"table: {table} (error: {e})"


def check_db_operational(engine, label):
    try:
        tables = inspect(engine).get_table_names()
        core = {"vehicles", "sensors", "shipments", "sensor_logs",
                "calibrations", "handovers", "route_events", "compliance_results"}
        found = core.intersection(set(tables))
        return len(found) == len(core), label, f"{len(found)}/{len(core)} core tables"
    except Exception as e:
        return False, label, str(e)


# ==========================================================
# RUN CHECKS
# ==========================================================
def run_checks():
    results = {
        "day1": [],
        "day2": [],
        "day3": [],
    }

    # --- PostgreSQL connection ---
    try:
        engine = create_engine(DB_URL, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
        engine = None

    # ==============================================================
    # DAY 1 CHECKS
    # ==============================================================
    day1 = results["day1"]

    day1.append((db_ok, "PostgreSQL operational database connected",
                 "localhost:5432/coldchainguard"))

    if db_ok:
        for tbl, lbl in [
            ("vehicles",          "Operational table: vehicles"),
            ("sensors",           "Operational table: sensors"),
            ("shipments",         "Operational table: shipments"),
            ("sensor_logs",       "Operational table: sensor_logs"),
            ("calibrations",      "Operational table: calibrations"),
            ("handovers",         "Operational table: handovers"),
            ("route_events",      "Operational table: route_events"),
            ("compliance_results","Operational table: compliance_results"),
        ]:
            day1.append(check_db_table(engine, tbl, lbl))

        for tbl, lbl in [
            ("dim_vehicle",       "Star schema: dim_vehicle"),
            ("dim_product",       "Star schema: dim_product"),
            ("dim_date",          "Star schema: dim_date"),
            ("fact_shipments",    "Star schema: fact_shipments"),
            ("fact_sensor_logs",  "Star schema: fact_sensor_logs"),
            ("fact_route_events", "Star schema: fact_route_events"),
            ("fact_handovers",    "Star schema: fact_handovers"),
        ]:
            day1.append(check_db_table(engine, tbl, lbl))
    else:
        day1.append((False, "PostgreSQL not reachable", "Check .env and DB service"))

    day1.append(check_file(
        os.path.join(ETL_DIR, "master_shipments.csv"),
        "Master analytical dataset: master_shipments.csv"
    ))
    day1.append(check_file(
        os.path.join(ETL_DIR, "etl_summary.csv"),
        "ETL summary: etl_summary.csv"
    ))
    day1.append(check_dir_nonempty(
        STAR_DIR,
        "Star schema CSV exports: data/etl/star_schema/"
    ))
    day1.append(check_file(
        os.path.join(SRC_DIR, "star_schema.py"),
        "ETL source module: src/star_schema.py"
    ))
    day1.append(check_file(
        os.path.join(DOC_DIR, "technical_documentation.md"),
        "Technical documentation: docs/technical_documentation.md"
    ))

    # ==============================================================
    # DAY 2 CHECKS
    # ==============================================================
    day2 = results["day2"]

    day2.append(check_file(
        os.path.join(SRC_DIR, "eda_analysis.py"),
        "EDA source module: src/eda_analysis.py"
    ))
    day2.append(check_file(
        os.path.join(EDA_DIR, "dataset_summary.csv"),
        "Dataset overview: dataset_summary.csv"
    ))
    day2.append(check_file(
        os.path.join(EDA_DIR, "missing_values.csv"),
        "Missing value analysis: missing_values.csv"
    ))
    day2.append(check_file(
        os.path.join(EDA_DIR, "descriptive_statistics.csv"),
        "Descriptive statistics: descriptive_statistics.csv"
    ))
    day2.append(check_file(
        os.path.join(EDA_DIR, "outlier_analysis.csv"),
        "Outlier analysis: outlier_analysis.csv"
    ))
    day2.append(check_file(
        os.path.join(EDA_DIR, "correlation_matrix.csv"),
        "Correlation matrix: correlation_matrix.csv"
    ))

    for plot, label in [
        ("temperature_distribution.png", "Plot: temperature_distribution.png"),
        ("temperature_boxplot.png",       "Plot: temperature_boxplot.png"),
        ("missing_values.png",            "Plot: missing_values.png"),
        ("shipment_status.png",           "Plot: shipment_status.png"),
        ("calibration_status.png",        "Plot: calibration_status.png"),
        ("handover_status.png",           "Plot: handover_status.png"),
        ("route_events.png",              "Plot: route_events.png"),
        ("correlation_heatmap.png",       "Plot: correlation_heatmap.png"),
    ]:
        day2.append(check_file(os.path.join(PLOT_DIR, plot), label))

    day2.append(check_file(
        os.path.join(EDA_DIR, "eda_insights.md"),
        "EDA insights document: eda_insights.md"
    ))

    # ==============================================================
    # DAY 3 CHECKS
    # ==============================================================
    day3 = results["day3"]

    day3.append(check_file(
        os.path.join(SRC_DIR, "rfm_segmentation.py"),
        "RFM source module: src/rfm_segmentation.py"
    ))
    day3.append(check_file(
        os.path.join(SEG_DIR, "rfm_vehicle_segments.csv"),
        "RFM dataset: rfm_vehicle_segments.csv"
    ))
    day3.append(check_file(
        os.path.join(SEG_DIR, "rfm_summary.csv"),
        "RFM summary: rfm_summary.csv"
    ))
    day3.append(check_file(
        os.path.join(SEG_DIR, "rfm_segment_distribution.csv"),
        "Segment distribution: rfm_segment_distribution.csv"
    ))
    day3.append(check_file(
        os.path.join(SEG_DIR, "rfm_segment_distribution.png"),
        "Plot: rfm_segment_distribution.png"
    ))
    day3.append(check_file(
        os.path.join(SEG_DIR, "rfm_scatter.png"),
        "Plot: rfm_scatter.png"
    ))
    day3.append(check_file(
        os.path.join(SEG_DIR, "rfm_scores.png"),
        "Plot: rfm_scores.png"
    ))
    day3.append(check_file(
        os.path.join(SEG_DIR, "rfm_insights.md"),
        "RFM insights document: rfm_insights.md"
    ))

    return results


# ==========================================================
# PRINT REPORT
# ==========================================================
def print_report(results):
    section_labels = {
        "day1": "DAY 1 -- ETL & DATA PREPROCESSING",
        "day2": "DAY 2 -- DESCRIPTIVE STATISTICS & EDA",
        "day3": "DAY 3 -- RFM ASSET SEGMENTATION",
    }

    section_pass = {}

    print("")
    print("=" * 65)
    print("COLDCHAINGUARD -- REVIEW 1 (35%) VALIDATION REPORT")
    print("=" * 65)

    for day_key in ["day1", "day2", "day3"]:
        checks = results[day_key]
        passed = sum(1 for ok, _, _ in checks if ok)
        total  = len(checks)
        day_ok = (passed == total)
        section_pass[day_key] = day_ok

        status = "PASS" if day_ok else f"PARTIAL ({passed}/{total})"
        print(f"\n{section_labels[day_key]}")
        print("-" * 65)

        for ok, label, detail in checks:
            mark = "[PASS]" if ok else "[FAIL]"
            print(f"  {mark}  {label}")
            if not ok:
                print(f"           --> {detail}")

        print(f"\n  Section result: {status}")

    print("")
    print("=" * 65)
    all_pass = all(section_pass.values())

    if all_pass:
        print("  DAY 1 -- ETL & PREPROCESSING         PASS")
        print("  DAY 2 -- EDA                          PASS")
        print("  DAY 3 -- RFM SEGMENTATION             PASS")
        print("")
        print("  FIRST 35% REQUIREMENT                 PASS")
    else:
        for day_key, ok in section_pass.items():
            label = section_labels[day_key].split("--")[1].strip()
            status = "PASS" if ok else "INCOMPLETE"
            print(f"  {label:<38} {status}")
        print("")
        print("  FIRST 35% REQUIREMENT                 INCOMPLETE")
        print("  Run missing scripts and re-validate.")

    print("=" * 65)
    return all_pass


# ==========================================================
# MAIN
# ==========================================================
def main():
    results = run_checks()
    all_pass = print_report(results)
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
