"""
src/final_validation.py
ColdChainGuard - Comprehensive Final Validation Script

Dynamically verifies ALL project components without hard-coded row counts.

Usage:
  python src/final_validation.py
  python src/final_validation.py --skip-db   (skip PostgreSQL checks)
"""

import os
import sys
import argparse

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

SKIP_DB = "--skip-db" in sys.argv

results = {}   # section_name -> (pass:bool, detail:str)


def chk(section, passed, detail=""):
    results[section] = (bool(passed), detail)
    mark = "[PASS]" if passed else "[FAIL]"
    label = f"{section:<20}"
    print(f"  {mark}  {label}  {detail}")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION CHECKS
# ─────────────────────────────────────────────────────────────────────────────

def check_environment():
    required = ["dash", "plotly", "pandas", "numpy", "sqlalchemy",
                "reportlab", "matplotlib", "sklearn", "joblib"]
    missing = []
    versions = []
    for pkg in required:
        try:
            mod = __import__(pkg)
            v = getattr(mod, "__version__", "ok")
            versions.append(f"{pkg}={v}")
        except ImportError:
            missing.append(pkg)
    # psycopg separately
    try:
        import psycopg
        versions.append(f"psycopg={psycopg.__version__}")
    except ImportError:
        missing.append("psycopg")

    if missing:
        chk("Environment", False, f"Missing packages: {missing}")
    else:
        chk("Environment", True, f"{len(required)+1} packages OK")


def check_input_validation():
    raw_dir = os.path.join(PROJECT_ROOT, "data", "raw")
    required_files = ["vehicles.csv", "sensors.csv", "product_batches.csv",
                      "shipments.csv", "sensor_logs.csv", "calibrations.csv",
                      "handovers.csv", "route_events.csv"]
    missing = [f for f in required_files if not os.path.exists(os.path.join(raw_dir, f))]
    if missing:
        chk("Input validation", False, f"Missing files: {missing}")
        return
    # check non-empty
    import pandas as pd
    empty = []
    counts = {}
    for f in required_files:
        try:
            df = pd.read_csv(os.path.join(raw_dir, f))
            if len(df) == 0:
                empty.append(f)
            counts[f.replace(".csv","")] = len(df)
        except Exception as e:
            empty.append(f"{f}(err:{e})")
    if empty:
        chk("Input validation", False, f"Empty files: {empty}")
    else:
        summary = f"{counts.get('shipments',0)} shipments, {counts.get('vehicles',0)} vehicles"
        chk("Input validation", True, summary)


def check_etl():
    import pandas as pd
    master = os.path.join(PROJECT_ROOT, "data", "etl", "master_shipments.csv")
    star_dir = os.path.join(PROJECT_ROOT, "data", "etl", "star_schema")
    issues = []
    if not os.path.exists(master):
        issues.append("master_shipments.csv missing")
    else:
        n = len(pd.read_csv(master))
        if n == 0:
            issues.append("master_shipments.csv is empty")
    if not os.path.isdir(star_dir):
        issues.append("star_schema/ directory missing")
    else:
        star_files = [f for f in os.listdir(star_dir) if f.endswith(".csv")]
        if len(star_files) < 7:
            issues.append(f"star_schema/ has only {len(star_files)} CSVs (need 7)")
    if issues:
        chk("ETL", False, "; ".join(issues))
    else:
        n = len(pd.read_csv(master))
        chk("ETL", True, f"master_shipments={n} rows, star_schema={len(star_files)} tables")


