import os
import time
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


# ==========================================================
# PROJECT PATHS
# ==========================================================

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

EVIDENCE_FILE = os.path.join(
    PROJECT_ROOT,
    "data",
    "evidence",
    "compliance_evidence_pack.csv"
)

REPORT_DIR = os.path.join(
    PROJECT_ROOT,
    "data",
    "reports"
)

RESULT_DIR = os.path.join(
    PROJECT_ROOT,
    "data",
    "experiments"
)

os.makedirs(
    RESULT_DIR,
    exist_ok=True
)


# ==========================================================
# EXPERIMENT PARAMETERS
# ==========================================================

# Estimated manual effort per shipment.
# This represents opening multiple records,
# checking sensor data, calibration, custody,
# route events and preparing the report.

MANUAL_MINUTES_PER_REPORT = 8


# Target reduction in manual effort.
TARGET_REDUCTION_PERCENT = 80


# ==========================================================
# LOAD DATA
# ==========================================================

def load_evidence():

    if not os.path.exists(EVIDENCE_FILE):

        raise FileNotFoundError(
            f"Evidence pack not found:\n{EVIDENCE_FILE}"
        )

    df = pd.read_csv(
        EVIDENCE_FILE
    )

    print(
        f"Evidence records loaded: {len(df)}"
    )

    return df


# ==========================================================
# CHECK AUTOMATED REPORTS
# ==========================================================

def check_generated_reports(df):

    generated = 0
    missing = []

    for shipment_id in df["shipment_id"]:

        filename = (
            f"{shipment_id}_audit_report.pdf"
        )

        filepath = os.path.join(
            REPORT_DIR,
            filename
        )

        if os.path.exists(filepath):

            generated += 1

        else:

            missing.append(
                shipment_id
            )

    return generated, missing


# ==========================================================
# EVIDENCE COMPLETENESS
# ==========================================================

def calculate_completeness(df):

    if "evidence_completeness_percent" not in df.columns:

        return 0

    return df[
        "evidence_completeness_percent"
    ].mean()


# ==========================================================
# BASELINE CALCULATION
# ==========================================================

def calculate_baseline(df):

    shipment_count = len(df)

    total_manual_minutes = (
        shipment_count *
        MANUAL_MINUTES_PER_REPORT
    )

    total_manual_hours = (
        total_manual_minutes / 60
    )

    return {
        "shipments": shipment_count,
        "minutes_per_report": MANUAL_MINUTES_PER_REPORT,
        "total_minutes": total_manual_minutes,
        "total_hours": total_manual_hours
    }


# ==========================================================
# AUTOMATED PROCESSING
# ==========================================================

def measure_automation(df):

    start_time = time.perf_counter()

    generated_reports, missing_reports = (
        check_generated_reports(df)
    )

    end_time = time.perf_counter()

    verification_time = (
        end_time - start_time
    )

    return {
        "reports_generated": generated_reports,
        "missing_reports": len(missing_reports),
        "verification_time_seconds": verification_time
    }


# ==========================================================
# EFFORT COMPARISON
# ==========================================================

def calculate_comparison(
    baseline,
    automation
):

    manual_seconds = (
        baseline["total_minutes"] * 60
    )

    automated_seconds = (
        automation["verification_time_seconds"]
    )

    time_saved_seconds = (
        manual_seconds -
        automated_seconds
    )

    reduction_percent = (
        time_saved_seconds /
        manual_seconds
    ) * 100

    return {
        "manual_seconds": manual_seconds,
        "automated_seconds": automated_seconds,
        "time_saved_seconds": time_saved_seconds,
        "reduction_percent": reduction_percent
    }


# ==========================================================
# SAVE RESULTS
# ==========================================================

def save_results(results):

    output_file = os.path.join(
        RESULT_DIR,
        "baseline_results.csv"
    )

    results.to_csv(
        output_file,
        index=False
    )

    print(
        f"\nResults saved to:\n{output_file}"
    )


# ==========================================================
# CREATE CHART
# ==========================================================

def create_time_comparison_chart(
    comparison
):

    methods = [
        "Manual",
        "ColdChainGuard"
    ]

    times = [
        comparison["manual_seconds"],
        comparison["automated_seconds"]
    ]

    plt.figure(
        figsize=(8, 5)
    )

    sns.barplot(
        x=methods,
        y=times
    )

    plt.title(
        "Compliance Report Processing Time"
    )

    plt.ylabel(
        "Time (seconds)"
    )

    plt.xlabel(
        "Method"
    )

    plt.tight_layout()

    output_file = os.path.join(
        RESULT_DIR,
        "processing_time_comparison.png"
    )

    plt.savefig(
        output_file,
        dpi=300
    )

    plt.close()

    print(
        f"Chart saved:\n{output_file}"
    )


