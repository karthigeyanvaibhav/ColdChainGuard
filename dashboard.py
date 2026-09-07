import os
import io
import csv
import uuid
from datetime import datetime
from urllib.parse import quote_plus

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from dash import Dash, html, dcc, Input, Output, State, callback_context
from dash.exceptions import PreventUpdate
import flask


# ==========================================================
# COLDCHAINGUARD DASHBOARD  (Enhanced v2)
# ==========================================================
# New in v2:
#   - CSV fallback when PostgreSQL is unavailable
#   - Interactive dispatcher override form
#   - Radar/spider trade-off chart (Cost × Time × Emissions × Reliability)
#   - PDF download button per shipment
#   - 30-second auto-refresh via dcc.Interval
#   - Flask route to serve PDF files from data/reports/
# ==========================================================


# ==========================================================
# DATABASE CONFIGURATION
# ==========================================================
DB_USER = "postgres"
DB_PASSWORD = os.getenv("COLDCHAINGUARD_DB_PASSWORD", "1322")
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "coldchainguard"

DATABASE_URL = (
    "postgresql+psycopg://"
    f"{quote_plus(DB_USER)}:{quote_plus(DB_PASSWORD)}@"
    f"{DB_HOST}:{DB_PORT}/{DB_NAME}"
)


# ==========================================================
# PROJECT PATHS
# ==========================================================
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_DIR = os.path.join(PROJECT_ROOT, "data")
EXPERIMENT_DIR = os.path.join(DATA_DIR, "experiments")
REPORTS_DIR = os.path.join(DATA_DIR, "reports")
RAW_DIR = os.path.join(DATA_DIR, "raw")

COMPLIANCE_CSV = os.path.join(DATA_DIR, "compliance_results.csv")
TRADEOFF_FILE = os.path.join(EXPERIMENT_DIR, "tradeoff_summary.csv")
OVERRIDE_FILE = os.path.join(EXPERIMENT_DIR, "dispatcher_override_history.csv")

os.makedirs(REPORTS_DIR, exist_ok=True)


# ==========================================================
# DATABASE / CSV LOADING WITH FALLBACK
# ==========================================================
DB_AVAILABLE = False

def load_database_data():
    """Try PostgreSQL first; fall back to CSV files if unavailable."""
    global DB_AVAILABLE

    try:
        from sqlalchemy import create_engine, text as sql_text
        engine = create_engine(
            DATABASE_URL,
            pool_pre_ping=True,
            pool_recycle=1800,
        )
        with engine.connect() as conn:
            compliance = pd.read_sql_query(
                sql_text("SELECT * FROM compliance_results"),
                conn,
            )
            shipments = pd.read_sql_query(
                sql_text("SELECT * FROM shipments"),
                conn,
            )
        DB_AVAILABLE = True
        print("[OK] Connected to PostgreSQL.")
        return compliance, shipments

    except Exception as db_err:
        print(f"[WARN] PostgreSQL unavailable: {db_err}")
        print("[INFO] Falling back to CSV files.")
        DB_AVAILABLE = False

    # ── CSV fallback ──────────────────────────────────────
    if os.path.exists(COMPLIANCE_CSV):
        compliance = pd.read_csv(COMPLIANCE_CSV)
        print(f"[OK] Loaded compliance from CSV ({len(compliance)} rows).")
    else:
        print("[WARN] No compliance_results.csv found -- using empty frame.")
        compliance = pd.DataFrame()

    shipments_csv = os.path.join(RAW_DIR, "shipments.csv")
    if os.path.exists(shipments_csv):
        shipments = pd.read_csv(shipments_csv)
    else:
        shipments = pd.DataFrame()

    return compliance, shipments


def load_experiment_data():
    """Load experiment outputs (always from CSV)."""
    tradeoff = pd.read_csv(TRADEOFF_FILE) if os.path.exists(TRADEOFF_FILE) else pd.DataFrame()
    overrides = pd.read_csv(OVERRIDE_FILE) if os.path.exists(OVERRIDE_FILE) else pd.DataFrame()
    return tradeoff, overrides


