import os
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

SENSOR_FILE = os.path.join(
    PROJECT_ROOT,
    "data",
    "raw",
    "sensor_logs.csv"
)

SHIPMENT_FILE = os.path.join(
    PROJECT_ROOT,
    "data",
    "raw",
    "shipments.csv"
)

BATCH_FILE = os.path.join(
    PROJECT_ROOT,
    "data",
    "raw",
    "product_batches.csv"
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
# LOAD DATA
# ==========================================================

def load_data():

    print("=" * 70)
    print("COLDCHAINGUARD - ALERT THRESHOLD TUNING")
    print("=" * 70)

    sensors = pd.read_csv(
        SENSOR_FILE
    )

    shipments = pd.read_csv(
        SHIPMENT_FILE
    )

    batches = pd.read_csv(
        BATCH_FILE
    )

    print(
        f"\nSensor records   : {len(sensors)}"
    )

    print(
        f"Shipments        : {len(shipments)}"
    )

    print(
        f"Product batches  : {len(batches)}"
    )

    return sensors, shipments, batches


# ==========================================================
# PREPARE DATA
# ==========================================================

def prepare_data(
    sensors,
    shipments,
    batches
):

    data = sensors.merge(
        shipments[
            [
                "shipment_id",
                "batch_id"
            ]
        ],
        on="shipment_id",
        how="left"
    )

    data = data.merge(
        batches[
            [
                "batch_id",
                "product_type",
                "min_temperature_c",
                "max_temperature_c"
            ]
        ],
        on="batch_id",
        how="left"
    )

    data["temperature_c"] = pd.to_numeric(
        data["temperature_c"],
        errors="coerce"
    )

    data = data.dropna(
        subset=[
            "temperature_c",
            "min_temperature_c",
            "max_temperature_c"
        ]
    )

    return data


# ==========================================================
# THRESHOLD STRATEGIES
# ==========================================================

def define_strategies():

    return {

        # --------------------------------------------------
        # Strategy 1
        # Tight threshold
        # --------------------------------------------------

        "Tight": {
            "warning_margin": 0.5,
            "critical_margin": 2.0
        },

        # --------------------------------------------------
        # Strategy 2
        # Balanced threshold
        # --------------------------------------------------

        "Balanced": {
            "warning_margin": 1.0,
            "critical_margin": 3.0
        },

        # --------------------------------------------------
        # Strategy 3
        # Relaxed threshold
        # --------------------------------------------------

        "Relaxed": {
            "warning_margin": 2.0,
            "critical_margin": 5.0
        }
    }


# ==========================================================
# CLASSIFY TEMPERATURE
# ==========================================================

def classify_temperature(
    temperature,
    minimum,
    maximum,
    warning_margin,
    critical_margin
):

    # ------------------------------------------------------
    # Safe range
    # ------------------------------------------------------

    if minimum <= temperature <= maximum:

        return "Compliant"

    # ------------------------------------------------------
    # Distance from valid range
    # ------------------------------------------------------

    if temperature < minimum:

        deviation = minimum - temperature

    else:

        deviation = temperature - maximum

    # ------------------------------------------------------
    # Critical
    # ------------------------------------------------------

    if deviation >= critical_margin:

        return "Critical"

    # ------------------------------------------------------
    # Warning
    # ------------------------------------------------------

    return "Warning"


# ==========================================================
# RUN STRATEGY
# ==========================================================

def run_strategy(
    data,
    strategy_name,
    parameters
):

    result = data.copy()

    result["temperature_status"] = result.apply(
        lambda row: classify_temperature(
            row["temperature_c"],
            row["min_temperature_c"],
            row["max_temperature_c"],
            parameters["warning_margin"],
            parameters["critical_margin"]
        ),
        axis=1
    )

    counts = (
        result["temperature_status"]
        .value_counts()
    )

    compliant = counts.get(
        "Compliant",
        0
    )

    warning = counts.get(
        "Warning",
        0
    )

    critical = counts.get(
        "Critical",
        0
    )

    total = len(result)

    alert_count = warning + critical

    alert_rate = (
        alert_count / total
    ) * 100

    critical_rate = (
        critical / total
    ) * 100

    return {
        "strategy": strategy_name,
        "warning_margin_c": parameters[
            "warning_margin"
        ],
        "critical_margin_c": parameters[
            "critical_margin"
        ],
        "total_observations": total,
        "compliant": compliant,
        "warning": warning,
        "critical": critical,
        "total_alerts": alert_count,
        "alert_rate_percent": alert_rate,
        "critical_rate_percent": critical_rate
    }


# ==========================================================
# RUN ALL STRATEGIES
# ==========================================================

def run_experiment(data):

    strategies = define_strategies()

    results = []

    for name, parameters in strategies.items():

        print("\n")
        print("-" * 70)

        print(
            f"Testing strategy: {name}"
        )

        print(
            f"Warning margin : "
            f"{parameters['warning_margin']}°C"
        )

        print(
            f"Critical margin: "
            f"{parameters['critical_margin']}°C"
        )

        result = run_strategy(
            data,
            name,
            parameters
        )

        results.append(
            result
        )

    return pd.DataFrame(
        results
    )


# ==========================================================
# SELECT BEST STRATEGY
# ==========================================================

def select_best_strategy(results):

    # ------------------------------------------------------
    # We want to minimize alerts while still maintaining
    # the ability to detect serious deviations.
    #
    # Critical alerts are never treated as false alerts.
    # The score penalizes excessive warning alerts.
    # ------------------------------------------------------

    results = results.copy()

    results["score"] = (
        results["critical"] * 5
        + results["warning"]
    )

    best = results.sort_values(
        by=[
            "score",
            "alert_rate_percent"
        ]
    ).iloc[0]

    return best


# ==========================================================
# SAVE RESULTS
# ==========================================================

def save_results(results):

    output_file = os.path.join(
        RESULT_DIR,
        "threshold_tuning_results.csv"
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

def create_chart(results):

    plt.figure(
        figsize=(9, 6)
    )

    chart_data = results[
        [
            "strategy",
            "warning",
            "critical"
        ]
    ].copy()

    chart_data = chart_data.melt(
        id_vars="strategy",
        var_name="alert_type",
        value_name="observations"
    )

    sns.barplot(
        data=chart_data,
        x="strategy",
        y="observations",
        hue="alert_type"
    )

    plt.title(
        "Temperature Alert Threshold Comparison"
    )

    plt.xlabel(
        "Threshold Strategy"
    )

    plt.ylabel(
        "Number of Observations"
    )

    plt.tight_layout()

    output_file = os.path.join(
        RESULT_DIR,
        "threshold_comparison.png"
    )

    plt.savefig(
        output_file,
        dpi=300
    )

    plt.close()

    print(
        f"Chart saved to:\n{output_file}"
    )


# ==========================================================
# MAIN
# ==========================================================

def main():

    sensors, shipments, batches = load_data()

    data = prepare_data(
        sensors,
        shipments,
        batches
    )

    print("\n")
    print("=" * 70)
    print("PREPARED TEMPERATURE DATA")
    print("=" * 70)

    print(
        f"\nUsable temperature observations: "
        f"{len(data)}"
    )

    results = run_experiment(
        data
    )

    print("\n")
    print("=" * 70)
    print("THRESHOLD EXPERIMENT RESULTS")
    print("=" * 70)

    print(
        results.to_string(
            index=False
        )
    )

    best = select_best_strategy(
        results
    )

    print("\n")
    print("=" * 70)
    print("SELECTED THRESHOLD")
    print("=" * 70)

    print(
        f"\nSelected strategy : "
        f"{best['strategy']}"
    )

    print(
        f"Warning margin    : "
        f"{best['warning_margin_c']}°C"
    )

    print(
        f"Critical margin   : "
        f"{best['critical_margin_c']}°C"
    )

    print(
        f"Warning alerts    : "
        f"{int(best['warning'])}"
    )

    print(
        f"Critical alerts   : "
        f"{int(best['critical'])}"
    )

    print(
        f"Total alerts      : "
        f"{int(best['total_alerts'])}"
    )

    print(
        f"Alert rate        : "
        f"{best['alert_rate_percent']:.2f}%"
    )

    save_results(
        results
    )

    create_chart(
        results
    )

    print("\n")
    print("=" * 70)
    print(
        "ALERT THRESHOLD TUNING COMPLETED"
    )
    print("=" * 70)


# ==========================================================
# RUN
# ==========================================================

if __name__ == "__main__":
    main()