"""
src/route_optimizer.py
ColdChainGuard - Day 5: Route & Resource Optimisation

Optimises vehicle-to-shipment assignments using multi-objective scoring:
  Minimize: cost + time + emissions
  Maximise: reliability (temperature compliance probability)

Approaches:
  1. Greedy baseline: assign by lowest composite score
  2. Weighted scoring: expose cost/time/emissions/reliability trade-off
  3. Strategy comparison: Conservative, Balanced, Eco-Friendly, Speed-First

Extends the existing tradeoff_experiment results with optimisation logic.

Outputs: data/optimization/
"""

import os
import sys
import warnings
warnings.filterwarnings("ignore")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OPT_DIR  = os.path.join(PROJECT_ROOT, "data", "optimization")
ETL_DIR  = os.path.join(PROJECT_ROOT, "data", "etl")
RAW_DIR  = os.path.join(PROJECT_ROOT, "data", "raw")
EXP_DIR  = os.path.join(PROJECT_ROOT, "data", "experiments")
PRED_DIR = os.path.join(PROJECT_ROOT, "data", "predictions")
os.makedirs(OPT_DIR, exist_ok=True)

PLOT_STYLE = {
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.3, "figure.dpi": 120, "font.size": 11,
}
plt.rcParams.update(PLOT_STYLE)

# Optimisation strategy definitions
STRATEGIES = {
    "Conservative":  {"w_cost": 0.15, "w_time": 0.15, "w_emit": 0.10, "w_rely": 0.60},
    "Balanced":      {"w_cost": 0.25, "w_time": 0.25, "w_emit": 0.25, "w_rely": 0.25},
    "Eco-Friendly":  {"w_cost": 0.15, "w_time": 0.10, "w_emit": 0.65, "w_rely": 0.10},
    "Speed-First":   {"w_cost": 0.10, "w_time": 0.70, "w_emit": 0.10, "w_rely": 0.10},
}


# ==========================================================
# LOAD DATA
# ==========================================================
def load_data():
    print("[Opt 1] Loading data...")

    master_csv = os.path.join(ETL_DIR, "master_shipments.csv")
    if os.path.exists(master_csv):
        master = pd.read_csv(master_csv)
    else:
        master = pd.read_csv(os.path.join(RAW_DIR, "shipments.csv"))

    vehicles  = pd.read_csv(os.path.join(RAW_DIR, "vehicles.csv"))
    shipments = pd.read_csv(os.path.join(RAW_DIR, "shipments.csv"))

    # Load risk scores if available
    pred_csv = os.path.join(PRED_DIR, "predictions.csv")
    risk_df = pd.read_csv(pred_csv)[["shipment_id", "excursion_risk_score"]] \
        if os.path.exists(pred_csv) else None

    print(f"         Master: {len(master)} rows | Vehicles: {len(vehicles)}")
    return master, vehicles, shipments, risk_df


