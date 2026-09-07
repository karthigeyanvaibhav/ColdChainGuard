import os
import pandas as pd
import matplotlib.pyplot as plt


# ==========================================================
# COLDCHAINGUARD - COST / TIME / EMISSIONS / RELIABILITY
# ==========================================================

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

COMPLIANCE_FILE = os.path.join(
    PROJECT_ROOT,
    "data",
    "compliance_results.csv"
)

ROUTE_FILE = os.path.join(
    PROJECT_ROOT,
    "data",
    "raw",
    "route_events.csv"
)

OUTPUT_DIR = os.path.join(
    PROJECT_ROOT,
    "data",
    "experiments"
)

os.makedirs(OUTPUT_DIR, exist_ok=True)

RESULT_FILE = os.path.join(
    OUTPUT_DIR,
    "tradeoff_results.csv"
)

CHART_FILE = os.path.join(
    OUTPUT_DIR,
    "cost_time_emissions_reliability.png"
)


# ==========================================================
# LOAD DATA
# ==========================================================

def load_data():

    print("=" * 70)
    print("COLDCHAINGUARD - TRADE-OFF EXPERIMENT")
    print("=" * 70)

    compliance = pd.read_csv(
        COMPLIANCE_FILE
    )

    route_events = pd.read_csv(
        ROUTE_FILE
    )

    print(
        f"\nCompliance records : {len(compliance)}"
    )

    print(
        f"Route events       : {len(route_events)}"
    )

    return compliance, route_events


# ==========================================================
# CALCULATE ROUTE DELAYS
# ==========================================================

def calculate_route_metrics(route_events):

    delay_events = route_events[
        route_events["event_type"].isin(
            [
                "Traffic Delay",
                "Rest Stop",
                "Cold Storage Stop"
            ]
        )
    ].copy()

    delay_by_shipment = (
        delay_events
        .groupby("shipment_id")[
            "duration_minutes"
        ]
        .sum()
        .reset_index()
    )

    delay_by_shipment.rename(
        columns={
            "duration_minutes":
                "delay_minutes"
        },
        inplace=True
    )

    return delay_by_shipment


# ==========================================================
# GENERATE STRATEGY METRICS
# ==========================================================

def generate_strategy_results(
    compliance,
    delay_data
):

    shipments = compliance[
        ["shipment_id"]
    ].drop_duplicates()

    shipments = shipments.merge(
        delay_data,
        on="shipment_id",
        how="left"
    )

    shipments["delay_minutes"] = (
        shipments["delay_minutes"]
        .fillna(0)
    )

    strategies = []

    # ------------------------------------------------------
    # Strategy assumptions
    # ------------------------------------------------------
    #
    # These are simulation parameters for the student
    # experiment, not real-world transport prices.
    #
    # ------------------------------------------------------

    strategy_config = {

        "Normal": {
            "cost_per_km": 1.00,
            "time_factor": 1.00,
            "emission_factor": 1.00,
            "reliability": 0.90
        },

        "Fast": {
            "cost_per_km": 1.35,
            "time_factor": 0.75,
            "emission_factor": 1.30,
            "reliability": 0.94
        },

        "Eco": {
            "cost_per_km": 0.90,
            "time_factor": 1.20,
            "emission_factor": 0.70,
            "reliability": 0.84
        },

        "Reliable": {
            "cost_per_km": 1.20,
            "time_factor": 0.95,
            "emission_factor": 1.05,
            "reliability": 0.97
        }
    }

    # ------------------------------------------------------
    # Estimated route distance
    # ------------------------------------------------------
    #
    # The project dataset does not contain actual GPS
    # distance, so we derive a reproducible simulated
    # distance from route-event activity.
    #
    # ------------------------------------------------------

    shipments["estimated_distance_km"] = (
        100
        + shipments["delay_minutes"] * 2
    )

    # ------------------------------------------------------
    # Generate metrics
    # ------------------------------------------------------

    for strategy, config in strategy_config.items():

        result = shipments.copy()

        result["strategy"] = strategy

        # Cost
        result["cost"] = (
            result["estimated_distance_km"]
            * config["cost_per_km"]
        )

        # Delivery time
        result["delivery_time_minutes"] = (
            120
            + result["delay_minutes"]
        ) * config["time_factor"]

        # Emissions
        result["emissions_kg"] = (
            result["estimated_distance_km"]
            * 0.8
            * config["emission_factor"]
        )

        # Reliability
        result["reliability"] = (
            config["reliability"]
        )

        strategies.append(
            result[
                [
                    "shipment_id",
                    "strategy",
                    "cost",
                    "delivery_time_minutes",
                    "emissions_kg",
                    "reliability"
                ]
            ]
        )

    return pd.concat(
        strategies,
        ignore_index=True
    )


# ==========================================================
# NORMALIZE METRICS
# ==========================================================