# ==========================================================
# SAFE HELPERS
# ==========================================================
def clean_dataframe(df):
    if df.empty:
        return df
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    for col in df.select_dtypes(include=["object", "string"]).columns:
        df[col] = df[col].astype(str).str.strip()
    return df


def ensure_columns(df, required):
    df = df.copy()
    for col, default in required.items():
        if col not in df.columns:
            df[col] = default
    return df


# ==========================================================
# INITIAL DATA LOAD
# ==========================================================
compliance_df, shipments_df = load_database_data()
compliance_df = clean_dataframe(compliance_df)
shipments_df = clean_dataframe(shipments_df)

compliance_df = ensure_columns(compliance_df, {
    "shipment_id": "Unknown",
    "overall_compliance": "Review",
    "temperature_status": "Unknown",
    "sensor_reliability": "Unknown",
    "custody_evidence_quality": "Unknown",
    "route_reliability": "Unknown",
    "route_status": "Unknown",
})

tradeoff_df, overrides_df = load_experiment_data()
tradeoff_df = clean_dataframe(tradeoff_df)
overrides_df = clean_dataframe(overrides_df)


# ==========================================================
# DASH APP
# ==========================================================
app = Dash(__name__, suppress_callback_exceptions=True)
app.title = "ColdChainGuard"
server = app.server   # expose Flask server


# ==========================================================
# FLASK ROUTE — serve PDF audit reports
# ==========================================================
@server.route("/reports/<path:filename>")
def serve_report(filename):
    """Serve a PDF audit report from data/reports/."""
    return flask.send_from_directory(REPORTS_DIR, filename)


# ==========================================================
# GLOBAL STYLES
# ==========================================================
PAGE_STYLE = {
    "fontFamily": "Arial, sans-serif",
    "backgroundColor": "#f4f6f8",
    "minHeight": "100vh",
    "paddingBottom": "50px",
}

HEADER_STYLE = {
    "padding": "30px 20px 20px 20px",
    "textAlign": "center",
    "background": "linear-gradient(135deg, #1a73e8 0%, #0d47a1 100%)",
    "color": "white",
    "marginBottom": "10px",
}

SECTION_STYLE = {
    "backgroundColor": "#ffffff",
    "borderRadius": "12px",
    "margin": "16px 20px",
    "padding": "16px",
    "boxShadow": "0 2px 10px rgba(0, 0, 0, 0.06)",
}

CARD_STYLE = {
    "padding": "18px",
    "borderRadius": "12px",
    "backgroundColor": "#ffffff",
    "boxShadow": "0 2px 10px rgba(0, 0, 0, 0.08)",
    "textAlign": "center",
    "flex": "1 1 180px",
    "margin": "8px",
    "minWidth": "160px",
}

GRAPH_STYLE = {"width": "100%", "minHeight": "420px"}

INPUT_STYLE = {
    "width": "100%",
    "padding": "8px 12px",
    "borderRadius": "6px",
    "border": "1px solid #ccc",
    "fontSize": "14px",
    "marginBottom": "10px",
    "boxSizing": "border-box",
}

BTN_STYLE = {
    "backgroundColor": "#1a73e8",
    "color": "white",
    "border": "none",
    "padding": "10px 24px",
    "borderRadius": "6px",
    "cursor": "pointer",
    "fontSize": "15px",
    "marginTop": "4px",
}


# ==========================================================
# CHART HELPERS
# ==========================================================
def kpi_card(title, value, subtitle="", color="#1a73e8"):
    return html.Div([
        html.H4(title, style={"marginBottom": "8px", "fontWeight": "600", "color": "#444"}),
        html.H2(value, style={"margin": "5px 0", "fontSize": "30px", "color": color}),
        html.P(subtitle, style={"margin": "5px 0 0 0", "color": "#666", "fontSize": "13px"}),
    ], style=CARD_STYLE)


