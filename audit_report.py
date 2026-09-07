import os
import sys
import time
import pandas as pd

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak
)


# ==========================================================
# PROJECT ROOT
# ==========================================================

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

sys.path.append(PROJECT_ROOT)


# ==========================================================
# INPUT / OUTPUT PATHS
# ==========================================================

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

os.makedirs(
    REPORT_DIR,
    exist_ok=True
)


# ==========================================================
# LOAD EVIDENCE PACK
# ==========================================================

def load_evidence_pack():

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
# FORMAT VALUE
# ==========================================================

def format_value(value):

    if pd.isna(value):
        return "N/A"

    if isinstance(value, float):

        return f"{value:.2f}"

    return str(value)


# ==========================================================
# REPORT HEADER
# ==========================================================

def create_header():

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=20,
        leading=24,
        spaceAfter=8
    )

    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        fontSize=10,
        leading=14,
        spaceAfter=15
    )

    elements = []

    elements.append(
        Paragraph(
            "COLDCHAINGUARD",
            title_style
        )
    )

    elements.append(
        Paragraph(
            "AUTOMATED COLD-CHAIN COMPLIANCE AUDIT REPORT",
            subtitle_style
        )
    )

    return elements


# ==========================================================
# SECTION TITLE
# ==========================================================

def section_title(title):

    styles = getSampleStyleSheet()

    style = ParagraphStyle(
        "SectionTitle",
        parent=styles["Heading2"],
        fontSize=12,
        leading=15,
        spaceBefore=10,
        spaceAfter=6
    )

    return Paragraph(
        title,
        style
    )


# ==========================================================
# CREATE TABLE
# ==========================================================

def create_table(data):

    table = Table(
        data,
        colWidths=[
            65 * mm,
            105 * mm
        ]
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.grey
                ),

                (
                    "BACKGROUND",
                    (0, 0),
                    (0, -1),
                    colors.lightgrey
                ),

                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE"
                ),

                (
                    "FONTNAME",
                    (0, 0),
                    (0, -1),
                    "Helvetica-Bold"
                ),

                (
                    "FONTNAME",
                    (1, 0),
                    (1, -1),
                    "Helvetica"
                ),

                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    9
                ),

                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    6
                ),

                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    6
                ),

                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    5
                ),

                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    5
                )
            ]
        )
    )

    return table


# ==========================================================
# COMPLIANCE STATUS
# ==========================================================

def status_text(status):

    if status == "Compliant":
        return "COMPLIANT"

    if status == "Non-Compliant":
        return "NON-COMPLIANT"

    return "REVIEW REQUIRED"


# ==========================================================
# CREATE SINGLE REPORT
# ==========================================================

