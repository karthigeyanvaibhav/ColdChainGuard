"""
src/predictive_model.py
ColdChainGuard - Day 4: Predictive Analytics

Trains machine-learning models to predict:
  1. Compliance outcome (Compliant / Non-Compliant)
  2. Temperature excursion risk score per shipment

Models: Logistic Regression, Random Forest, Gradient Boosting
Evaluation: Accuracy, F1, ROC-AUC, Confusion Matrix, Feature Importance
Output: data/predictions/
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

from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import (
    accuracy_score, f1_score, roc_auc_score, classification_report,
    confusion_matrix, ConfusionMatrixDisplay, roc_curve
)
from sklearn.pipeline import Pipeline
import joblib

PRED_DIR = os.path.join(PROJECT_ROOT, "data", "predictions")
ETL_DIR  = os.path.join(PROJECT_ROOT, "data", "etl")
os.makedirs(PRED_DIR, exist_ok=True)
os.makedirs(os.path.join(PRED_DIR, "models"), exist_ok=True)

PLOT_STYLE = {
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "figure.dpi": 120,
    "font.size": 11,
}
plt.rcParams.update(PLOT_STYLE)


# ==========================================================
# LOAD DATA
# ==========================================================
def load_data():
    master_csv = os.path.join(ETL_DIR, "master_shipments.csv")
    if not os.path.exists(master_csv):
        raise FileNotFoundError("Run src/star_schema.py first to generate master_shipments.csv")

    df = pd.read_csv(master_csv)
    print(f"[OK] Loaded master_shipments.csv: {len(df)} rows, {len(df.columns)} columns")
    return df


# ==========================================================
# FEATURE ENGINEERING
# ==========================================================
def build_features(df):
    print("\n[ML 1] Building features...")

    feature_cols = [
        "avg_temperature_c",
        "stddev_temperature_c",
        "obs_min_temp",
        "obs_max_temp",
        "missing_readings",
        "offline_readings",
        "avg_battery_level",
        "avg_signal_strength",
        "total_delay_minutes",
        "traffic_delay_events",
        "route_deviation_events",
        "missing_signatures",
        "signature_rate_pct",
        "total_handovers",
        "total_events",
        "journey_duration_min",
        "batch_quantity",
    ]

    # Add product_type as binary flag
    if "product_type" in df.columns:
        df = df.copy()
        df["is_frozen"] = (df["product_type"] == "Frozen").astype(int)
        feature_cols.append("is_frozen")

    # Temperature range feature
    if "obs_max_temp" in df.columns and "obs_min_temp" in df.columns:
        df["temp_range"] = df["obs_max_temp"] - df["obs_min_temp"]
        feature_cols.append("temp_range")

    # Missing rate feature
    if "missing_readings" in df.columns and "total_readings" in df.columns:
        df["missing_rate"] = df["missing_readings"] / (df["total_readings"].replace(0, 1))
        feature_cols.append("missing_rate")

    # Use only available columns
    feature_cols = [c for c in feature_cols if c in df.columns]
    X = df[feature_cols].copy()

    # Fill remaining NaN with column medians
    X = X.fillna(X.median(numeric_only=True))

    print(f"         Features: {len(feature_cols)}")
    print(f"         Feature list: {', '.join(feature_cols)}")
    return X, feature_cols, df


def build_target(df):
    """Binary target: 1 = Compliant, 0 = Non-Compliant or Review"""
    if "overall_compliance" not in df.columns:
        raise ValueError("overall_compliance column missing from master dataset")

    y = (df["overall_compliance"].str.strip() == "Compliant").astype(int)
    print(f"         Target distribution: Compliant={y.sum()} ({y.mean()*100:.1f}%), "
          f"Non-Compliant/Review={len(y)-y.sum()} ({(1-y.mean())*100:.1f}%)")
    return y


# ==========================================================
# TRAIN MODELS
# ==========================================================
def train_models(X, y):
    print("\n[ML 2] Training models...")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )
    print(f"         Train: {len(X_train)}, Test: {len(X_test)}")

    pipelines = {
        "Logistic Regression": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(max_iter=1000, random_state=42, C=1.0))
        ]),
        "Random Forest": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", RandomForestClassifier(n_estimators=150, max_depth=8,
                                           random_state=42, n_jobs=-1))
        ]),
        "Gradient Boosting": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", GradientBoostingClassifier(n_estimators=100, max_depth=4,
                                               learning_rate=0.1, random_state=42))
        ]),
    }

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    results = {}

    for name, pipe in pipelines.items():
        pipe.fit(X_train, y_train)
        y_pred  = pipe.predict(X_test)
        y_proba = pipe.predict_proba(X_test)[:, 1]

        cv_scores = cross_val_score(pipe, X, y, cv=cv, scoring="f1", n_jobs=-1)

        acc   = accuracy_score(y_test, y_pred)
        f1    = f1_score(y_test, y_pred, zero_division=0)
        auc   = roc_auc_score(y_test, y_proba)
        cv_f1 = cv_scores.mean()

        results[name] = {
            "pipeline": pipe,
            "y_pred":  y_pred,
            "y_proba": y_proba,
            "accuracy": round(acc, 4),
            "f1": round(f1, 4),
            "roc_auc": round(auc, 4),
            "cv_f1_mean": round(cv_f1, 4),
            "cv_f1_std": round(cv_scores.std(), 4),
        }
        print(f"         {name:<22} Acc={acc:.3f}  F1={f1:.3f}  AUC={auc:.3f}  "
              f"CV-F1={cv_f1:.3f}(+-{cv_scores.std():.3f})")

    # Save pipelines
    for name, r in results.items():
        fname = name.lower().replace(" ", "_") + ".joblib"
        joblib.dump(r["pipeline"], os.path.join(PRED_DIR, "models", fname))

    return results, X_train, X_test, y_train, y_test


# ==========================================================
# BEST MODEL ANALYSIS
# ==========================================================
def analyse_best_model(results, X, y, X_test, y_test, feature_cols, df):
    print("\n[ML 3] Detailed analysis of best model...")

    best_name = max(results, key=lambda k: results[k]["roc_auc"])
    best      = results[best_name]
    pipe      = best["pipeline"]
    print(f"         Best model: {best_name} (AUC={best['roc_auc']})")

    # --- Feature importance ---
    clf = pipe.named_steps["clf"]
    if hasattr(clf, "feature_importances_"):
        importances = clf.feature_importances_
    elif hasattr(clf, "coef_"):
        importances = np.abs(clf.coef_[0])
    else:
        importances = np.ones(len(feature_cols))

    fi_df = pd.DataFrame({
        "feature": feature_cols,
        "importance": importances
    }).sort_values("importance", ascending=False)
    fi_df.to_csv(os.path.join(PRED_DIR, "feature_importance.csv"), index=False)

    fig, ax = plt.subplots(figsize=(9, 6))
    top = fi_df.head(12)
    colors = ["#2196F3" if i < 3 else "#90CAF9" for i in range(len(top))]
    bars = ax.barh(top["feature"][::-1], top["importance"][::-1], color=colors[::-1])
    ax.set_title(f"Feature Importance ({best_name})", fontsize=13, fontweight="bold")
    ax.set_xlabel("Importance Score")
    plt.tight_layout()
    plt.savefig(os.path.join(PRED_DIR, "feature_importance.png"), bbox_inches="tight")
    plt.close()

    # --- Confusion Matrix ---
    cm = confusion_matrix(y_test, best["y_pred"])
    fig, ax = plt.subplots(figsize=(6, 5))
    disp = ConfusionMatrixDisplay(cm, display_labels=["Non-Compliant", "Compliant"])
    disp.plot(ax=ax, colorbar=False, cmap="Blues")
    ax.set_title(f"Confusion Matrix ({best_name})", fontsize=12, fontweight="bold")
    plt.tight_layout()
    plt.savefig(os.path.join(PRED_DIR, "confusion_matrix.png"), bbox_inches="tight")
    plt.close()

    # --- ROC Curve (all models) ---
    fig, ax = plt.subplots(figsize=(7, 6))
    colors_roc = ["#2196F3", "#27ae60", "#e74c3c"]
    for (name, r), color in zip(results.items(), colors_roc):
        fpr, tpr, _ = roc_curve(y_test, r["y_proba"])
        ax.plot(fpr, tpr, color=color, lw=2,
                label=f"{name} (AUC={r['roc_auc']:.3f})")
    ax.plot([0, 1], [0, 1], "k--", lw=1, alpha=0.5)
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title("ROC Curves — Compliance Prediction", fontsize=13, fontweight="bold")
    ax.legend(loc="lower right", fontsize=9)
    plt.tight_layout()
    plt.savefig(os.path.join(PRED_DIR, "roc_curve.png"), bbox_inches="tight")
    plt.close()

    # --- Apply best model to ALL shipments for risk scores ---
    X_full = df[[c for c in feature_cols if c in df.columns]].fillna(
        df[[c for c in feature_cols if c in df.columns]].median(numeric_only=True)
    )
    risk_scores = pipe.predict_proba(X_full)[:, 1]
    predictions = pipe.predict(X_full)

    pred_df = df[["shipment_id", "vehicle_id", "product_type",
                  "overall_compliance"]].copy() if "shipment_id" in df.columns else df.copy()
    pred_df["predicted_compliant"] = predictions
    pred_df["compliance_probability"] = risk_scores.round(4)
    pred_df["excursion_risk_score"] = (1 - risk_scores).round(4)
    pred_df["risk_tier"] = pd.cut(
        pred_df["excursion_risk_score"],
        bins=[0, 0.25, 0.5, 0.75, 1.0],
        labels=["Low", "Medium", "High", "Critical"]
    )
    pred_df.to_csv(os.path.join(PRED_DIR, "predictions.csv"), index=False)
    print(f"         Risk tiers: {pred_df['risk_tier'].value_counts().to_dict()}")

    return fi_df, best_name, pred_df


# ==========================================================
# MODEL COMPARISON TABLE
# ==========================================================
def save_model_comparison(results):
    rows = []
    for name, r in results.items():
        rows.append({
            "model": name,
            "accuracy": r["accuracy"],
            "f1_score": r["f1"],
            "roc_auc": r["roc_auc"],
            "cv_f1_mean": r["cv_f1_mean"],
            "cv_f1_std": r["cv_f1_std"],
        })
    comp_df = pd.DataFrame(rows).sort_values("roc_auc", ascending=False)
    comp_df.to_csv(os.path.join(PRED_DIR, "model_comparison.csv"), index=False)

    # Bar chart comparison
    fig, axes = plt.subplots(1, 3, figsize=(13, 5))
    fig.suptitle("Model Performance Comparison", fontsize=13, fontweight="bold")
    metrics = [("accuracy", "Accuracy"), ("f1_score", "F1 Score"), ("roc_auc", "ROC-AUC")]
    palette = ["#2196F3", "#27ae60", "#e74c3c"]

    for ax, (metric, title) in zip(axes, metrics):
        bars = ax.bar(comp_df["model"], comp_df[metric], color=palette, edgecolor="white")
        ax.bar_label(bars, fmt="%.3f", padding=3, fontsize=10)
        ax.set_title(title)
        ax.set_ylim(0, 1.1)
        ax.tick_params(axis="x", rotation=20)

    plt.tight_layout()
    plt.savefig(os.path.join(PRED_DIR, "model_comparison.png"), bbox_inches="tight")
    plt.close()

    return comp_df


# ==========================================================
# MAIN
# ==========================================================
def main():
    print("=" * 60)
    print("COLDCHAINGUARD - DAY 4 PREDICTIVE ANALYTICS")
    print("=" * 60)

    df = load_data()
    X, feature_cols, df = build_features(df)
    y = build_target(df)
    results, X_train, X_test, y_train, y_test = train_models(X, y)
    fi_df, best_name, pred_df = analyse_best_model(
        results, X, y, X_test, y_test, feature_cols, df
    )
    comp_df = save_model_comparison(results)

    print("\n" + "=" * 60)
    print("PREDICTIVE MODEL RESULTS")
    print("=" * 60)
    print(comp_df.to_string(index=False))
    print(f"\nBest model: {best_name}")
    print(f"Risk scores saved: {len(pred_df)} shipments")
    print("\nOutputs saved to: data/predictions/")
    for f in sorted(os.listdir(PRED_DIR)):
        if os.path.isfile(os.path.join(PRED_DIR, f)):
            print(f"  {f}")
    print("=" * 60)
    print("DAY 4 PREDICTIVE ANALYTICS COMPLETE")


if __name__ == "__main__":
    main()