def make_count_bar(df, column, title, category_order=None):
    if column not in df.columns:
        counts = pd.DataFrame({"status": ["Unavailable"], "count": [0]})
    else:
        values = df[column].copy().fillna("Unknown").astype(str).str.strip().replace("", "Unknown")
        counts = values.value_counts(dropna=False).reset_index()
        counts.columns = ["status", "count"]
        counts["status"] = counts["status"].astype(str)
        counts["count"] = pd.to_numeric(counts["count"], errors="coerce").fillna(0).astype(int)

        if category_order:
            ordered = [c for c in category_order if c in counts["status"].tolist()]
            ordered += [c for c in counts["status"].tolist() if c not in ordered]
            counts["status"] = pd.Categorical(counts["status"], categories=ordered, ordered=True)
            counts = counts.sort_values("status")
            counts["status"] = counts["status"].astype(str)

    color_map = {
        "Compliant": "#34a853", "Complete": "#34a853", "Reliable": "#34a853",
        "High": "#34a853", "Normal": "#34a853",
        "Warning": "#fbbc04", "Review": "#fbbc04", "Partial": "#fbbc04",
        "Moderate": "#fbbc04", "Delayed": "#fbbc04",
        "Critical": "#ea4335", "Non-Compliant": "#ea4335",
        "Incomplete": "#ea4335", "Low": "#ea4335", "Deviation": "#ea4335",
        "Alert": "#ff6d00",
    }
    bar_colors = [color_map.get(s, "#4285f4") for s in counts["status"].tolist()]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=counts["status"].tolist(),
        y=counts["count"].tolist(),
        text=counts["count"].tolist(),
        textposition="auto",
        marker_color=bar_colors,
        hovertemplate="Status: %{x}<br>Count: %{y}<extra></extra>",
    ))
    max_count = int(counts["count"].max()) if not counts.empty else 0
    upper = max(1, int(max_count * 1.20) + 1)
    fig.update_layout(
        title=title,
        xaxis_title="Status",
        yaxis_title="Count",
        yaxis=dict(range=[0, upper], dtick=max(1, upper // 5)),
        template="plotly_white",
        margin=dict(l=55, r=30, t=70, b=65),
        hovermode="x unified",
    )
    return fig


def make_compliance_pie(df):
    if "overall_compliance" not in df.columns:
        counts = pd.DataFrame({"status": ["Review"], "count": [0]})
    else:
        values = df["overall_compliance"].fillna("Review").astype(str).str.strip().replace("", "Review")
        counts = values.value_counts().reset_index()
        counts.columns = ["status", "count"]

    color_map = {"Compliant": "#34a853", "Non-Compliant": "#ea4335", "Review": "#fbbc04"}
    colors = [color_map.get(s, "#4285f4") for s in counts["status"]]

    fig = go.Figure(data=[go.Pie(
        labels=counts["status"],
        values=counts["count"],
        hole=0.38,
        textinfo="percent+label",
        marker=dict(colors=colors),
        hovertemplate="%{label}<br>Shipments: %{value}<br>%{percent}<extra></extra>",
    )])
    fig.update_layout(
        title="Overall Compliance Distribution",
        template="plotly_white",
        margin=dict(l=30, r=30, t=70, b=30),
        legend=dict(orientation="h", y=-0.05),
    )
    return fig


def make_exception_chart(df):
    checks = [
        ("Temperature", "temperature_status", ["Warning", "Critical"]),
        ("Sensor", "sensor_reliability", ["Review", "Partial"]),
        ("Custody", "custody_evidence_quality", ["Incomplete"]),
        ("Route", "route_reliability", ["Moderate", "Low"]),
    ]
    labels, counts = [], []
    for label, col, bad_vals in checks:
        labels.append(label)
        if col in df.columns:
            series = df[col].fillna("Unknown").astype(str).str.strip()
            counts.append(int(series.isin(bad_vals).sum()))
        else:
            counts.append(0)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=labels, y=counts,
        text=counts, textposition="auto",
        marker_color=["#ea4335", "#fbbc04", "#ff6d00", "#4285f4"],
        hovertemplate="Exception: %{x}<br>Affected: %{y}<extra></extra>",
    ))
    upper = max(1, int(max(counts) * 1.20) + 1) if counts else 1
    fig.update_layout(
        title="Failure / Exception Monitoring",
        xaxis_title="Exception Type",
        yaxis_title="Affected Shipments",
        yaxis=dict(range=[0, upper], dtick=max(1, upper // 5)),
        template="plotly_white",
        margin=dict(l=55, r=30, t=70, b=65),
        hovermode="x unified",
    )
    return fig


def make_radar_tradeoff():
    """4-axis radar chart: Cost × Time × Emissions × Reliability."""
    if tradeoff_df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="Trade-off data unavailable<br>Run: python src/tradeoff_experiment.py",
            x=0.5, y=0.5, xref="paper", yref="paper",
            showarrow=False, font=dict(size=16),
        )
        fig.update_layout(title="Cost × Time × Emissions × Reliability Trade-off", template="plotly_white")
        return fig

    # Expected columns: strategy, cost_score, time_score, emissions_score, reliability_score
    # Fall back gracefully if only overall_score is present
    cols = tradeoff_df.columns.tolist()
    strategies = tradeoff_df["strategy"].astype(str).tolist() if "strategy" in cols else []

    categories = ["Cost", "Time", "Emissions", "Reliability", "Cost"]  # close radar loop
    fig = go.Figure()

    score_cols = {
        "Cost": "cost_score",
        "Time": "time_score",
        "Emissions": "emissions_score",
        "Reliability": "reliability_score",
    }

    for _, row in tradeoff_df.iterrows():
        values = []
        for dim, col in score_cols.items():
            if col in row.index:
                v = pd.to_numeric(row[col], errors="coerce")
                values.append(float(v) if pd.notna(v) else 50.0)
            elif "overall_score" in row.index:
                # Use overall_score with slight variation as placeholder
                base = pd.to_numeric(row["overall_score"], errors="coerce")
                base = float(base) if pd.notna(base) else 50.0
                offsets = {"Cost": 0, "Time": 5, "Emissions": -5, "Reliability": 10}
                values.append(max(0, min(100, base + offsets[dim])))
            else:
                values.append(50.0)

        values.append(values[0])  # close the radar loop
        strategy_name = str(row.get("strategy", "Strategy"))

        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=categories,
            fill="toself",
            name=strategy_name,
            opacity=0.75,
        ))

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        title="Cost × Time × Emissions × Reliability Trade-off",
        template="plotly_white",
        margin=dict(l=30, r=30, t=70, b=30),
        legend=dict(orientation="h", y=-0.15),
    )
    return fig


