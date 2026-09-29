"""
run_all.py - ColdChainGuard Single-Command Pipeline Orchestrator

Usage:
    python run_all.py                 # Full pipeline (requires PostgreSQL)
    python run_all.py --skip-db       # CSV-only mode (skips DB steps)
    python run_all.py --fresh         # Full reset + reload (WARNING: truncates DB)

The pipeline runs in dependency order:
  1.  Data generation
  2.  PostgreSQL load
  3.  Sensor processing
  4.  Compliance engine
  5.  Evidence pack
  6.  Dispatcher override demo
  7.  Store-and-forward demo
  8.  Baseline experiment
  9.  Threshold tuning
  10. Trade-off experiment
  11. Failure mode tests
  12. Experiment HTML report
  13. Audit PDF reports (all shipments)
  14. ETL / Star schema
  15. EDA analysis
  16. RFM segmentation
  17. Predictive ML
  18. Route optimisation
  19. System evaluation
  20. Final validation
"""

import sys
import time
import subprocess
import os

# ==========================================================
# CONFIGURATION
# ==========================================================

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(PROJECT_ROOT, "src")
DB  = os.path.join(PROJECT_ROOT, "database")
SCR = os.path.join(PROJECT_ROOT, "scripts")

SKIP_DB = "--skip-db" in sys.argv
FRESH   = "--fresh"   in sys.argv

_start_total = time.perf_counter()


def banner(text):
    width = 70
    print("\n" + "=" * width)
    print(f"  {text}")
    print("=" * width)


def step(number, description):
    print(f"\n{'-' * 70}")
    print(f"  STEP {number}: {description}")
    print(f"{'-' * 70}")


def run(script_path_rel, description, skip=False, extra_args=None):
    """Run a Python script by relative path from PROJECT_ROOT."""
    if skip:
        print(f"  [SKIPPED] {description}")
        return True

    # Resolve: try src/, database/, scripts/, root
    candidates = [
        os.path.join(SRC, script_path_rel),
        os.path.join(DB,  script_path_rel),
        os.path.join(SCR, script_path_rel),
        os.path.join(PROJECT_ROOT, script_path_rel),
    ]
    script_path = None
    for c in candidates:
        if os.path.exists(c):
            script_path = c
            break

    if script_path is None:
        print(f"  [MISSING] {script_path_rel} — skipping")
        return False

    cmd = [sys.executable, script_path]
    if extra_args:
        cmd.extend(extra_args)

    t0 = time.perf_counter()
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    elapsed = time.perf_counter() - t0

    if result.returncode == 0:
        print(f"  [OK] Completed in {elapsed:.1f}s")
        return True
    else:
        print(f"  [ERROR] Exit code {result.returncode} — {script_path_rel}")
        return False


# ==========================================================
# PIPELINE
# ==========================================================

