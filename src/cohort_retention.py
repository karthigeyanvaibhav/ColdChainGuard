"""
src/cohort_retention.py
ColdChainGuard — Day 9: Cohort & Retention Analysis Analogue

Official Day 9 requirement: Cohort & Retention Analysis.
ColdChainGuard analogue: Vehicle Compliance-Retention Cohort Analysis.

In retail analytics, cohort/retention tracks how customers acquired in the same
period continue to purchase in subsequent periods. In ColdChainGuard, the
directly analogous concept is:

  "How do vehicles first deployed in the same quarter maintain compliance
   performance across subsequent operational quarters?"

A vehicle 'retained' in a quarter = it operated at least one compliant shipment
in that quarter. This reveals whether fleet quality is improving, degrading, or
stable across operational cohorts.

Additional cohorts:
  - Sensor installation cohort: sensors installed same month -> calibration
    survival (fraction still valid N months later)
  - Product-type cohort: batches of the same product type -> compliance
    retention across route-age quartiles

Outputs:
  data/cohort/vehicle_cohort_matrix.csv
  data/cohort/sensor_survival_matrix.csv
  data/cohort/cohort_heatmap_vehicle.png
  data/cohort/cohort_heatmap_sensor.png
  data/cohort/cohort_report.md
"""

import os
import sys
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