def make_override_table(selected_shipment):
    if overrides_df.empty:
        return html.P("No dispatcher overrides recorded.", style={"padding": "15px", "color": "#666"})

    display_df = overrides_df.copy()
    if selected_shipment != "ALL" and "shipment_id" in display_df.columns:
        display_df = display_df[
            display_df["shipment_id"].astype(str).str.strip() == str(selected_shipment).strip()
        ].copy()

    if display_df.empty:
        return html.P("No overrides for this shipment.", style={"padding": "15px", "color": "#666"})

    header_style = {
        "padding": "10px 12px", "backgroundColor": "#e8f0fe", "fontWeight": "bold",
        "border": "1px solid #ddd", "textAlign": "left", "whiteSpace": "nowrap",
    }
    cell_style = {
        "padding": "9px 12px", "border": "1px solid #ddd",
        "textAlign": "left", "verticalAlign": "top",
    }

    header = html.Thead(html.Tr([
        html.Th(col, style=header_style) for col in display_df.columns
    ]))
    rows = [
        html.Tr([html.Td(str(row[col]), style=cell_style) for col in display_df.columns])
        for _, row in display_df.iterrows()
    ]
    return html.Div(
        html.Table(
            [header, html.Tbody(rows)],
            style={"width": "100%", "borderCollapse": "collapse", "fontSize": "14px"},
        ),
        style={"overflowX": "auto", "maxHeight": "400px", "overflowY": "auto"},
    )