def create_single_report(row):

    shipment_id = str(
        row["shipment_id"]
    )

    filename = (
        f"{shipment_id}_audit_report.pdf"
    )

    output_path = os.path.join(
        REPORT_DIR,
        filename
    )

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm
    )

    elements = []

    # ------------------------------------------------------
    # Header
    # ------------------------------------------------------

    elements.extend(
        create_header()
    )

    # ------------------------------------------------------
    # Shipment Information
    # ------------------------------------------------------

    elements.append(
        section_title(
            "1. Shipment Information"
        )
    )

    shipment_data = [
        [
            "Shipment ID",
            format_value(
                row["shipment_id"]
            )
        ],
        [
            "Batch ID",
            format_value(
                row["batch_id"]
            )
        ],
        [
            "Vehicle ID",
            format_value(
                row["vehicle_id"]
            )
        ],
        [
            "Vehicle Type",
            format_value(
                row["vehicle_type"]
            )
        ],
        [
            "Origin",
            format_value(
                row["origin"]
            )
        ],
        [
            "Destination",
            format_value(
                row["destination"]
            )
        ],
        [
            "Departure",
            format_value(
                row["departure_time"]
            )
        ],
        [
            "Arrival",
            format_value(
                row["arrival_time"]
            )
        ],
        [
            "Shipment Status",
            format_value(
                row["shipment_status"]
            )
        ]
    ]

    elements.append(
        create_table(
            shipment_data
        )
    )

    # ------------------------------------------------------
    # Product Information
    # ------------------------------------------------------

    elements.append(
        section_title(
            "2. Product Information"
        )
    )

    product_data = [
        [
            "Product",
            format_value(
                row["product_name"]
            )
        ],
        [
            "Product Type",
            format_value(
                row["product_type"]
            )
        ],
        [
            "Required Temperature",
            (
                f'{format_value(row["min_temperature_c"])} °C '
                f'to '
                f'{format_value(row["max_temperature_c"])} °C'
            )
        ],
        [
            "Quantity",
            format_value(
                row["quantity"]
            )
        ],
        [
            "Expiry Date",
            format_value(
                row["expiry_date"]
            )
        ]
    ]

    elements.append(
        create_table(
            product_data
        )
    )

    # ------------------------------------------------------
    # Temperature Evidence
    # ------------------------------------------------------

    elements.append(
        section_title(
            "3. Temperature Evidence"
        )
    )

    temperature_data = [
        [
            "Sensor Records",
            format_value(
                row["total_raw_sensor_records"]
            )
        ],
        [
            "Available Readings",
            format_value(
                row["available_temperature_records"]
            )
        ],
        [
            "Missing Readings",
            format_value(
                row["missing_temperature_records"]
            )
        ],
        [
            "Offline Observations",
            format_value(
                row["offline_observations"]
            )
        ],
        [
            "Average Temperature",
            f'{format_value(row["raw_average_temperature"])} °C'
        ],
        [
            "Minimum Temperature",
            f'{format_value(row["raw_min_temperature"])} °C'
        ],
        [
            "Maximum Temperature",
            f'{format_value(row["raw_max_temperature"])} °C'
        ],
        [
            "Excursion Records",
            format_value(
                row["excursion_records"]
            )
        ],
        [
            "Excursion Duration",
            f'{format_value(row["total_excursion_minutes"])} minutes'
        ],
        [
            "Temperature Status",
            format_value(
                row["temperature_status"]
            )
        ]
    ]

    elements.append(
        create_table(
            temperature_data
        )
    )

    # ------------------------------------------------------
    # Calibration Evidence
    # ------------------------------------------------------

    elements.append(
        section_title(
            "4. Calibration Evidence"
        )
    )

    calibration_data = [
        [
            "Sensors Used",
            format_value(
                row["sensors_used"]
            )
        ],
        [
            "Valid Calibration Sensors",
            format_value(
                row["valid_calibration_sensors"]
            )
        ],
        [
            "Invalid Calibration Sensors",
            format_value(
                row["invalid_calibration_sensors"]
            )
        ],
        [
            "Maximum Calibration Error",
            format_value(
                row["maximum_calibration_error"]
            )
        ],
        [
            "Average Calibration Error",
            format_value(
                row["average_calibration_error"]
            )
        ],
        [
            "Calibration Status",
            format_value(
                row["calibration_status"]
            )
        ],
        [
            "Sensor Reliability",
            format_value(
                row["sensor_reliability"]
            )
        ]
    ]

    elements.append(
        create_table(
            calibration_data
        )
    )

    # ------------------------------------------------------
    # Custody Evidence
    # ------------------------------------------------------

    elements.append(
        section_title(
            "5. Custody / Handover Evidence"
        )
    )

    custody_data = [
        [
            "Total Handovers",
            format_value(
                row["total_handovers"]
            )
        ],
        [
            "Signed Handovers",
            format_value(
                row["signed_handovers"]
            )
        ],
        [
            "Missing Signatures",
            format_value(
                row["missing_handover_signatures"]
            )
        ],
        [
            "Custody Locations",
            format_value(
                row["custody_locations"]
            )
        ],
        [
            "Custody Evidence",
            format_value(
                row["custody_evidence_quality"]
            )
        ],
        [
            "Custody Status",
            format_value(
                row["custody_status"]
            )
        ]
    ]

    elements.append(
        create_table(
            custody_data
        )
    )

    # ------------------------------------------------------
    # Route Evidence
    # ------------------------------------------------------

    elements.append(
        section_title(
            "6. Route Evidence"
        )
    )

    route_data = [
        [
            "Total Route Events",
            format_value(
                row["total_route_events"]
            )
        ],
        [
            "Traffic Delay Events",
            format_value(
                row["traffic_delay_events"]
            )
        ],
        [
            "Traffic Delay Minutes",
            format_value(
                row["traffic_delay_minutes"]
            )
        ],
        [
            "Route Deviations",
            format_value(
                row["route_deviation_events"]
            )
        ],
        [
            "Route Deviation Minutes",
            format_value(
                row["route_deviation_minutes"]
            )
        ],
        [
            "Total Route Event Minutes",
            format_value(
                row["total_route_event_minutes"]
            )
        ],
        [
            "Route Reliability",
            format_value(
                row["route_reliability"]
            )
        ],
        [
            "Route Status",
            format_value(
                row["route_status"]
            )
        ]
    ]

    elements.append(
        create_table(
            route_data
        )
    )

    # ------------------------------------------------------
    # Evidence Completeness
    # ------------------------------------------------------

    elements.append(
        section_title(
            "7. Evidence Completeness"
        )
    )

    completeness_data = [
        [
            "Evidence Sources Available",
            f'{format_value(row["evidence_completeness"])} / 4'
        ],
        [
            "Evidence Completeness",
            (
                f'{format_value(row["evidence_completeness_percent"])} %'
            )
        ]
    ]

    elements.append(
        create_table(
            completeness_data
        )
    )

    # ------------------------------------------------------
    # Final Compliance Decision
    # ------------------------------------------------------

    elements.append(
        section_title(
            "8. Final Compliance Decision"
        )
    )

    final_status = status_text(
        row["overall_compliance"]
    )

    final_data = [
        [
            "Overall Compliance",
            final_status
        ],
        [
            "Compliance Reason",
            format_value(
                row["compliance_reason"]
            )
        ],
        [
            "Audit Conclusion",
            format_value(
                row["audit_conclusion"]
            )
        ]
    ]

    elements.append(
        create_table(
            final_data
        )
    )

    elements.append(
        Spacer(
            1,
            15
        )
    )

    elements.append(
        Paragraph(
            "This report was automatically generated by "
            "ColdChainGuard from sensor, calibration, "
            "custody and route evidence.",
            ParagraphStyle(
                "Footer",
                parent=getSampleStyleSheet()["Normal"],
                fontSize=8,
                alignment=TA_CENTER
            )
        )
    )

    # ------------------------------------------------------
    # Build PDF
    # ------------------------------------------------------

    doc.build(
        elements
    )

    return output_path


