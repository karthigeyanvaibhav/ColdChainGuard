"""
run_all.py - ColdChainGuard Single-Command Pipeline Orchestrator

Usage:
    python run_all.py            # Full pipeline (requires PostgreSQL)
    python run_all.py --skip-db  # CSV-only mode (skips DB steps)
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

SKIP_DB = "--skip-db" in sys.argv


def banner(text):
    width = 70
    print("\n" + "=" * width)
    print(f"  {text}")
    print("=" * width)


def step(number, description):
    print(f"\n{'-' * 70}")
    print(f"  STEP {number}: {description}")
    print(f"{'-' * 70}")


def run(script_name, description, skip=False):
    """Run a Python script in the project src directory."""
    if skip:
        print(f"  [SKIPPED] {description}")
        return True

    script_path = os.path.join(SRC, script_name)
    if not os.path.exists(script_path):
        # Try project root
        script_path = os.path.join(PROJECT_ROOT, script_name)

    if not os.path.exists(script_path):
        print(f"  [MISSING] {script_path} — skipping")
        return False

    start = time.perf_counter()
    result = subprocess.run(
        [sys.executable, script_path],
        cwd=PROJECT_ROOT,
    )
    elapsed = time.perf_counter() - start

    if result.returncode == 0:
        print(f"  [OK] Completed in {elapsed:.1f}s")
        return True
    else:
        print(f"  [ERROR] Exit code {result.returncode}")
        print(f"  Script: {script_path}")
        return False


# ==========================================================
# PIPELINE
# ==========================================================

def main():

    banner("COLDCHAINGUARD — AUTOMATED COMPLIANCE PIPELINE")

    if SKIP_DB:
        print("\n  Mode: CSV-only (--skip-db flag detected)")
        print("  DB steps will be skipped.")
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
    # STEP 2: Load data to PostgreSQL
    # ──────────────────────────────────────────────────────
    step(2, "Load data to PostgreSQL")
    ok = run(
        os.path.join("..", "database", "load_data.py"),
        "Database load",
        skip=SKIP_DB,
    )
    results["load_data"] = ok or SKIP_DB

    # ──────────────────────────────────────────────────────
    # STEP 3: Process sensor logs
    # ──────────────────────────────────────────────────────
    step(3, "Process sensor logs (handle missing/noisy observations)")
    ok = run("sensor_processor.py", "Sensor processing")
    results["sensor_processor"] = ok

    # ──────────────────────────────────────────────────────
    # STEP 4: Run compliance engine
    # ──────────────────────────────────────────────────────
    step(4, "Run compliance engine")
    ok = run("compliance_engine.py", "Compliance engine")
    results["compliance_engine"] = ok

    # ──────────────────────────────────────────────────────
    # STEP 5: Build evidence pack
    # ──────────────────────────────────────────────────────
    step(5, "Build compliance evidence pack")
    ok = run("evidence_pack.py", "Evidence pack", skip=SKIP_DB)
    results["evidence_pack"] = ok or SKIP_DB

    # ──────────────────────────────────────────────────────
    # STEP 6: Dispatcher override demo
    # ──────────────────────────────────────────────────────
    step(6, "Run dispatcher override demonstration")
    ok = run("dispatcher_override.py", "Dispatcher override")
    results["dispatcher_override"] = ok

    # ──────────────────────────────────────────────────────
    # STEP 7: Store-and-forward demonstration
    # ──────────────────────────────────────────────────────
    step(7, "Demonstrate store-and-forward / fallback behaviour")
    ok = run("store_and_forward.py", "Store-and-forward")
    results["store_and_forward"] = ok

    # ──────────────────────────────────────────────────────
    # STEP 8: Baseline experiment
    # ──────────────────────────────────────────────────────
    step(8, "Run baseline experiment (manual vs automated comparison)")
    ok = run("baseline_experiment.py", "Baseline experiment")
    results["baseline_experiment"] = ok

    # ──────────────────────────────────────────────────────
    # STEP 9: Threshold tuning
    # ──────────────────────────────────────────────────────
    step(9, "Tune alert thresholds")
    ok = run("threshold_tuning.py", "Threshold tuning")
    results["threshold_tuning"] = ok

    # ──────────────────────────────────────────────────────
    # STEP 10: Trade-off experiment
    # ──────────────────────────────────────────────────────
    step(10, "Run cost/time/emissions/reliability trade-off experiment")
    ok = run("tradeoff_experiment.py", "Trade-off experiment")
    results["tradeoff_experiment"] = ok

    # ──────────────────────────────────────────────────────
    # STEP 11: Failure mode tests
    # ──────────────────────────────────────────────────────
    step(11, "Run edge/failure case tests")
    ok = run("failure_tests.py", "Failure tests")
    results["failure_tests"] = ok

    # ──────────────────────────────────────────────────────
    # STEP 12: Generate experiment HTML report
    # ──────────────────────────────────────────────────────
    step(12, "Generate experiment HTML report")
    ok = run("experiment_notebook.py", "Experiment report")
    results["experiment_notebook"] = ok

    # ----------------------------------------------------------
    # STEP 13: Generate audit PDF reports
    # ----------------------------------------------------------
    step(13, "Generate audit PDF reports (sample: first 10 shipments)")
    ok = run("audit_report.py", "Audit PDF reports")
    results["audit_report"] = ok

    # ----------------------------------------------------------
    # SUMMARY
    # ----------------------------------------------------------
    banner("PIPELINE SUMMARY")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for step_name, ok in results.items():
        status = "[OK]  " if ok else "[FAIL]"
        print(f"  {status}  {step_name}")

    print(f"\n  {passed}/{total} steps completed successfully.")

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
        print("\n  Some steps failed - check output above for details.")
        print("  To skip DB-dependent steps: python run_all.py --skip-db")


if __name__ == "__main__":
    main()