# ==========================================================
# SHIPMENT OPTIONS
# ==========================================================
def build_shipment_options(df):
    options = [{"label": "All Shipments", "value": "ALL"}]
    if not df.empty and "shipment_id" in df.columns:
        ids = df["shipment_id"].dropna().astype(str).str.strip().unique()
        options += [{"label": sid, "value": sid} for sid in sorted(ids)]
    return options


shipment_options = build_shipment_options(compliance_df)


# ==========================================================
# LAYOUT
# ==========================================================
app.layout = html.Div([

    # ── Header ────────────────────────────────────────────
    html.Div([
        html.H1("❄ ColdChainGuard", style={"fontSize": "42px", "marginBottom": "4px"}),
        html.P(
            "Automated Cold-Chain Compliance Evidence System",
            style={"fontSize": "17px", "opacity": "0.88"},
        ),
        html.P(
            f"{'Database: PostgreSQL' if DB_AVAILABLE else 'Database: CSV fallback mode'}",
            style={"fontSize": "13px", "opacity": "0.7", "marginTop": "4px"},
        ),
    ], style=HEADER_STYLE),

    # ── Auto-refresh ──────────────────────────────────────
    dcc.Interval(id="auto-refresh", interval=30_000, n_intervals=0),

    # ── Filter ───────────────────────────────────────────
    html.Div([
        html.Label("Filter by Shipment", style={"fontWeight": "600", "display": "block", "marginBottom": "6px"}),
        dcc.Dropdown(
            id="shipment-filter",
            options=shipment_options,
            value="ALL",
            clearable=False,
            searchable=True,
            style={"fontSize": "15px"},
        ),
    ], style={"margin": "10px 20px 20px 20px"}),

    # ── KPI Row ───────────────────────────────────────────
    html.Div(id="kpi-row", style={"display": "flex", "flexWrap": "wrap", "margin": "0 10px 15px 10px"}),

    # ── Compliance + Temperature ──────────────────────────
    html.Div([
        html.Div(dcc.Graph(id="compliance-chart", config={"displayModeBar": True, "responsive": True}, style=GRAPH_STYLE), style={"flex": "1 1 48%"}),
        html.Div(dcc.Graph(id="temperature-chart", config={"displayModeBar": True, "responsive": True}, style=GRAPH_STYLE), style={"flex": "1 1 48%"}),
    ], style={**SECTION_STYLE, "display": "flex", "flexWrap": "wrap"}),

    # ── Sensor + Custody ─────────────────────────────────
    html.Div([
        html.Div(dcc.Graph(id="sensor-chart", config={"displayModeBar": True, "responsive": True}, style=GRAPH_STYLE), style={"flex": "1 1 48%"}),
        html.Div(dcc.Graph(id="custody-chart", config={"displayModeBar": True, "responsive": True}, style=GRAPH_STYLE), style={"flex": "1 1 48%"}),
    ], style={**SECTION_STYLE, "display": "flex", "flexWrap": "wrap"}),

    # ── Route Reliability ─────────────────────────────────
    html.Div(dcc.Graph(id="route-chart", config={"displayModeBar": True, "responsive": True}, style=GRAPH_STYLE), style=SECTION_STYLE),

    # ── Exception Monitoring ──────────────────────────────
    html.Div(dcc.Graph(id="exception-chart", config={"displayModeBar": True, "responsive": True}, style=GRAPH_STYLE), style=SECTION_STYLE),

    # ── RADAR Trade-off Chart ─────────────────────────────
    html.Div([
        html.H3("Cost × Time × Emissions × Reliability Trade-off", style={"marginTop": "0"}),
        dcc.Graph(
            id="tradeoff-chart",
            figure=make_radar_tradeoff(),
            config={"displayModeBar": True, "responsive": True},
            style=GRAPH_STYLE,
        ),
    ], style=SECTION_STYLE),

    # ── Audit Report Download ─────────────────────────────
    html.Div([
        html.H3("📄 Audit Report Download", style={"marginTop": "0"}),
        html.Div(id="report-download-area"),
    ], style=SECTION_STYLE),

    # ── Dispatcher Override History ───────────────────────
    html.Div([
        html.H3("🔄 Dispatcher Override History", style={"marginTop": "0"}),
        html.Div(id="override-table"),
    ], style=SECTION_STYLE),

    # ── Dispatcher Override Form ──────────────────────────
    html.Div([
        html.H3("✏ Apply Dispatcher Override", style={"marginTop": "0"}),
        html.P("Submit a documented route plan change. All changes are logged with timestamp and reason.", style={"color": "#555", "marginBottom": "16px"}),

        html.Div([

            html.Div([
                html.Label("Shipment ID *", style={"fontWeight": "600"}),
                dcc.Input(id="ovr-shipment-id", type="text", placeholder="e.g. SHP0001", style=INPUT_STYLE),
            ], style={"flex": "1 1 200px", "marginRight": "16px"}),

            html.Div([
                html.Label("New Route Plan *", style={"fontWeight": "600"}),
                dcc.Dropdown(
                    id="ovr-new-plan",
                    options=[
                        {"label": "Normal", "value": "Normal"},
                        {"label": "Delayed", "value": "Delayed"},
                        {"label": "Deviation", "value": "Deviation"},
                        {"label": "Rerouted", "value": "Rerouted"},
                        {"label": "Emergency Stop", "value": "Emergency Stop"},
                    ],
                    placeholder="Select new plan...",
                    style={"fontSize": "14px", "marginBottom": "10px"},
                ),
            ], style={"flex": "1 1 200px", "marginRight": "16px"}),

            html.Div([
                html.Label("Dispatcher Name *", style={"fontWeight": "600"}),
                dcc.Input(id="ovr-dispatcher", type="text", placeholder="e.g. Dispatcher_01", style=INPUT_STYLE),
            ], style={"flex": "1 1 200px"}),

        ], style={"display": "flex", "flexWrap": "wrap", "gap": "4px"}),

        html.Label("Override Reason * (minimum 5 characters)", style={"fontWeight": "600"}),
        dcc.Textarea(
            id="ovr-reason",
            placeholder="Explain why the plan is being changed...",
            style={**INPUT_STYLE, "height": "80px", "resize": "vertical"},
        ),

        html.Button("Submit Override", id="ovr-submit", n_clicks=0, style=BTN_STYLE),
        html.Div(id="ovr-feedback", style={"marginTop": "12px", "fontWeight": "600"}),

    ], style=SECTION_STYLE),

], style=PAGE_STYLE)