# ==========================================================
# GENERATE ALL REPORTS
# ==========================================================

def generate_all_reports(df):

    print("\n")
    print("=" * 70)
    print("GENERATING AUDIT REPORTS")
    print("=" * 70)

    start_time = time.perf_counter()

    generated = 0

    for _, row in df.iterrows():

        create_single_report(
            row
        )

        generated += 1

        if generated % 50 == 0:

            print(
                f"Generated {generated} / {len(df)} reports"
            )

    end_time = time.perf_counter()

    processing_time = (
        end_time - start_time
    )

    print("\n")
    print("=" * 70)
    print("REPORT GENERATION COMPLETED")
    print("=" * 70)

    print(
        f"\nReports generated : {generated}"
    )

    print(
        f"Processing time   : {processing_time:.2f} seconds"
    )

    if generated > 0:

        print(
            f"Average per report: "
            f"{processing_time / generated:.4f} seconds"
        )

    print(
        f"\nReports saved to:\n{REPORT_DIR}"
    )

    return generated, processing_time


# ==========================================================
# MAIN
# ==========================================================

def main():

    print("=" * 70)
    print("COLDCHAINGUARD - AUDIT REPORT GENERATOR")
    print("=" * 70)

    df = load_evidence_pack()

    generated, processing_time = (
        generate_all_reports(df)
    )

    print("\n")
    print("=" * 70)
    print("AUDIT REPORT GENERATION SUCCESSFUL")
    print("=" * 70)


# ==========================================================
# RUN
# ==========================================================

if __name__ == "__main__":
    main()