def check_database():
    if SKIP_DB:
        chk("Database", True, "SKIPPED (--skip-db)")
        return
    try:
        from sqlalchemy import create_engine, text, inspect
        engine = create_engine(
            "postgresql+psycopg://postgres:1322@localhost:5432/coldchainguard",
            pool_pre_ping=True
        )
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        ins = inspect(engine)
        tables = set(ins.get_table_names())

        operational = ["vehicles","sensors","product_batches","shipments",
                       "sensor_logs","calibrations","handovers","route_events",
                       "compliance_results"]
        analytical  = ["dim_vehicle","dim_product","dim_date",
                       "fact_shipments","fact_sensor_logs",
                       "fact_route_events","fact_handovers"]
        all_required = operational + analytical

        missing_tables = [t for t in all_required if t not in tables]
        if missing_tables:
            chk("Database", False, f"Missing tables: {missing_tables}")
            return

        with engine.connect() as conn:
            counts = {}
            for t in all_required:
                counts[t] = conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
        empty = [t for t, n in counts.items() if n == 0]
        if empty:
            chk("Database", False, f"Empty tables: {empty}")
        else:
            shp = counts.get("shipments", 0)
            sl  = counts.get("sensor_logs", 0)
            chk("Database", True, f"{len(all_required)} tables OK | shipments={shp}, logs={sl}")
    except Exception as e:
        chk("Database", False, str(e)[:120])


def check_star_schema():
    if SKIP_DB:
        import pandas as pd
        star_dir = os.path.join(PROJECT_ROOT, "data", "etl", "star_schema")
        required = ["dim_vehicle","dim_product","dim_date",
                    "fact_shipments","fact_sensor_logs","fact_route_events","fact_handovers"]
        missing = [f"{r}.csv" for r in required
                   if not os.path.exists(os.path.join(star_dir, f"{r}.csv"))]
        if missing:
            chk("Star schema", False, f"Missing CSVs: {missing}")
        else:
            chk("Star schema", True, "7 star-schema CSVs present (CSV mode)")
        return
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(
            "postgresql+psycopg://postgres:1322@localhost:5432/coldchainguard",
            pool_pre_ping=True
        )
        analytical = ["dim_vehicle","dim_product","dim_date",
                      "fact_shipments","fact_sensor_logs","fact_route_events","fact_handovers"]
        with engine.connect() as conn:
            counts = {t: conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
                      for t in analytical}
        empty = [t for t, n in counts.items() if n == 0]
        if empty:
            chk("Star schema", False, f"Empty analytical tables: {empty}")
        else:
            total = sum(counts.values())
            chk("Star schema", True, f"7 tables, {total:,} total analytical rows")
    except Exception as e:
        chk("Star schema", False, str(e)[:100])


def check_eda():
    eda_dir = os.path.join(PROJECT_ROOT, "data", "eda")
    plot_dir = os.path.join(eda_dir, "plots")
    issues = []
    if not os.path.isdir(plot_dir):
        issues.append("data/eda/plots/ directory missing")
    else:
        plots = [f for f in os.listdir(plot_dir) if f.endswith(".png")]
        if len(plots) < 8:
            issues.append(f"Only {len(plots)} plots (need >=8)")
    csvs = [f for f in os.listdir(eda_dir) if f.endswith(".csv")] if os.path.isdir(eda_dir) else []
    if len(csvs) < 4:
        issues.append(f"Only {len(csvs)} CSVs in data/eda/ (need >=4)")
    insights = os.path.join(eda_dir, "eda_insights.md")
    if not os.path.exists(insights):
        issues.append("eda_insights.md missing")
    if issues:
        chk("EDA", False, "; ".join(issues))
    else:
        chk("EDA", True, f"{len(plots)} plots, {len(csvs)} CSVs, insights.md present")


def check_rfm():
    import pandas as pd
    seg_dir = os.path.join(PROJECT_ROOT, "data", "segmentation")
    seg_file = os.path.join(seg_dir, "rfm_vehicle_segments.csv")
    dist_file = os.path.join(seg_dir, "rfm_segment_distribution.csv")
    if not os.path.exists(seg_file):
        chk("RFM", False, "rfm_vehicle_segments.csv missing")
        return
    df = pd.read_csv(seg_file)
    if len(df) == 0:
        chk("RFM", False, "rfm_vehicle_segments.csv is empty")
        return
    segments = df.get("RFM_segment", df.iloc[:, -1]).nunique() if not df.empty else 0
    chk("RFM", True,
        f"{len(df)} vehicles segmented, {segments} segments, dist_file={'present' if os.path.exists(dist_file) else 'missing'}")