# ==========================================================
# COMPUTE PER-SHIPMENT SCORES
# ==========================================================
def compute_shipment_scores(master, risk_df):
    """Normalise cost/time/emissions/reliability metrics per shipment."""
    print("[Opt 2] Computing normalised objective scores...")

    df = master.copy()

    # Proxy cost = journey_duration * 0.5 (fuel) + missing_readings * 2 (rework)
    if "journey_duration_min" in df.columns:
        df["cost_proxy"] = (
            df["journey_duration_min"].fillna(df["journey_duration_min"].median()) * 0.5
            + df["missing_readings"].fillna(0) * 2
            + df["traffic_delay_events"].fillna(0) * 15
        )
    else:
        df["cost_proxy"] = 100.0

    # Time proxy = journey duration + delays
    if "journey_duration_min" in df.columns:
        df["time_proxy"] = (
            df["journey_duration_min"].fillna(df["journey_duration_min"].median())
            + df["total_delay_minutes"].fillna(0)
        )
    else:
        df["time_proxy"] = 200.0

    # Emissions proxy = distance * vehicle_type factor (approximation)
    df["emissions_proxy"] = df["time_proxy"] * 0.21  # avg kg CO2/hr for refrigerated van

    # Reliability: 1 - excursion_risk (if available) else use compliance
    if risk_df is not None:
        df = df.merge(risk_df, on="shipment_id", how="left")
        df["reliability_score"] = 1 - df["excursion_risk_score"].fillna(0.3)
    elif "overall_compliance" in df.columns:
        df["reliability_score"] = (df["overall_compliance"] == "Compliant").astype(float)
    else:
        df["reliability_score"] = 0.7

    # Min-max normalise cost/time/emissions to [0,1]
    for col in ["cost_proxy", "time_proxy", "emissions_proxy"]:
        mn = df[col].min()
        mx = df[col].max()
        rng = mx - mn if mx != mn else 1
        df[f"{col}_norm"] = (df[col] - mn) / rng

    # Reliability already in [0,1]
    df["reliability_norm"] = df["reliability_score"].clip(0, 1)

    print(f"         Mean cost_norm={df['cost_proxy_norm'].mean():.3f}  "
          f"time_norm={df['time_proxy_norm'].mean():.3f}  "
          f"emit_norm={df['emissions_proxy_norm'].mean():.3f}  "
          f"rely_norm={df['reliability_norm'].mean():.3f}")
    return df


# ==========================================================
# APPLY STRATEGIES
# ==========================================================
def apply_strategies(df):
    """Score each shipment under each strategy and classify optimal strategy."""
    print("[Opt 3] Applying optimisation strategies...")

    strategy_results = {}

    for name, w in STRATEGIES.items():
        # Composite score = weighted sum (lower = better for cost/time/emit, higher rely is inverted)
        df[f"score_{name}"] = (
            w["w_cost"] * df["cost_proxy_norm"]
            + w["w_time"] * df["time_proxy_norm"]
            + w["w_emit"] * df["emissions_proxy_norm"]
            + w["w_rely"] * (1 - df["reliability_norm"])  # invert: lower is better
        )

        avg_cost  = df["cost_proxy"].mean()
        avg_time  = df["time_proxy"].mean()
        avg_emit  = df["emissions_proxy"].mean()
        avg_rely  = df["reliability_norm"].mean()
        avg_score = df[f"score_{name}"].mean()

        strategy_results[name] = {
            "avg_composite_score": round(avg_score, 4),
            "avg_cost":            round(avg_cost, 2),
            "avg_time_min":        round(avg_time, 2),
            "avg_emissions_kg":    round(avg_emit, 2),
            "avg_reliability_pct": round(avg_rely * 100, 2),
            "weights":             w,
        }
        print(f"         {name:<15} score={avg_score:.4f}  "
              f"cost={avg_cost:.1f}  time={avg_time:.1f}  "
              f"emit={avg_emit:.1f}  rely={avg_rely*100:.1f}%")

    # Each shipment's recommended strategy = lowest composite score
    score_cols = [f"score_{n}" for n in STRATEGIES]
    df["recommended_strategy"] = df[score_cols].idxmin(axis=1).str.replace("score_", "")

    return df, strategy_results


# ==========================================================
# VEHICLE ASSIGNMENT OPTIMISATION
# ==========================================================
def vehicle_assignment_optimisation(df, vehicles):
    """Greedy vehicle assignment: match shipments to least-loaded vehicles."""
    print("[Opt 4] Vehicle assignment optimisation...")

    if "vehicle_id" not in df.columns:
        print("         vehicle_id not in master — skipping assignment optimisation")
        return df

    # Current utilisation
    utilisation = df.groupby("vehicle_id").agg(
        shipment_count=("shipment_id", "count"),
        avg_score_balanced=(f"score_Balanced", "mean") if f"score_Balanced" in df.columns
        else ("shipment_id", "count"),
    ).reset_index()

    vehicles_aug = vehicles.merge(utilisation, on="vehicle_id", how="left")
    vehicles_aug["shipment_count"] = vehicles_aug["shipment_count"].fillna(0)

    # Flag over/under-utilised vehicles
    median_load = vehicles_aug["shipment_count"].median()
    vehicles_aug["utilisation_status"] = pd.cut(
        vehicles_aug["shipment_count"],
        bins=[-1, 0, median_load * 0.5, median_load * 1.5, float("inf")],
        labels=["Idle", "Under-utilised", "Optimal", "Over-utilised"]
    )

    utilisation_dist = vehicles_aug["utilisation_status"].value_counts().to_dict()
    print(f"         Vehicle utilisation: {utilisation_dist}")
    vehicles_aug.to_csv(os.path.join(OPT_DIR, "vehicle_utilisation.csv"), index=False)
    return vehicles_aug


