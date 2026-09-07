import os
import pandas as pd


# ==========================================================
# PROJECT PATHS
# ==========================================================

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

SENSOR_LOG_FILE = os.path.join(
    PROJECT_ROOT,
    "data",
    "raw",
    "sensor_logs.csv"
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
# CONFIGURATION
# ==========================================================

MAX_RETRY_ATTEMPTS = 3


# ==========================================================
# LOAD SENSOR DATA
# ==========================================================

def load_sensor_data():

    print("=" * 70)
    print("COLDCHAINGUARD - STORE AND FORWARD SIMULATION")
    print("=" * 70)

    df = pd.read_csv(
        SENSOR_LOG_FILE
    )

    df["recorded_at"] = pd.to_datetime(
        df["recorded_at"]
    )

    print(
        f"\nTotal sensor observations: {len(df)}"
    )

    return df


# ==========================================================
# SIMULATE STORE-AND-FORWARD
# ==========================================================

def simulate_store_and_forward(df):

    print("\n")
    print("=" * 70)
    print("SIMULATING NETWORK FAILURE")
    print("=" * 70)

    result = df.copy()

    # ------------------------------------------------------
    # Default state
    # ------------------------------------------------------

    result["transmission_status"] = "Uploaded"

    result["buffer_status"] = "Not Buffered"

    result["retry_count"] = 0

    result["recovery_status"] = "Not Required"

    # ------------------------------------------------------
    # Detect offline observations
    # ------------------------------------------------------

    offline_mask = (
        result["network_status"]
        .astype(str)
        .str.lower()
        == "offline"
    )

    offline_count = offline_mask.sum()

    print(
        f"\nOffline observations detected: "
        f"{offline_count}"
    )

    # ------------------------------------------------------
    # Store offline observations locally
    # ------------------------------------------------------

    result.loc[
        offline_mask,
        "transmission_status"
    ] = "Buffered"

    result.loc[
        offline_mask,
        "buffer_status"
    ] = "Stored Locally"

    result.loc[
        offline_mask,
        "recovery_status"
    ] = "Waiting for Network"

    # ------------------------------------------------------
    # Simulate network recovery
    # ------------------------------------------------------

    # In this simulation, every buffered observation
    # is successfully forwarded once connectivity returns.

    result.loc[
        offline_mask,
        "transmission_status"
    ] = "Forwarded"

    result.loc[
        offline_mask,
        "buffer_status"
    ] = "Released"

    result.loc[
        offline_mask,
        "retry_count"
    ] = 1

    result.loc[
        offline_mask,
        "recovery_status"
    ] = "Recovered"

    return result


# ==========================================================
# CALCULATE METRICS
# ==========================================================

def calculate_metrics(result):

    total = len(result)

    online = (
        result["network_status"]
        .astype(str)
        .str.lower()
        == "online"
    ).sum()

    offline = (
        result["network_status"]
        .astype(str)
        .str.lower()
        == "offline"
    ).sum()

    buffered = (
        result["buffer_status"]
        == "Released"
    ).sum()

    forwarded = (
        result["transmission_status"]
        == "Forwarded"
    ).sum()

    recovered = (
        result["recovery_status"]
        == "Recovered"
    ).sum()

    data_loss = total - (
        online + recovered
    )

    if offline > 0:

        recovery_rate = (
            recovered / offline
        ) * 100

    else:

        recovery_rate = 100

    return {
        "total_observations": total,
        "online_observations": online,
        "offline_observations": offline,
        "buffered_observations": buffered,
        "forwarded_observations": forwarded,
        "recovered_observations": recovered,
        "data_loss": data_loss,
        "recovery_rate_percent": recovery_rate
    }


# ==========================================================
# DISPLAY RESULTS
# ==========================================================

def display_results(metrics):

    print("\n")
    print("=" * 70)
    print("STORE-AND-FORWARD RESULTS")
    print("=" * 70)

    print(
        f"\nTotal observations       : "
        f"{metrics['total_observations']}"
    )

    print(
        f"Online observations      : "
        f"{metrics['online_observations']}"
    )

    print(
        f"Offline observations     : "
        f"{metrics['offline_observations']}"
    )

    print(
        f"Buffered observations    : "
        f"{metrics['buffered_observations']}"
    )

    print(
        f"Successfully forwarded   : "
        f"{metrics['forwarded_observations']}"
    )

    print(
        f"Recovered observations   : "
        f"{metrics['recovered_observations']}"
    )

    print(
        f"Data loss                : "
        f"{metrics['data_loss']}"
    )

    print(
        f"Recovery rate            : "
        f"{metrics['recovery_rate_percent']:.2f}%"
    )

    if metrics["data_loss"] == 0:

        print(
            "\nSTORE-AND-FORWARD TEST: PASSED"
        )

    else:

        print(
            "\nSTORE-AND-FORWARD TEST: REVIEW"
        )


# ==========================================================
# SAVE RESULTS
# ==========================================================

def save_results(result, metrics):

    output_file = os.path.join(
        RESULT_DIR,
        "store_and_forward_results.csv"
    )

    result.to_csv(
        output_file,
        index=False
    )

    metrics_file = os.path.join(
        RESULT_DIR,
        "store_and_forward_metrics.csv"
    )

    pd.DataFrame(
        [metrics]
    ).to_csv(
        metrics_file,
        index=False
    )

    print("\n")
    print("=" * 70)
    print("FILES SAVED")
    print("=" * 70)

    print(
        f"\nDetailed records:\n{output_file}"
    )

    print(
        f"\nMetrics:\n{metrics_file}"
    )


# ==========================================================
# MAIN
# ==========================================================

def main():

    df = load_sensor_data()

    result = simulate_store_and_forward(
        df
    )

    metrics = calculate_metrics(
        result
    )

    display_results(
        metrics
    )

    save_results(
        result,
        metrics
    )

    print("\n")
    print("=" * 70)
    print(
        "STORE-AND-FORWARD SIMULATION COMPLETED"
    )
    print("=" * 70)


# ==========================================================
# RUN
# ==========================================================

if __name__ == "__main__":
    main()