RAW_DIR  = os.path.join(PROJECT_ROOT, "data", "raw")
ETL_DIR  = os.path.join(PROJECT_ROOT, "data", "etl")
OUT_DIR  = os.path.join(PROJECT_ROOT, "data", "cohort")
os.makedirs(OUT_DIR, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────────────────────────────────────

def load_data():
    print("[C1] Loading data...")

    master_csv = os.path.join(ETL_DIR, "master_shipments.csv")
    master = pd.read_csv(master_csv) if os.path.exists(master_csv) \
             else pd.read_csv(os.path.join(RAW_DIR, "shipments.csv"))

    comp_csv = os.path.join(PROJECT_ROOT, "data", "compliance_results.csv")
    if os.path.exists(comp_csv):
        comp = pd.read_csv(comp_csv)
        if "overall_compliance" not in master.columns:
            master = master.merge(
                comp[["shipment_id", "overall_compliance"]],
                on="shipment_id", how="left"
            )

    vehicles = pd.read_csv(os.path.join(RAW_DIR, "vehicles.csv"))
    sensors  = pd.read_csv(os.path.join(RAW_DIR, "sensors.csv"))
    cals     = pd.read_csv(os.path.join(RAW_DIR, "calibrations.csv"))

    print(f"     Master: {len(master)} | Vehicles: {len(vehicles)} | "
          f"Sensors: {len(sensors)} | Calibrations: {len(cals)}")
    return master, vehicles, sensors, cals


# ─────────────────────────────────────────────────────────────────────────────
# VEHICLE COMPLIANCE-RETENTION COHORT
# ─────────────────────────────────────────────────────────────────────────────

def vehicle_cohort_analysis(master, vehicles):
    """
    Cohort = quarter in which a vehicle made its FIRST shipment.
    Retention metric = fraction of vehicles in that cohort that had at least one
    compliant shipment in each subsequent quarter (Quarter 0, 1, 2, ...).
    """
    print("[C2] Vehicle compliance-retention cohort analysis...")

    df = master.copy()

    # Ensure departure_time is available (may not be in master_shipments.csv after merges)
    if "departure_time" not in df.columns or df["departure_time"].isna().all():
        raw_shp = pd.read_csv(os.path.join(RAW_DIR, "shipments.csv"))
        if "departure_time" in raw_shp.columns and "shipment_id" in raw_shp.columns:
            df = df.merge(raw_shp[["shipment_id", "departure_time"]], on="shipment_id",
                          how="left", suffixes=("", "_raw"))
            if "departure_time_raw" in df.columns:
                df["departure_time"] = df["departure_time"].fillna(df["departure_time_raw"])
                df.drop(columns=["departure_time_raw"], inplace=True)

    df["departure_time"] = pd.to_datetime(df.get("departure_time"), errors="coerce")
    df = df.dropna(subset=["departure_time"])
    df["quarter"] = df["departure_time"].dt.to_period("Q")

    # Cohort = first quarter each vehicle appeared
    first_q = df.groupby("vehicle_id")["quarter"].min().reset_index()
    first_q.columns = ["vehicle_id", "cohort_quarter"]

    df = df.merge(first_q, on="vehicle_id", how="left")

    # Parse "2024Q2" -> integer = year*4 + quarter
    def _q2i(val):
        """Convert period string like '2024Q2' to integer."""
        try:
            s = str(val)
            yr, q = s.split("Q")
            return int(yr) * 4 + int(q)
        except Exception:
            return None

    q_ints  = [_q2i(v) for v in df["quarter"].astype(str)]
    cq_ints = [_q2i(v) for v in df["cohort_quarter"].astype(str)]
    df["quarter_offset"] = [
        (a - b) if (a is not None and b is not None) else None
        for a, b in zip(q_ints, cq_ints)
    ]
    df["quarter_offset"] = pd.array(df["quarter_offset"], dtype="Int64")

    df["is_compliant"] = (df.get("overall_compliance", pd.Series([""] * len(df))) == "Compliant").astype(int)

    # For each (cohort_quarter, quarter_offset) — fraction of cohort vehicles with >=1 compliant shipment
    pivot = (
        df.groupby(["cohort_quarter", "quarter_offset", "vehicle_id"])["is_compliant"]
        .max()                        # 1 if vehicle had any compliant shipment that offset
        .reset_index()
        .groupby(["cohort_quarter", "quarter_offset"])
        .agg(vehicles_active=("vehicle_id", "count"),
             vehicles_compliant=("is_compliant", "sum"))
        .reset_index()
    )
    pivot["retention_rate"] = (pivot["vehicles_compliant"] / pivot["vehicles_active"]).round(3)

    # Pivot to cohort matrix (rows=cohort, cols=offset)
    matrix = pivot.pivot(index="cohort_quarter", columns="quarter_offset",
                         values="retention_rate")
    matrix.index = matrix.index.astype(str)
    matrix.columns = [f"Q+{c}" for c in matrix.columns]
    matrix = matrix.fillna(np.nan)

    matrix.to_csv(os.path.join(OUT_DIR, "vehicle_cohort_matrix.csv"))
    print(f"     Cohorts: {len(matrix)} | Quarters tracked: {matrix.shape[1]}")

    # Cohort sizes
    cohort_sizes = first_q.groupby("cohort_quarter")["vehicle_id"].count()
    cohort_sizes.index = cohort_sizes.index.astype(str)

    return matrix, cohort_sizes, pivot


# ─────────────────────────────────────────────────────────────────────────────
# SENSOR CALIBRATION SURVIVAL COHORT
# ─────────────────────────────────────────────────────────────────────────────

def sensor_survival_cohort(sensors, cals):
    """
    Cohort = month sensor was installed.
    Retention metric = fraction of sensors in that cohort with a VALID calibration
    N months after installation (calibration not expired).
    """
    print("[C3] Sensor calibration survival cohort analysis...")

    s = sensors.copy()
    c = cals.copy()

    s["installation_date"] = pd.to_datetime(s["installation_date"], errors="coerce")
    c["expiry_date"]        = pd.to_datetime(c["expiry_date"],       errors="coerce")
    c["calibration_date"]   = pd.to_datetime(c["calibration_date"],  errors="coerce")

    s = s.dropna(subset=["installation_date"])
    s["install_month"] = s["installation_date"].dt.to_period("M")

    # Latest calibration expiry per sensor
    latest_cal = c.groupby("sensor_id")["expiry_date"].max().reset_index()
    latest_cal.columns = ["sensor_id", "latest_expiry"]

    s = s.merge(latest_cal, on="sensor_id", how="left")

    # Survival at months 1, 3, 6, 12 post-installation
    offsets = [1, 3, 6, 12]
    rows = []
    for cohort, grp in s.groupby("install_month"):
        n_total = len(grp)
        row = {"cohort_month": str(cohort), "cohort_size": n_total}
        for mo in offsets:
            cutoff = cohort.to_timestamp() + pd.DateOffset(months=mo)
            n_valid = (grp["latest_expiry"].fillna(pd.Timestamp.min) >= cutoff).sum()
            row[f"valid_at_M{mo:02d}"] = round(n_valid / n_total, 3) if n_total > 0 else np.nan
        rows.append(row)

    survival = pd.DataFrame(rows)
    survival.to_csv(os.path.join(OUT_DIR, "sensor_survival_matrix.csv"), index=False)
    print(f"     Sensor cohorts: {len(survival)} | Offsets: M01, M03, M06, M12")
    return survival


# ─────────────────────────────────────────────────────────────────────────────
# HEATMAP PLOTS
# ─────────────────────────────────────────────────────────────────────────────

def plot_heatmap(matrix, title, filename, fmt=".0%", cmap="RdYlGn"):
    """Plot a cohort retention heatmap."""
    if matrix.empty or matrix.shape[1] == 0:
        print(f"     [SKIP] {filename} — no data")
        return
    fig, ax = plt.subplots(figsize=(max(6, matrix.shape[1] * 1.4),
                                     max(4, matrix.shape[0] * 0.8)))
    data = matrix.values.astype(float)

    im = ax.imshow(data, cmap=cmap, aspect="auto", vmin=0, vmax=1)
    plt.colorbar(im, ax=ax, label="Retention Rate")

    ax.set_xticks(range(matrix.shape[1]))
    ax.set_xticklabels(matrix.columns, fontsize=9, rotation=30)
    ax.set_yticks(range(matrix.shape[0]))
    ax.set_yticklabels(matrix.index, fontsize=9)

    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            val = data[i, j]
            if not np.isnan(val):
                text_color = "black" if val > 0.4 else "white"
                ax.text(j, i, f"{val:.0%}", ha="center", va="center",
                        fontsize=8, color=text_color, fontweight="bold")

    ax.set_title(title, fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("Period Offset (since first activity)", fontsize=10)
    ax.set_ylabel("Cohort", fontsize=10)
    plt.tight_layout()
    plt.savefig(filename, dpi=120, bbox_inches="tight")
    plt.close()
    print(f"     Saved: {os.path.basename(filename)}")


def plot_survival_heatmap(survival, filename):
    """Plot sensor calibration survival heatmap."""
    if survival.empty:
        return
    cols = [c for c in survival.columns if c.startswith("valid_at_")]
    if not cols:
        return
    matrix = survival.set_index("cohort_month")[cols]
    matrix.columns = [c.replace("valid_at_", "Month ") for c in cols]
    plot_heatmap(matrix, "Sensor Calibration Survival by Installation Cohort",
                 filename, cmap="RdYlGn")


# ─────────────────────────────────────────────────────────────────────────────
# INSIGHTS
# ─────────────────────────────────────────────────────────────────────────────

def compute_insights(matrix, cohort_sizes):
    """Extract key insights from the cohort matrix."""
    insights = []

    # Average retention at Q+0 (first quarter)
    if "Q+0" in matrix.columns:
        avg_q0 = matrix["Q+0"].mean()
        insights.append(f"Mean first-quarter compliance retention: {avg_q0:.0%}")

    # Retention trend across offsets
    means = matrix.mean(axis=0).dropna()
    if len(means) > 1:
        first, last = means.iloc[0], means.iloc[-1]
        direction = "improving" if last > first else "declining"
        insights.append(f"Retention trend Q+0 to Q+{len(means)-1}: {first:.0%} -> {last:.0%} ({direction})")

    # Best and worst cohorts
    q0 = matrix.get("Q+0", pd.Series(dtype=float)).dropna()
    if len(q0):
        best  = q0.idxmax()
        worst = q0.idxmin()
        insights.append(f"Best-performing cohort (Q+0 retention): {best} ({q0[best]:.0%})")
        insights.append(f"Worst-performing cohort (Q+0 retention): {worst} ({q0[worst]:.0%})")

    return insights


# ─────────────────────────────────────────────────────────────────────────────
# REPORT
# ─────────────────────────────────────────────────────────────────────────────

def write_report(matrix, cohort_sizes, survival, insights):
    lines = [
        "# ColdChainGuard -- Day 9: Cohort & Retention Analysis",
        "",
        "## Analogue Mapping",
        "",
        "| Official Requirement | ColdChainGuard Implementation |",
        "|----------------------|-------------------------------|",
        "| Cohort & Retention (Day 9) | Vehicle Compliance-Retention Cohort Analysis |",
        "| Customer cohorts by acquisition date | Vehicle cohorts by first-shipment quarter |",
        "| Retention = customer re-purchases | Retention = vehicle had compliant shipment |",
        "| Period = calendar month | Period = operational quarter |",
        "",
        "**Rationale:** In retail, cohort analysis reveals whether recently acquired customers",
        "retain buying behaviour over time. In ColdChainGuard, the analogous question is:",
        "'Do vehicles first deployed in the same quarter maintain compliance performance?'",
        "This reveals fleet quality trends, helps identify deteriorating cohorts early, and",
        "supports targeted maintenance scheduling.",
        "",
        "## Vehicle Compliance-Retention Cohort Matrix",
        "",
        "Rows = quarter in which each vehicle made its first shipment.",
        "Columns = operational quarter offset (Q+0 = debut quarter).",
        "Cell value = fraction of cohort vehicles that had at least one COMPLIANT shipment.",
        "",
    ]

    if not matrix.empty:
        lines.append("| Cohort | Cohort Size | " + " | ".join(matrix.columns) + " |")
        lines.append("|--------|-------------|" + "|".join(["---"] * matrix.shape[1]) + "|")
        for idx in matrix.index:
            sz = cohort_sizes.get(idx, "?")
            vals = " | ".join(
                f"{v:.0%}" if not np.isnan(v) else "-"
                for v in matrix.loc[idx]
            )
            lines.append(f"| {idx} | {sz} | {vals} |")
    else:
        lines.append("*No multi-quarter data available.*")

    lines += [
        "",
        "## Key Insights",
        "",
    ]
    for ins in insights:
        lines.append(f"- {ins}")

    lines += [
        "",
        "## Sensor Calibration Survival",
        "",
        "Rows = month sensors were installed. Columns = fraction with valid calibration",
        "after 1, 3, 6, 12 months from installation.",
        "",
    ]
    if not survival.empty:
        cols = [c for c in survival.columns if c.startswith("valid_at_")]
        hdr = "| Cohort | Size | " + " | ".join(c.replace("valid_at_", "M") for c in cols) + " |"
        lines.append(hdr)
        lines.append("|--------|------|" + "|".join(["---"] * len(cols)) + "|")
        for _, row in survival.iterrows():
            vals = " | ".join(
                f"{row[c]:.0%}" if pd.notna(row[c]) else "-"
                for c in cols
            )
            lines.append(f"| {row['cohort_month']} | {row['cohort_size']} | {vals} |")

    lines += [
        "",
        "## Outputs",
        "",
        "- `vehicle_cohort_matrix.csv` — retention rates by cohort and quarter",
        "- `sensor_survival_matrix.csv` — calibration survival by installation cohort",
        "- `cohort_heatmap_vehicle.png` — vehicle retention heatmap",
        "- `cohort_heatmap_sensor.png` — sensor survival heatmap",
        "",
        "## Operational Use",
        "",
        "1. Cohorts with declining Q+1/Q+2 retention → schedule proactive maintenance",
        "2. Sensor cohorts with low M06 survival → accelerate recalibration programme",
        "3. Compliance-retention trend across all cohorts → measure systemic improvement",
    ]

    with open(os.path.join(OUT_DIR, "cohort_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("     Saved: cohort_report.md")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("COLDCHAINGUARD -- DAY 9: COHORT & RETENTION ANALYSIS")
    print("Vehicle Compliance-Retention and Sensor Survival Cohorts")
    print("=" * 60)

    master, vehicles, sensors, cals = load_data()

    matrix, cohort_sizes, pivot = vehicle_cohort_analysis(master, vehicles)
    survival = sensor_survival_cohort(sensors, cals)

    plot_heatmap(
        matrix,
        "Vehicle Compliance-Retention Cohort\n"
        "(fraction of vehicles with >=1 compliant shipment per quarter)",
        os.path.join(OUT_DIR, "cohort_heatmap_vehicle.png"),
    )
    plot_survival_heatmap(survival, os.path.join(OUT_DIR, "cohort_heatmap_sensor.png"))

    insights = compute_insights(matrix, cohort_sizes)
    write_report(matrix, cohort_sizes, survival, insights)

    print("\n" + "=" * 60)
    print("DAY 9 COHORT & RETENTION COMPLETE")
    print(f"  Outputs: {OUT_DIR}/")
    for f in sorted(os.listdir(OUT_DIR)):
        print(f"    {f}")
    print("=" * 60)


if __name__ == "__main__":
    main()