# ==========================================================
# MAIN CALLBACK — update all charts on filter or refresh
# ==========================================================
@app.callback(
    [
        Output("kpi-row", "children"),
        Output("compliance-chart", "figure"),
        Output("temperature-chart", "figure"),
        Output("sensor-chart", "figure"),
        Output("custody-chart", "figure"),
        Output("route-chart", "figure"),
        Output("exception-chart", "figure"),
        Output("tradeoff-chart", "figure"),
        Output("override-table", "children"),
        Output("report-download-area", "children"),
    ],
    [
        Input("shipment-filter", "value"),
        Input("auto-refresh", "n_intervals"),
    ],
)
def update_dashboard(selected_shipment, _n):
    sel = selected_shipment if selected_shipment else "ALL"

    # ── Reload data on refresh ───────────────────────────
    global compliance_df, shipments_df, tradeoff_df, overrides_df
    try:
        compliance_df, shipments_df = load_database_data()
        compliance_df = clean_dataframe(compliance_df)
        compliance_df = ensure_columns(compliance_df, {
            "shipment_id": "Unknown",
            "overall_compliance": "Review",
            "temperature_status": "Unknown",
            "sensor_reliability": "Unknown",
            "custody_evidence_quality": "Unknown",
            "route_reliability": "Unknown",
            "route_status": "Unknown",
        })
        tradeoff_df, overrides_df = load_experiment_data()
        tradeoff_df = clean_dataframe(tradeoff_df)
        overrides_df = clean_dataframe(overrides_df)
    except Exception:
        pass

    # ── Filter ───────────────────────────────────────────
    if sel == "ALL":
        df = compliance_df.copy()
    else:
        df = compliance_df[
            compliance_df["shipment_id"].astype(str).str.strip() == sel.strip()
        ].copy()

    # ── KPIs ─────────────────────────────────────────────
    total = len(df)
    compliant = int((df["overall_compliance"].astype(str).str.strip() == "Compliant").sum())
    non_compliant = int((df["overall_compliance"].astype(str).str.strip() == "Non-Compliant").sum())
    review = int((df["overall_compliance"].astype(str).str.strip() == "Review").sum())

    if sel == "ALL":
        ovr_count = len(overrides_df)
    elif not overrides_df.empty and "shipment_id" in overrides_df.columns:
        ovr_count = int((overrides_df["shipment_id"].astype(str).str.strip() == sel.strip()).sum())
    else:
        ovr_count = 0

    compliance_rate = f"{round(compliant / total * 100, 1)}%" if total > 0 else "N/A"

    kpis = html.Div([
        kpi_card("Total Shipments", str(total), "Monitored", "#1a73e8"),
        kpi_card("Compliant", str(compliant), f"{compliance_rate} pass rate", "#34a853"),
        kpi_card("Non-Compliant", str(non_compliant), "Requires action", "#ea4335"),
        kpi_card("Review", str(review), "Needs verification", "#fbbc04"),
        kpi_card("Overrides", str(ovr_count), "Plan changes logged", "#9c27b0"),
    ], style={"display": "flex", "flexWrap": "wrap", "width": "100%"})

    # ── Charts ───────────────────────────────────────────
    compliance_fig = make_compliance_pie(df)
    temperature_fig = make_count_bar(df, "temperature_status", "Temperature Status", ["Compliant", "Warning", "Alert", "Critical"])
    sensor_fig = make_count_bar(df, "sensor_reliability", "Sensor Reliability", ["Reliable", "Review", "Partial"])
    custody_fig = make_count_bar(df, "custody_evidence_quality", "Custody Evidence Quality", ["Complete", "Incomplete"])
    route_fig = make_count_bar(df, "route_reliability", "Route Reliability", ["High", "Moderate", "Low"])
    exception_fig = make_exception_chart(df)
    tradeoff_fig = make_radar_tradeoff()

    # ── Override table ────────────────────────────────────
    override_table = make_override_table(sel)

    # ── Report download area ──────────────────────────────
    if sel == "ALL":
        report_area = html.P(
            "Select a specific shipment to download its audit report PDF.",
            style={"color": "#666", "padding": "8px 0"},
        )
    else:
        pdf_name = f"{sel}_audit_report.pdf"
        pdf_path = os.path.join(REPORTS_DIR, pdf_name)
        if os.path.exists(pdf_path):
            report_area = html.Div([
                html.P(f"Audit report available for shipment {sel}:", style={"marginBottom": "8px"}),
                html.A(
                    f"📥 Download {pdf_name}",
                    href=f"/reports/{pdf_name}",
                    target="_blank",
                    style={
                        "backgroundColor": "#34a853",
                        "color": "white",
                        "padding": "10px 20px",
                        "borderRadius": "6px",
                        "textDecoration": "none",
                        "fontWeight": "600",
                    },
                ),
            ])
        else:
            report_area = html.P(
                f"No PDF report found for {sel}. Run: python src/audit_report.py",
                style={"color": "#666", "fontStyle": "italic"},
            )

    return (kpis, compliance_fig, temperature_fig, sensor_fig,
            custody_fig, route_fig, exception_fig, tradeoff_fig,
            override_table, report_area)