def check_compliance():
    import pandas as pd
    comp_csv = os.path.join(PROJECT_ROOT, "data", "compliance_results.csv")
    if not os.path.exists(comp_csv):
        if SKIP_DB:
            chk("Compliance", False, "compliance_results.csv missing (--skip-db mode)")
            return
        # check DB
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(
                "postgresql+psycopg://postgres:1322@localhost:5432/coldchainguard",
                pool_pre_ping=True
            )
            with engine.connect() as conn:
                n = conn.execute(text("SELECT COUNT(*) FROM compliance_results")).scalar()
            if n == 0:
                chk("Compliance", False, "compliance_results table is empty")
            else:
                chk("Compliance", True, f"DB: {n} compliance results")
        except Exception as e:
            chk("Compliance", False, str(e)[:80])
        return
    df = pd.read_csv(comp_csv)
    if len(df) == 0:
        chk("Compliance", False, "compliance_results.csv is empty")
        return
    vc = df.get("overall_compliance", pd.Series()).value_counts().to_dict()
    chk("Compliance", True, f"{len(df)} results | {vc}")


def check_evidence():
    ev_csv  = os.path.join(PROJECT_ROOT, "data", "evidence", "compliance_evidence_pack.csv")
    ev_json = os.path.join(PROJECT_ROOT, "data", "evidence", "compliance_evidence_pack.json")
    if os.path.exists(ev_csv):
        import pandas as pd
        df = pd.read_csv(ev_csv)
        chk("Evidence", len(df) > 0, f"evidence_pack.csv: {len(df)} records")
    elif os.path.exists(ev_json):
        size = os.path.getsize(ev_json)
        chk("Evidence", size > 1000, f"evidence_pack.json: {size:,} bytes")
    else:
        chk("Evidence", False, "No evidence pack found (csv or json)")


def check_failure_modes():
    import pandas as pd
    f = os.path.join(PROJECT_ROOT, "data", "experiments", "failure_mode_results.csv")
    if not os.path.exists(f):
        chk("Failure modes", False, "failure_mode_results.csv missing")
        return
    df = pd.read_csv(f)
    if len(df) < 3:
        chk("Failure modes", False, f"Only {len(df)} failure cases (need >=3)")
        return
    passed = (df.get("result", df.get("status", pd.Series())) == "PASS").sum() if not df.empty else 0
    chk("Failure modes", True, f"{len(df)} cases, {passed} PASS")


def check_store_forward():
    f = os.path.join(PROJECT_ROOT, "data", "experiments", "store_and_forward_metrics.csv")
    if not os.path.exists(f):
        chk("Store-forward", False, "store_and_forward_metrics.csv missing")
        return
    import pandas as pd
    df = pd.read_csv(f)
    rate = float(df.get("recovery_rate", df.get("recovery_rate_pct", pd.Series([0]))).iloc[0])
    chk("Store-forward", True, f"recovery_rate={rate}")


def check_threshold_tuning():
    f = os.path.join(PROJECT_ROOT, "data", "experiments", "threshold_tuning_results.csv")
    if not os.path.exists(f):
        chk("Threshold tuning", False, "threshold_tuning_results.csv missing")
        return
    import pandas as pd
    df = pd.read_csv(f)
    chk("Threshold tuning", True, f"{len(df)} threshold configurations")


def check_dispatcher():
    f = os.path.join(PROJECT_ROOT, "data", "experiments", "dispatcher_override_history.csv")
    if not os.path.exists(f):
        chk("Dispatcher", False, "dispatcher_override_history.csv missing")
        return
    import pandas as pd
    df = pd.read_csv(f)
    chk("Dispatcher", True, f"{len(df)} override history records")