def calculate_scores(results):

    # Lower is better for cost, time and emissions.
    # Higher is better for reliability.

    for column in [
        "cost",
        "delivery_time_minutes",
        "emissions_kg"
    ]:

        minimum = results[column].min()
        maximum = results[column].max()

        results[
            f"{column}_score"
        ] = (
            (maximum - results[column])
            / (maximum - minimum)
            * 100
        )

    results["reliability_score"] = (
        results["reliability"] * 100
    )

    # ------------------------------------------------------
    # Overall weighted score
    # ------------------------------------------------------
    #
    # Cost       = 25%
    # Time       = 25%
    # Emissions  = 20%
    # Reliability= 30%
    #
    # Reliability receives the highest weight because
    # compliance is the primary objective.
    #
    # ------------------------------------------------------

    results["overall_score"] = (

        results["cost_score"] * 0.25

        + results["delivery_time_minutes_score"]
        * 0.25

        + results["emissions_kg_score"]
        * 0.20

        + results["reliability_score"]
        * 0.30
    )

    return results


# ==========================================================
# CREATE SUMMARY
# ==========================================================

def create_summary(results):

    summary = (
        results
        .groupby("strategy")
        .agg(
            shipments=(
                "shipment_id",
                "count"
            ),

            average_cost=(
                "cost",
                "mean"
            ),

            average_delivery_time=(
                "delivery_time_minutes",
                "mean"
            ),

            average_emissions=(
                "emissions_kg",
                "mean"
            ),

            reliability=(
                "reliability",
                "mean"
            ),

            overall_score=(
                "overall_score",
                "mean"
            )
        )
        .reset_index()
    )

    summary["reliability_percent"] = (
        summary["reliability"] * 100
    )

    summary = summary.sort_values(
        "overall_score",
        ascending=False
    )

    return summary


# ==========================================================
# DISPLAY RESULTS
# ==========================================================

def display_results(summary):

    print("\n")
    print("=" * 70)
    print("TRADE-OFF RESULTS")
    print("=" * 70)

    display_columns = [
        "strategy",
        "average_cost",
        "average_delivery_time",
        "average_emissions",
        "reliability_percent",
        "overall_score"
    ]

    print(
        summary[
            display_columns
        ].round(2).to_string(
            index=False
        )
    )

    best_strategy = summary.iloc[0]

    print("\n")
    print("=" * 70)
    print("SELECTED STRATEGY")
    print("=" * 70)

    print(
        f"\nStrategy     : "
        f"{best_strategy['strategy']}"
    )

    print(
        f"Overall score: "
        f"{best_strategy['overall_score']:.2f}"
    )

    print(
        f"Reliability  : "
        f"{best_strategy['reliability_percent']:.2f}%"
    )


# ==========================================================
# CREATE CHART
# ==========================================================

def create_chart(summary):

    plt.figure(
        figsize=(10, 6)
    )

    plt.bar(
        summary["strategy"],
        summary["overall_score"]
    )

    plt.xlabel(
        "Strategy"
    )

    plt.ylabel(
        "Overall Score"
    )

    plt.title(
        "ColdChainGuard Strategy Trade-off"
    )

    plt.ylim(
        0,
        100
    )

    plt.tight_layout()

    plt.savefig(
        CHART_FILE,
        dpi=300
    )

    plt.close()

    print(
        f"\nChart saved to:\n"
        f"{CHART_FILE}"
    )


# ==========================================================
# SAVE RESULTS
# ==========================================================

def save_results(
    results,
    summary
):

    # Save detailed shipment-level experiment
    results.to_csv(
        RESULT_FILE,
        index=False
    )

    print(
        f"\nDetailed results saved to:\n"
        f"{RESULT_FILE}"
    )

    # Also save strategy summary
    summary_file = os.path.join(
        OUTPUT_DIR,
        "tradeoff_summary.csv"
    )

    summary.to_csv(
        summary_file,
        index=False
    )

    print(
        f"Summary saved to:\n"
        f"{summary_file}"
    )


# ==========================================================
# MAIN
# ==========================================================

def main():

    compliance, route_events = load_data()

    print("\n")
    print(
        "=" * 70
    )
    print(
        "CALCULATING ROUTE METRICS"
    )
    print(
        "=" * 70
    )

    delay_data = calculate_route_metrics(
        route_events
    )

    print(
        f"\nShipments with route data: "
        f"{len(delay_data)}"
    )

    results = generate_strategy_results(
        compliance,
        delay_data
    )

    results = calculate_scores(
        results
    )

    summary = create_summary(
        results
    )

    display_results(
        summary
    )

    create_chart(
        summary
    )

    save_results(
        results,
        summary
    )

    print("\n")
    print("=" * 70)
    print(
        "TRADE-OFF EXPERIMENT COMPLETED"
    )
    print("=" * 70)


# ==========================================================
# RUN
# ==========================================================

if __name__ == "__main__":
    main()