# ==========================================================
# DISPATCHER OVERRIDE SUBMIT CALLBACK
# ==========================================================
@app.callback(
    Output("ovr-feedback", "children"),
    Input("ovr-submit", "n_clicks"),
    [
        State("ovr-shipment-id", "value"),
        State("ovr-new-plan", "value"),
        State("ovr-dispatcher", "value"),
        State("ovr-reason", "value"),
    ],
    prevent_initial_call=True,
)
def submit_override(n_clicks, shipment_id, new_plan, dispatcher, reason):
    if not n_clicks:
        raise PreventUpdate

    # ── Validation ────────────────────────────────────────
    errors = []
    if not shipment_id or not str(shipment_id).strip():
        errors.append("Shipment ID is required.")
    if not new_plan:
        errors.append("New route plan is required.")
    if not dispatcher or not str(dispatcher).strip():
        errors.append("Dispatcher name is required.")
    if not reason or len(str(reason).strip()) < 5:
        errors.append("Reason must be at least 5 characters.")

    if errors:
        return html.Div([
            html.P("❌ Override rejected:", style={"color": "#ea4335", "margin": "0 0 4px 0"}),
            html.Ul([html.Li(e, style={"color": "#ea4335"}) for e in errors]),
        ])

    # ── Find previous plan ────────────────────────────────
    prev_plan = "Unknown"
    mask = compliance_df["shipment_id"].astype(str).str.strip() == str(shipment_id).strip()
    if mask.any() and "route_status" in compliance_df.columns:
        prev_plan = str(compliance_df.loc[mask.idxmax(), "route_status"])

    # ── Write override record ─────────────────────────────
    record = {
        "override_id": f"OVR-{uuid.uuid4().hex[:8].upper()}",
        "shipment_id": str(shipment_id).strip(),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "dispatcher": str(dispatcher).strip(),
        "previous_plan": prev_plan,
        "new_plan": new_plan,
        "reason": str(reason).strip(),
        "override_status": "Approved",
    }

    os.makedirs(EXPERIMENT_DIR, exist_ok=True)
    file_exists = os.path.exists(OVERRIDE_FILE)

    with open(OVERRIDE_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(record.keys()))
        if not file_exists:
            writer.writeheader()
        writer.writerow(record)

    return html.Div([
        html.P(
            f"✅ Override {record['override_id']} applied for shipment {shipment_id}.",
            style={"color": "#34a853"},
        ),
        html.P(
            f"Plan changed: {prev_plan} → {new_plan} | Dispatcher: {dispatcher}",
            style={"color": "#555", "fontSize": "13px"},
        ),
        html.P(
            "The override history table will refresh on the next 30-second cycle.",
            style={"color": "#888", "fontSize": "12px"},
        ),
    ])


# ==========================================================
# RUN
# ==========================================================
if __name__ == "__main__":
    print("=" * 70)
    print("COLDCHAINGUARD DASHBOARD v2")
    print("=" * 70)
    print(f"\nDatabase mode: {'PostgreSQL' if DB_AVAILABLE else 'CSV fallback'}")
    print("\nFeatures:")
    print("  [+] Dynamic shipment filtering")
    print("  [+] KPI cards with compliance rate")
    print("  [+] Compliance, temperature, sensor, custody, route charts")
    print("  [+] Exception monitoring bar chart")
    print("  [+] Radar trade-off chart (Cost x Time x Emissions x Reliability)")
    print("  [+] PDF audit report download links")
    print("  [+] Dispatcher override form with audit trail")
    print("  [+] 30-second auto-refresh")
    print("\nOpen in browser: http://127.0.0.1:8050/")
    print("=" * 70)
    app.run(host="127.0.0.1", port=8050, debug=True)