def check_optimisation():
    opt_dir = os.path.join(PROJECT_ROOT, "data", "optimization")
    sc_file  = os.path.join(opt_dir, "strategy_comparison.csv")
    radar    = os.path.join(opt_dir, "strategy_tradeoff_radar.png")
    issues   = []
    if not os.path.exists(sc_file):
        issues.append("strategy_comparison.csv missing")
    if not os.path.exists(radar):
        issues.append("strategy_tradeoff_radar.png missing")
    if issues:
        chk("Optimisation", False, "; ".join(issues))
        return
    import pandas as pd
    df = pd.read_csv(sc_file)
    chk("Optimisation", True, f"{len(df)} strategies, radar chart present")


def check_ml():
    import pandas as pd
    pred_dir = os.path.join(PROJECT_ROOT, "data", "predictions")
    comp_f   = os.path.join(pred_dir, "model_comparison.csv")
    pred_f   = os.path.join(pred_dir, "predictions.csv")
    issues   = []
    if not os.path.exists(comp_f):
        issues.append("model_comparison.csv missing")
    if not os.path.exists(pred_f):
        issues.append("predictions.csv missing")
    else:
        n = len(pd.read_csv(pred_f))
        if n == 0:
            issues.append("predictions.csv is empty")
    if issues:
        chk("ML", False, "; ".join(issues))
        return
    comp = pd.read_csv(comp_f)
    best_auc = float(comp["roc_auc"].max()) if "roc_auc" in comp.columns else 0
    n_preds  = len(pd.read_csv(pred_f))
    chk("ML", True, f"{len(comp)} models, best_auc={best_auc:.3f}, {n_preds} predictions")


def check_reports():
    import pandas as pd
    rpt_dir = os.path.join(PROJECT_ROOT, "data", "reports")
    if not os.path.isdir(rpt_dir):
        chk("Reports", False, "data/reports/ directory missing")
        return
    pdfs = [f for f in os.listdir(rpt_dir) if f.endswith(".pdf")]
    if len(pdfs) == 0:
        chk("Reports", False, "No PDF reports found")
        return
    # Dynamic check: PDFs should cover all shipments in compliance_results
    comp_csv = os.path.join(PROJECT_ROOT, "data", "compliance_results.csv")
    if os.path.exists(comp_csv):
        comp_df = pd.read_csv(comp_csv)
        n_shipments = len(comp_df)
        ok = len(pdfs) >= n_shipments
        chk("Reports", ok,
            f"{len(pdfs)} PDFs vs {n_shipments} shipments in compliance_results "
            f"({'OK' if ok else 'INCOMPLETE'})")
    else:
        chk("Reports", True, f"{len(pdfs)} PDF audit reports present")


def check_dashboard():
    dashboard = os.path.join(PROJECT_ROOT, "src", "dashboard.py")
    if not os.path.exists(dashboard):
        chk("Dashboard", False, "src/dashboard.py missing")
        return
    try:
        import dash
        import plotly
        chk("Dashboard", True,
            f"dashboard.py present | dash={dash.__version__}, plotly={plotly.__version__}")
    except ImportError as e:
        chk("Dashboard", False, f"Import error: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("\nCOLDCHAINGUARD FINAL VALIDATION")
    print("=" * 50)
    if SKIP_DB:
        print("  Mode: CSV-only (--skip-db)\n")

    check_environment()
    check_input_validation()
    check_etl()
    check_database()
    check_star_schema()
    check_eda()
    check_rfm()
    check_compliance()
    check_evidence()
    check_failure_modes()
    check_store_forward()
    check_threshold_tuning()
    check_dispatcher()
    check_optimisation()
    check_ml()
    check_reports()
    check_dashboard()

    # ── Summary ──
    total  = len(results)
    passed = sum(1 for v in results.values() if v[0])
    failed = [k for k, v in results.items() if not v[0]]

    print("\n" + "=" * 50)
    print(f"TOTAL: {passed}/{total} PASS")

    if failed:
        print(f"FAILED: {', '.join(failed)}")
        print("FINAL STATUS: INCOMPLETE")
        sys.exit(1)
    else:
        print("FINAL STATUS: COMPLETE")
        sys.exit(0)


if __name__ == "__main__":
    main()