def main():

    banner("COLDCHAINGUARD — AUTOMATED COMPLIANCE PIPELINE")

    if FRESH and not SKIP_DB:
        print("\n  Mode: FRESH (database will be reset before loading)")
        print("  WARNING: All existing data will be truncated.")
    elif SKIP_DB:
        print("\n  Mode: CSV-only (--skip-db flag detected)")
    else:
        print("\n  Mode: Full pipeline (PostgreSQL required)")
    print("  Use --skip-db to skip database steps.")

    results = {}

    # ──────────────────────────────────────────────────────
    # STEP 1: Generate synthetic data
    # ──────────────────────────────────────────────────────
    step(1, "Generate synthetic data")
    ok = run("data_generator.py", "Data generation")
    results["data_generator"] = ok

    # ──────────────────────────────────────────────────────
    # STEP 1b: Validate input schema
    # ──────────────────────────────────────────────────────
    step("1b", "Validate input dataset schema")
    ok = run("schema_validator.py", "Schema validation")
    results["schema_validator"] = ok

    # ──────────────────────────────────────────────────────
    # STEP 2: (Optional) Reset database for fresh load
    # ──────────────────────────────────────────────────────
    if FRESH and not SKIP_DB:
        step(2, "Reset database (--fresh flag)")
        ok = run("reset_database.py", "Database reset", extra_args=["--confirm"])
        results["reset_database"] = ok

    # ──────────────────────────────────────────────────────
    # STEP 2/3: Load data to PostgreSQL
    # ──────────────────────────────────────────────────────
    step(3, "Load data to PostgreSQL")
    ok = run(
        "load_data.py",
        "Database load",
        skip=SKIP_DB,
    )
    results["load_data"] = ok or SKIP_DB

    # ──────────────────────────────────────────────────────
    # STEP 4: Process sensor logs
    # ──────────────────────────────────────────────────────
    step(4, "Process sensor logs (handle missing/noisy observations)")
    ok = run("sensor_processor.py", "Sensor processing")
    results["sensor_processor"] = ok

    # ──────────────────────────────────────────────────────
    # STEP 5: Run compliance engine
    # ──────────────────────────────────────────────────────
    step(5, "Run compliance engine")
    ok = run("compliance_engine.py", "Compliance engine")
    results["compliance_engine"] = ok

    # ──────────────────────────────────────────────────────
    # STEP 6: Build evidence pack
    # ──────────────────────────────────────────────────────
    step(6, "Build compliance evidence pack")
    ok = run("evidence_pack.py", "Evidence pack", skip=SKIP_DB)
    results["evidence_pack"] = ok or SKIP_DB

    # ──────────────────────────────────────────────────────
    # STEP 7: Dispatcher override demo
    # ──────────────────────────────────────────────────────
    step(7, "Run dispatcher override demonstration")
    ok = run("dispatcher_override.py", "Dispatcher override")
    results["dispatcher_override"] = ok

    # ──────────────────────────────────────────────────────
    # STEP 8: Store-and-forward demonstration
    # ──────────────────────────────────────────────────────
    step(8, "Demonstrate store-and-forward / fallback behaviour")
    ok = run("store_and_forward.py", "Store-and-forward")
    results["store_and_forward"] = ok

    # ──────────────────────────────────────────────────────
    # STEP 9: Baseline experiment
    # ──────────────────────────────────────────────────────
    step(9, "Run baseline experiment (manual vs automated comparison)")
    ok = run("baseline_experiment.py", "Baseline experiment")
    results["baseline_experiment"] = ok

    # ──────────────────────────────────────────────────────
    # STEP 10: Threshold tuning
    # ──────────────────────────────────────────────────────
    step(10, "Tune alert thresholds")
    ok = run("threshold_tuning.py", "Threshold tuning")
    results["threshold_tuning"] = ok

    # ──────────────────────────────────────────────────────
    # STEP 11: Trade-off experiment
    # ──────────────────────────────────────────────────────
    step(11, "Run cost/time/emissions/reliability trade-off experiment")
    ok = run("tradeoff_experiment.py", "Trade-off experiment")
    results["tradeoff_experiment"] = ok

    # ──────────────────────────────────────────────────────
    # STEP 12: Failure mode tests
    # ──────────────────────────────────────────────────────
    step(12, "Run edge/failure case tests")
    ok = run("failure_tests.py", "Failure tests")
    results["failure_tests"] = ok

    # ──────────────────────────────────────────────────────
    # STEP 13: Generate experiment HTML report
    # ──────────────────────────────────────────────────────
    step(13, "Generate experiment HTML report")
    ok = run("experiment_notebook.py", "Experiment report")
    results["experiment_notebook"] = ok

    # ──────────────────────────────────────────────────────
    # STEP 14: Generate audit PDF reports (all shipments)
    # ──────────────────────────────────────────────────────
    step(14, "Generate audit PDF reports (all shipments, dynamically)")
    ok = run("audit_report.py", "Audit PDF reports")
    results["audit_report"] = ok

    # ──────────────────────────────────────────────────────
    # STEP 15: ETL / Star Schema
    # ──────────────────────────────────────────────────────
    step(15, "Build analytical star schema (ETL)")
    ok = run("star_schema.py", "Star schema ETL", skip=SKIP_DB)
    results["star_schema"] = ok or SKIP_DB

    # ──────────────────────────────────────────────────────
    # STEP 16: EDA
    # ──────────────────────────────────────────────────────
    step(16, "Run exploratory data analysis")
    ok = run("eda_analysis.py", "EDA analysis")
    results["eda_analysis"] = ok

    # ──────────────────────────────────────────────────────
    # STEP 17: RFM Segmentation
    # ──────────────────────────────────────────────────────
    step(17, "Run vehicle RFM segmentation")
    ok = run("rfm_segmentation.py", "RFM segmentation")
    results["rfm_segmentation"] = ok

    # ──────────────────────────────────────────────────────
    # STEP 18: Predictive ML
    # ──────────────────────────────────────────────────────
    step(18, "Train predictive compliance models")
    ok = run("predictive_model.py", "Predictive ML")
    results["predictive_model"] = ok

    # ──────────────────────────────────────────────────────
    # STEP 19: Route Optimisation
    # ──────────────────────────────────────────────────────
    step(19, "Run multi-objective route optimisation")
    ok = run("route_optimizer.py", "Route optimisation")
    results["route_optimizer"] = ok

    # ──────────────────────────────────────────────────────
    # STEP 20: System Evaluation
    # ──────────────────────────────────────────────────────
    step(20, "Run system evaluation")
    ok = run("system_evaluation.py", "System evaluation")
    results["system_evaluation"] = ok

    # ──────────────────────────────────────────────────────
    # STEP 22: Forecasting (Day 8 analogue)
    # ──────────────────────────────────────────────────────
    step(22, "Compliance-rate and excursion forecasting (Day 8 analogue)")
    ok = run("forecasting.py", "Forecasting")
    results["forecasting"] = ok

    # ──────────────────────────────────────────────────────
    # STEP 23: Cohort & Retention (Day 9 analogue)
    # ──────────────────────────────────────────────────────
    step(23, "Vehicle cohort and sensor survival analysis (Day 9 analogue)")
    ok = run("cohort_retention.py", "Cohort & Retention")
    results["cohort_retention"] = ok

    # ──────────────────────────────────────────────────────
    # STEP 24: Final Validation
    # ──────────────────────────────────────────────────────
    step(24, "Run final validation (all 17 checks)")
    ok = run("final_validation.py", "Final validation",
             extra_args=["--skip-db"] if SKIP_DB else [])
    results["final_validation"] = ok

    # ──────────────────────────────────────────────────────
    # SUMMARY
    # ──────────────────────────────────────────────────────
    total_elapsed = time.perf_counter() - _start_total
    banner("PIPELINE SUMMARY")

    passed = sum(1 for v in results.values() if v)
    total  = len(results)

    for step_name, ok in results.items():
        status = "[OK]  " if ok else "[FAIL]"
        print(f"  {status}  {step_name}")

    print(f"\n  {passed}/{total} steps completed successfully.")
    print(f"  Total elapsed: {total_elapsed:.1f}s")

    if passed == total:
        print("\n  All steps passed!")
        print("\n  ------------------------------------------")
        print("  Next: open the dashboard")
        print("  Command:  python src/dashboard.py")
        print("  URL:      http://127.0.0.1:8050/")
        print("\n  Or view the experiment report:")
        print("  File:     data/experiments/experiment_report.html")
        print("  ------------------------------------------")
    else:
        failed = [k for k, v in results.items() if not v]
        print(f"\n  Failed steps: {failed}")
        print("  To skip DB-dependent steps: python run_all.py --skip-db")


if __name__ == "__main__":
    main()