# ==========================================================
# MAIN EXPERIMENT
# ==========================================================

def main():

    print("=" * 70)
    print(
        "COLDCHAINGUARD - BASELINE EXPERIMENT"
    )
    print("=" * 70)

    # ------------------------------------------------------
    # Load evidence
    # ------------------------------------------------------

    df = load_evidence()

    # ------------------------------------------------------
    # Baseline
    # ------------------------------------------------------

    baseline = calculate_baseline(
        df
    )

    # ------------------------------------------------------
    # Automation
    # ------------------------------------------------------

    automation = measure_automation(
        df
    )

    # ------------------------------------------------------
    # Evidence completeness
    # ------------------------------------------------------

    completeness = calculate_completeness(
        df
    )

    # ------------------------------------------------------
    # Comparison
    # ------------------------------------------------------

    comparison = calculate_comparison(
        baseline,
        automation
    )

    # ------------------------------------------------------
    # Results
    # ------------------------------------------------------

    print("\n")
    print("=" * 70)
    print("BASELINE RESULTS")
    print("=" * 70)

    print(
        f"\nShipments              : "
        f"{baseline['shipments']}"
    )

    print(
        f"Manual time/report     : "
        f"{baseline['minutes_per_report']} minutes"
    )

    print(
        f"Manual total effort    : "
        f"{baseline['total_hours']:.2f} hours"
    )

    print("\n")
    print("=" * 70)
    print("AUTOMATED RESULTS")
    print("=" * 70)

    print(
        f"\nReports generated      : "
        f"{automation['reports_generated']}"
    )

    print(
        f"Missing reports        : "
        f"{automation['missing_reports']}"
    )

    print(
        f"Verification time      : "
        f"{automation['verification_time_seconds']:.4f} seconds"
    )

    print(
        f"Evidence completeness  : "
        f"{completeness:.2f}%"
    )

    print("\n")
    print("=" * 70)
    print("EFFORT COMPARISON")
    print("=" * 70)

    print(
        f"\nManual processing      : "
        f"{comparison['manual_seconds']:.2f} seconds"
    )

    print(
        f"Automated processing   : "
        f"{comparison['automated_seconds']:.4f} seconds"
    )

    print(
        f"Time saved             : "
        f"{comparison['time_saved_seconds']:.2f} seconds"
    )

    print(
        f"Effort reduction       : "
        f"{comparison['reduction_percent']:.2f}%"
    )

    print(
        f"Target reduction       : "
        f"{TARGET_REDUCTION_PERCENT}%"
    )

    # ------------------------------------------------------
    # Target evaluation
    # ------------------------------------------------------

    if (
        comparison["reduction_percent"]
        >= TARGET_REDUCTION_PERCENT
    ):

        print(
            "\nTARGET STATUS: ACHIEVED"
        )

    else:

        print(
            "\nTARGET STATUS: NOT ACHIEVED"
        )

    # ------------------------------------------------------
    # Save results
    # ------------------------------------------------------

    results = pd.DataFrame(
        [
            {
                "method": "Manual Baseline",
                "shipments": baseline["shipments"],
                "time_per_report_minutes":
                    baseline["minutes_per_report"],
                "total_processing_seconds":
                    comparison["manual_seconds"],
                "reports_generated":
                    baseline["shipments"],
                "evidence_completeness_percent":
                    completeness
            },
            {
                "method": "ColdChainGuard",
                "shipments": baseline["shipments"],
                "time_per_report_seconds":
                    automation[
                        "verification_time_seconds"
                    ] / max(
                        automation[
                            "reports_generated"
                        ],
                        1
                    ),
                "total_processing_seconds":
                    comparison["automated_seconds"],
                "reports_generated":
                    automation["reports_generated"],
                "evidence_completeness_percent":
                    completeness
            }
        ]
    )

    save_results(
        results
    )

    # ------------------------------------------------------
    # Chart
    # ------------------------------------------------------

    create_time_comparison_chart(
        comparison
    )

    print("\n")
    print("=" * 70)
    print(
        "BASELINE EXPERIMENT COMPLETED"
    )
    print("=" * 70)


# ==========================================================
# RUN
# ==========================================================

if __name__ == "__main__":
    main()