# ==========================================================
# SAVE AND VISUALISE
# ==========================================================
def save_and_visualise(df, strategy_results, vehicles_aug):
    print("[Opt 5] Saving outputs and generating charts...")

    # Per-shipment optimisation results
    save_cols = [c for c in [
        "shipment_id", "vehicle_id", "product_type",
        "journey_duration_min", "cost_proxy", "time_proxy",
        "emissions_proxy", "reliability_norm",
        "score_Conservative", "score_Balanced",
        "score_Eco-Friendly", "score_Speed-First",
        "recommended_strategy",
    ] if c in df.columns]
    df[save_cols].to_csv(os.path.join(OPT_DIR, "optimisation_results.csv"), index=False)

    # Strategy comparison CSV
    rows = []
    for name, r in strategy_results.items():
        rows.append({
            "strategy": name,
            "avg_composite_score": r["avg_composite_score"],
            "avg_cost_proxy":      r["avg_cost"],
            "avg_time_min":        r["avg_time_min"],
            "avg_emissions_kg":    r["avg_emissions_kg"],
            "avg_reliability_pct": r["avg_reliability_pct"],
            "w_cost":  r["weights"]["w_cost"],
            "w_time":  r["weights"]["w_time"],
            "w_emit":  r["weights"]["w_emit"],
            "w_rely":  r["weights"]["w_rely"],
        })
    comp_df = pd.DataFrame(rows)
    comp_df.to_csv(os.path.join(OPT_DIR, "strategy_comparison.csv"), index=False)

    # Recommended strategy distribution
    if "recommended_strategy" in df.columns:
        rec_dist = df["recommended_strategy"].value_counts().reset_index()
        rec_dist.columns = ["strategy", "shipment_count"]
        rec_dist.to_csv(os.path.join(OPT_DIR, "recommended_strategy_distribution.csv"), index=False)

    # --- Plot 1: Strategy trade-off radar ---
    categories = ["Cost", "Time", "Emissions", "Reliability"]
    strategy_names = list(strategy_results.keys())
    palette = ["#2196F3", "#27ae60", "#e74c3c", "#f39c12"]

    # Normalise for radar
    vals_dict = {
        "Cost":        [r["avg_cost"] for r in strategy_results.values()],
        "Time":        [r["avg_time_min"] for r in strategy_results.values()],
        "Emissions":   [r["avg_emissions_kg"] for r in strategy_results.values()],
        "Reliability": [r["avg_reliability_pct"] for r in strategy_results.values()],
    }
    # Scale each to 0-100
    scaled = {}
    for k, vals in vals_dict.items():
        mn, mx = min(vals), max(vals)
        rng = mx - mn if mx != mn else 1
        if k == "Reliability":
            scaled[k] = [v for v in vals]  # already %
        else:
            scaled[k] = [100 - (v - mn) / rng * 100 for v in vals]  # invert: lower is better

    N = len(categories)
    angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(8, 7), subplot_kw=dict(polar=True))
    for i, name in enumerate(strategy_names):
        values = [scaled[cat][i] for cat in categories]
        values += values[:1]
        ax.plot(angles, values, color=palette[i], linewidth=2, label=name)
        ax.fill(angles, values, color=palette[i], alpha=0.12)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, fontsize=12)
    ax.set_title("Strategy Trade-off Radar\n(Cost, Time, Emissions, Reliability)",
                 fontsize=13, fontweight="bold", pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1), fontsize=10)
    plt.tight_layout()
    plt.savefig(os.path.join(OPT_DIR, "strategy_tradeoff_radar.png"), bbox_inches="tight")
    plt.close()

    # --- Plot 2: Strategy score bar chart ---
    fig, axes = plt.subplots(2, 2, figsize=(12, 9))
    fig.suptitle("Strategy Comparison Across Objectives", fontsize=13, fontweight="bold")
    metrics = [
        ("avg_cost_proxy",      "Avg Cost Proxy",       "#e74c3c"),
        ("avg_time_min",        "Avg Journey Time (min)","#f39c12"),
        ("avg_emissions_kg",    "Avg Emissions (kg CO2)","#27ae60"),
        ("avg_reliability_pct", "Avg Reliability (%)",   "#2196F3"),
    ]
    for ax, (col, title, color) in zip(axes.flatten(), metrics):
        bars = ax.bar(comp_df["strategy"], comp_df[col], color=color, edgecolor="white")
        ax.bar_label(bars, fmt="%.1f", padding=3, fontsize=9)
        ax.set_title(title, fontsize=11)
        ax.tick_params(axis="x", rotation=20)
    plt.tight_layout()
    plt.savefig(os.path.join(OPT_DIR, "strategy_comparison.png"), bbox_inches="tight")
    plt.close()

    # --- Plot 3: Vehicle utilisation ---
    if "utilisation_status" in vehicles_aug.columns:
        vc = vehicles_aug["utilisation_status"].value_counts()
        colors = {"Idle": "#e74c3c", "Under-utilised": "#f39c12",
                  "Optimal": "#27ae60", "Over-utilised": "#9b59b6"}
        fig, ax = plt.subplots(figsize=(8, 5))
        bars = ax.bar(vc.index, vc.values,
                      color=[colors.get(s, "#95a5a6") for s in vc.index],
                      edgecolor="white")
        ax.bar_label(bars, fmt="%d", padding=3)
        ax.set_title("Fleet Vehicle Utilisation Distribution", fontsize=13, fontweight="bold")
        ax.set_xlabel("Utilisation Status")
        ax.set_ylabel("Number of Vehicles")
        plt.tight_layout()
        plt.savefig(os.path.join(OPT_DIR, "vehicle_utilisation.png"), bbox_inches="tight")
        plt.close()

    print(f"         Outputs saved to data/optimization/")
    return comp_df


