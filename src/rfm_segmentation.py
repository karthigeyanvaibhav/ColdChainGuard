"""
src/rfm_segmentation.py
ColdChainGuard - Day 3: Operational RFM-Based Asset Segmentation

Entity:   VEHICLE (vehicle_id)
R = Recency   - Days since vehicle's most recent shipment departure
F = Frequency - Number of shipments handled
M = Volume    - Total product quantity transported

Note on M adaptation:
  The standard RFM 'Monetary' dimension uses transaction value.
  ColdChainGuard does not record revenue per shipment.
  M is therefore adapted to 'transported product volume' (sum of
  batch_quantity across all shipments for a vehicle).
  This is explicitly documented and is a valid adaptation for
  asset/operational segmentation in cold-chain logistics.

Scoring:
  Quintile-based (1-5) scoring where dataset size supports it.
  For R: lower recency days = better score (score=5 is most recent).
  For F: higher frequency = higher score.
  For M: higher volume = higher score.
  RFM_score = R_score + F_score + M_score  (max 15, min 3)

Segments (derived from RFM_score):
  Champions (13-15):        Highest activity, most reliable assets
  Loyal Assets (10-12):     Frequently active, good volume
  Active Assets (7-9):      Moderate activity
  At-Risk Assets (4-6):     Low recent activity
  Low-Activity Assets (3):  Minimal or no recent shipments

Outputs:
  data/segmentation/
    rfm_vehicle_segments.csv
    rfm_summary.csv
    rfm_segment_distribution.csv
    rfm_segment_distribution.png
    rfm_scatter.png
    rfm_scores.png
    rfm_insights.md
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
import matplotlib.cm as cm
from sqlalchemy import create_engine, text

# ==========================================================
# PATHS
# ==========================================================
DB_URL = "postgresql+psycopg://postgres:1322@localhost:5432/coldchainguard"
SEG_DIR = os.path.join(PROJECT_ROOT, "data", "segmentation")
RAW_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
os.makedirs(SEG_DIR, exist_ok=True)

PLOT_STYLE = {
    "axes.spines.top":   False,
    "axes.spines.right": False,
    "axes.grid":         True,
    "grid.alpha":        0.35,
    "figure.dpi":        120,
    "font.size":         11,
}
plt.rcParams.update(PLOT_STYLE)

SEGMENT_COLORS = {
    "Champions":          "#27ae60",
    "Loyal Assets":       "#2ecc71",
    "Active Assets":      "#f39c12",
    "At-Risk Assets":     "#e67e22",
    "Low-Activity Assets":"#e74c3c",
}


# ==========================================================
# LOAD DATA
# ==========================================================
def load_data():
    """Load vehicles, shipments and product_batches from PostgreSQL or CSV."""
    try:
        engine = create_engine(DB_URL, pool_pre_ping=True)
        with engine.connect() as conn:
            vehicles  = pd.read_sql("SELECT * FROM vehicles", conn)
            shipments = pd.read_sql("SELECT * FROM shipments", conn)
            batches   = pd.read_sql("SELECT * FROM product_batches", conn)
        print("[OK] Loaded from PostgreSQL.")
        source = "PostgreSQL"
    except Exception as e:
        print(f"[WARN] DB unavailable ({e}) -- loading from CSV.")
        source = "CSV"
        vehicles  = pd.read_csv(os.path.join(RAW_DIR, "vehicles.csv"))
        shipments = pd.read_csv(os.path.join(RAW_DIR, "shipments.csv"))
        batches   = pd.read_csv(os.path.join(RAW_DIR, "product_batches.csv"))

    # Parse dates
    for col in ["departure_time", "arrival_time"]:
        if col in shipments.columns:
            shipments[col] = pd.to_datetime(shipments[col], errors="coerce")

    print(f"  Vehicles: {len(vehicles)}, Shipments: {len(shipments)}, Batches: {len(batches)}")
    return vehicles, shipments, batches, source


# ==========================================================
# CALCULATE RFM VALUES
# ==========================================================
def calculate_rfm(vehicles, shipments, batches):
    print("\n[RFM 1] Calculating RFM values...")

    # Join shipments with product batches to get quantity
    ship_batch = shipments.merge(
        batches[["batch_id", "quantity"]],
        on="batch_id",
        how="left"
    )

    # Reference date: latest departure date in dataset
    ref_date = shipments["departure_time"].max()
    print(f"         Reference date: {ref_date.date()}")

    # Aggregate per vehicle
    rfm_active = (
        ship_batch.groupby("vehicle_id")
        .agg(
            last_shipment=("departure_time", "max"),
            frequency=("shipment_id", "count"),
            total_volume=("quantity", "sum"),
        )
        .reset_index()
    )

    rfm_active["recency_days"] = (
        ref_date - rfm_active["last_shipment"]
    ).dt.days.fillna(9999).astype(int)

    rfm_active["total_volume"] = rfm_active["total_volume"].fillna(0).astype(int)

    # Add vehicles with zero shipments
    all_vehicle_ids = set(vehicles["vehicle_id"].tolist())
    active_ids      = set(rfm_active["vehicle_id"].tolist())
    inactive_ids    = all_vehicle_ids - active_ids

    if inactive_ids:
        print(f"         Vehicles with no shipments: {len(inactive_ids)} -- included with R=max+1, F=0, M=0")
        max_recency = int(rfm_active["recency_days"].max()) if not rfm_active.empty else 0
        inactive_rows = pd.DataFrame({
            "vehicle_id":   list(inactive_ids),
            "last_shipment": pd.NaT,
            "frequency":    0,
            "total_volume": 0,
            "recency_days": max_recency + 1,
        })
        rfm_active = pd.concat([rfm_active, inactive_rows], ignore_index=True)

    rfm_df = rfm_active.merge(
        vehicles[["vehicle_id", "vehicle_type", "capacity_kg"]],
        on="vehicle_id",
        how="left"
    )

    print(f"         Vehicles with shipments: {len(active_ids)}")
    print(f"         Total vehicles in RFM:   {len(rfm_df)}")
    return rfm_df, ref_date


# ==========================================================
# SCORE RFM (QUINTILE-BASED)
# ==========================================================
def score_rfm(rfm_df):
    print("\n[RFM 2] Scoring RFM dimensions...")

    n = len(rfm_df)
    # Use quintiles if >=25 distinct vehicles, else use tertiles, else binary
    if n >= 25:
        q = 5
        labels = [1, 2, 3, 4, 5]
        method_desc = "quintile (5-level)"
    elif n >= 10:
        q = 3
        labels = [1, 2, 3]
        method_desc = "tertile (3-level)"
    else:
        q = 2
        labels = [1, 2]
        method_desc = "binary (2-level)"

    print(f"         Scoring method: {method_desc} (n={n})")

    def safe_qcut(series, q, labels, reverse=False):
        """Apply pd.qcut with duplicate edge handling; reverse for Recency."""
        try:
            if reverse:
                # Lower recency = better = higher score
                scored = pd.qcut(series, q=q, labels=list(reversed(labels)), duplicates="drop")
            else:
                scored = pd.qcut(series, q=q, labels=labels, duplicates="drop")
            return scored.astype(int)
        except Exception:
            # Fallback: rank-based percentile
            rank = series.rank(method="first", ascending=not reverse)
            pct  = rank / len(rank)
            scored = np.ceil(pct * len(labels)).astype(int).clip(1, len(labels))
            return scored

    rfm_df = rfm_df.copy()
    rfm_df["R_score"] = safe_qcut(rfm_df["recency_days"],  q, labels, reverse=True)
    rfm_df["F_score"] = safe_qcut(rfm_df["frequency"],     q, labels, reverse=False)
    rfm_df["M_score"] = safe_qcut(rfm_df["total_volume"],  q, labels, reverse=False)

    # Vehicles with zero frequency get minimum scores
    rfm_df.loc[rfm_df["frequency"] == 0, ["F_score", "M_score"]] = 1

    rfm_df["RFM_score"] = rfm_df["R_score"] + rfm_df["F_score"] + rfm_df["M_score"]

    max_score = len(labels) * 3
    print(f"         RFM score range: {rfm_df['RFM_score'].min()} - {rfm_df['RFM_score'].max()} (max {max_score})")
    return rfm_df, max_score


# ==========================================================
# ASSIGN SEGMENTS
# ==========================================================
def assign_segments(rfm_df, max_score):
    print("\n[RFM 3] Assigning segments...")

    # Derive thresholds proportionally from max_score
    t1 = round(max_score * 0.87)  # top 13% -> Champions
    t2 = round(max_score * 0.67)  # Loyal
    t3 = round(max_score * 0.47)  # Active
    t4 = round(max_score * 0.27)  # At-Risk
    # below t4 -> Low-Activity

    def classify(score):
        if score >= t1:
            return "Champions"
        elif score >= t2:
            return "Loyal Assets"
        elif score >= t3:
            return "Active Assets"
        elif score >= t4:
            return "At-Risk Assets"
        else:
            return "Low-Activity Assets"

    rfm_df = rfm_df.copy()
    rfm_df["RFM_segment"] = rfm_df["RFM_score"].apply(classify)

    dist = rfm_df["RFM_segment"].value_counts()
    for seg, count in dist.items():
        pct = round(count / len(rfm_df) * 100, 1)
        print(f"         {seg:<25} {count:>4} vehicles ({pct}%)")

    return rfm_df


# ==========================================================
# SAVE OUTPUTS
# ==========================================================
def save_outputs(rfm_df):
    print("\n[RFM 4] Saving outputs...")

    # Full RFM dataset
    out_cols = ["vehicle_id", "vehicle_type", "capacity_kg",
                "last_shipment", "recency_days", "frequency", "total_volume",
                "R_score", "F_score", "M_score", "RFM_score", "RFM_segment"]
    out_cols = [c for c in out_cols if c in rfm_df.columns]
    rfm_df[out_cols].sort_values("RFM_score", ascending=False).to_csv(
        os.path.join(SEG_DIR, "rfm_vehicle_segments.csv"), index=False
    )

    # Summary per segment
    summary = (
        rfm_df.groupby("RFM_segment")
        .agg(
            vehicle_count=("vehicle_id", "count"),
            avg_recency_days=("recency_days", "mean"),
            avg_frequency=("frequency", "mean"),
            avg_volume=("total_volume", "mean"),
            avg_rfm_score=("RFM_score", "mean"),
            total_volume=("total_volume", "sum"),
        )
        .round(2)
        .reset_index()
        .sort_values("avg_rfm_score", ascending=False)
    )
    summary.to_csv(os.path.join(SEG_DIR, "rfm_summary.csv"), index=False)

    # Segment distribution
    dist = rfm_df["RFM_segment"].value_counts().reset_index()
    dist.columns = ["segment", "count"]
    dist["percentage"] = (dist["count"] / dist["count"].sum() * 100).round(2)
    dist.to_csv(os.path.join(SEG_DIR, "rfm_segment_distribution.csv"), index=False)

    print(f"         rfm_vehicle_segments.csv: {len(rfm_df)} rows")
    print(f"         rfm_summary.csv: {len(summary)} segments")
    return summary, dist


# ==========================================================
# VISUALIZATIONS
# ==========================================================
def visualize(rfm_df, summary, dist):
    print("\n[RFM 5] Generating visualizations...")

    # --- Plot 1: Segment Distribution Bar ---
    fig, ax = plt.subplots(figsize=(10, 6))
    seg_order = ["Champions", "Loyal Assets", "Active Assets",
                 "At-Risk Assets", "Low-Activity Assets"]
    seg_order = [s for s in seg_order if s in dist["segment"].values]
    dist_sorted = dist.set_index("segment").reindex(seg_order).dropna().reset_index()

    colors = [SEGMENT_COLORS.get(s, "#95a5a6") for s in dist_sorted["segment"]]
    bars = ax.bar(dist_sorted["segment"], dist_sorted["count"],
                  color=colors, edgecolor="white", linewidth=0.8)
    ax.bar_label(bars, fmt="%d", padding=4, fontsize=11)
    ax.set_title("Operational RFM Asset Segmentation\n(Vehicle Count per Segment)",
                 fontsize=13, fontweight="bold")
    ax.set_xlabel("Segment")
    ax.set_ylabel("Number of Vehicles")
    ax.tick_params(axis="x", rotation=20)
    plt.tight_layout()
    plt.savefig(os.path.join(SEG_DIR, "rfm_segment_distribution.png"), bbox_inches="tight")
    plt.close()

    # --- Plot 2: RFM Scatter (Frequency vs Volume, coloured by segment) ---
    fig, ax = plt.subplots(figsize=(10, 7))
    for seg, grp in rfm_df.groupby("RFM_segment"):
        color = SEGMENT_COLORS.get(seg, "#95a5a6")
        ax.scatter(grp["frequency"], grp["total_volume"],
                   c=color, label=seg, alpha=0.7, s=60, edgecolors="white", linewidth=0.5)
    ax.set_title("Vehicle RFM Scatter: Frequency vs Total Volume",
                 fontsize=13, fontweight="bold")
    ax.set_xlabel("Shipment Frequency (F)")
    ax.set_ylabel("Total Product Volume Transported (M)")
    ax.legend(loc="upper left", fontsize=9, framealpha=0.85)
    plt.tight_layout()
    plt.savefig(os.path.join(SEG_DIR, "rfm_scatter.png"), bbox_inches="tight")
    plt.close()

    # --- Plot 3: RFM Score Distribution ---
    fig, axes = plt.subplots(1, 3, figsize=(14, 5))
    fig.suptitle("RFM Score Distributions by Dimension", fontsize=13, fontweight="bold")
    for ax, (col, label, color) in zip(axes, [
        ("R_score", "Recency Score (R)", "#3498db"),
        ("F_score", "Frequency Score (F)", "#27ae60"),
        ("M_score", "Volume Score (M)",   "#e67e22"),
    ]):
        if col not in rfm_df.columns:
            ax.set_visible(False)
            continue
        vc = rfm_df[col].value_counts().sort_index()
        ax.bar(vc.index.astype(str), vc.values, color=color, edgecolor="white")
        ax.set_title(label)
        ax.set_xlabel("Score")
        ax.set_ylabel("Vehicle Count")
    plt.tight_layout()
    plt.savefig(os.path.join(SEG_DIR, "rfm_scores.png"), bbox_inches="tight")
    plt.close()

    print(f"         3 plots saved to data/segmentation/")


# ==========================================================
# GENERATE INSIGHTS
# ==========================================================
def generate_insights(rfm_df, summary, ref_date):
    print("\n[RFM 6] Generating RFM insights...")

    total = len(rfm_df)
    dist = rfm_df["RFM_segment"].value_counts()

    # Find key segments
    largest_seg = dist.idxmax()
    largest_n   = int(dist.max())

    # Highest frequency segment (from summary)
    if "avg_frequency" in summary.columns:
        hf_row = summary.loc[summary["avg_frequency"].idxmax()]
        hf_seg = hf_row["RFM_segment"]
        hf_val = round(float(hf_row["avg_frequency"]), 1)
    else:
        hf_seg = hf_val = "N/A"

    # Highest volume segment
    if "avg_volume" in summary.columns:
        hv_row = summary.loc[summary["avg_volume"].idxmax()]
        hv_seg = hv_row["RFM_segment"]
        hv_val = round(float(hv_row["avg_volume"]), 0)
    else:
        hv_seg = hv_val = "N/A"

    # Least active
    if "At-Risk Assets" in dist.index or "Low-Activity Assets" in dist.index:
        low_n = int(dist.get("Low-Activity Assets", 0)) + int(dist.get("At-Risk Assets", 0))
    else:
        low_n = 0

    lines = [
        "# ColdChainGuard -- Operational RFM Asset Segmentation Insights",
        "",
        "## Methodology",
        "Entity segmented: **Vehicle** (vehicle_id)",
        "",
        "| Dimension | Definition | Direction |",
        "|-----------|-----------|-----------|",
        "| R (Recency) | Days since vehicle's most recent shipment | Lower = better |",
        "| F (Frequency) | Number of shipments handled | Higher = better |",
        "| M (Volume) | Total product quantity transported | Higher = better |",
        "",
        "> **Note on M adaptation:** Standard RFM uses monetary transaction value.",
        "> ColdChainGuard does not record per-shipment revenue.",
        "> M is adapted to transported product volume (sum of batch_quantity).",
        "> This is a valid and documented adaptation for asset/operational segmentation.",
        "",
        f"Reference date: {ref_date.date()}",
        f"Total vehicles analysed: **{total}**",
        "",
        "## Segment Summary",
    ]

    seg_order = ["Champions", "Loyal Assets", "Active Assets",
                 "At-Risk Assets", "Low-Activity Assets"]

    for seg in seg_order:
        n = int(dist.get(seg, 0))
        pct = round(n / total * 100, 1)
        row = summary[summary["RFM_segment"] == seg]
        if not row.empty:
            avg_r = round(float(row["avg_recency_days"].values[0]), 1)
            avg_f = round(float(row["avg_frequency"].values[0]), 1)
            avg_m = round(float(row["avg_volume"].values[0]), 0)
        else:
            avg_r = avg_f = avg_m = "N/A"
        lines.append(f"- **{seg}**: {n} vehicles ({pct}%) | "
                     f"Avg Recency: {avg_r} days | "
                     f"Avg Frequency: {avg_f} shipments | "
                     f"Avg Volume: {avg_m} units")

    lines += [
        "",
        "## Key Findings",
        f"- **Largest segment**: {largest_seg} ({largest_n} vehicles, "
        f"{round(largest_n/total*100,1)}% of fleet)",
        f"- **Highest-frequency segment**: {hf_seg} (avg {hf_val} shipments/vehicle)",
        f"- **Highest-volume segment**: {hv_seg} (avg {hv_val} units/vehicle)",
        f"- **Low / at-risk vehicles**: {low_n} vehicles need operational attention",
        "",
        "## Operational Implications for Cold-Chain",
        "- **Champions** are the fleet backbone: prioritise for preventive maintenance",
        "  and compliance certification renewal.",
        "- **Loyal Assets** should be monitored for any drop in frequency,",
        "  which could indicate mechanical issues or route reassignment.",
        "- **Active Assets** represent normal operational utilisation.",
        "  Standard compliance monitoring is appropriate.",
        "- **At-Risk Assets** show declining frequency.",
        "  Investigate whether vehicles are awaiting maintenance or have been reassigned.",
        "- **Low-Activity Assets** have minimal recent shipments.",
        "  Consider whether these vehicles are retired, under repair,",
        "  or require compliance certificate renewal before reactivation.",
        "",
        "## Compliance Intersection",
        "Vehicles in lower segments (At-Risk, Low-Activity) are more likely to have:",
        "- Expired sensor calibration certificates (due to inactivity)",
        "- Outdated compliance records",
        "- Higher per-shipment excursion risk (equipment degradation during idle periods)",
        "",
        "Cross-referencing RFM segments with compliance_results can identify",
        "high-risk vehicles requiring immediate audit attention.",
    ]

    text = "\n".join(lines)
    with open(os.path.join(SEG_DIR, "rfm_insights.md"), "w", encoding="utf-8") as f:
        f.write(text)

    print(f"         rfm_insights.md saved.")


# ==========================================================
# MAIN
# ==========================================================
def main():
    print("=" * 60)
    print("COLDCHAINGUARD - DAY 3 RFM ASSET SEGMENTATION")
    print("=" * 60)
    print("")
    print("Segmentation entity: VEHICLE")
    print("R = Recency   (days since last shipment)")
    print("F = Frequency (shipment count)")
    print("M = Volume    (total quantity transported)")
    print("")

    vehicles, shipments, batches, source = load_data()
    rfm_df, ref_date = calculate_rfm(vehicles, shipments, batches)
    rfm_df, max_score = score_rfm(rfm_df)
    rfm_df = assign_segments(rfm_df, max_score)
    summary, dist = save_outputs(rfm_df)
    visualize(rfm_df, summary, dist)
    generate_insights(rfm_df, summary, ref_date)

    print("")
    print("=" * 60)
    print("RFM SEGMENTATION COMPLETE -- outputs in data/segmentation/")
    print("=" * 60)
    for f in sorted(os.listdir(SEG_DIR)):
        print(f"  {f}")
    print("=" * 60)


if __name__ == "__main__":
    main()