# ==========================================================
# MAIN
# ==========================================================
def main():
    print("=" * 60)
    print("COLDCHAINGUARD - DAY 5 ROUTE OPTIMISATION")
    print("=" * 60)

    master, vehicles, shipments, risk_df = load_data()
    df = compute_shipment_scores(master, risk_df)
    df, strategy_results = apply_strategies(df)
    vehicles_aug = vehicle_assignment_optimisation(df, vehicles)
    comp_df = save_and_visualise(df, strategy_results, vehicles_aug)

    print("\n" + "=" * 60)
    print("OPTIMISATION RESULTS SUMMARY")
    print("=" * 60)
    best_strategy = comp_df.loc[comp_df["avg_composite_score"].idxmin(), "strategy"]
    print(comp_df[["strategy", "avg_composite_score",
                   "avg_time_min", "avg_emissions_kg",
                   "avg_reliability_pct"]].to_string(index=False))
    print(f"\nLowest composite score: {best_strategy}")
    print("\nOutputs saved to: data/optimization/")
    for f in sorted(os.listdir(OPT_DIR)):
        if os.path.isfile(os.path.join(OPT_DIR, f)):
            print(f"  {f}")
    print("=" * 60)
    print("DAY 5 OPTIMISATION COMPLETE")


if __name__ == "__main__":
    main()
