import os
import uuid
from datetime import datetime

import pandas as pd


# ==========================================================
# PROJECT PATHS
# ==========================================================

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

COMPLIANCE_FILE = os.path.join(
    PROJECT_ROOT,
    "data",
    "compliance_results.csv"
)

RESULT_DIR = os.path.join(
    PROJECT_ROOT,
    "data",
    "experiments"
)

HISTORY_FILE = os.path.join(
    RESULT_DIR,
    "dispatcher_override_history.csv"
)

os.makedirs(
    RESULT_DIR,
    exist_ok=True
)


# ==========================================================
# LOAD COMPLIANCE DATA
# ==========================================================

def load_compliance_data():

    print("=" * 70)
    print("COLDCHAINGUARD - DISPATCHER OVERRIDE")
    print("=" * 70)

    if not os.path.exists(COMPLIANCE_FILE):

        raise FileNotFoundError(
            f"Compliance file not found:\n"
            f"{COMPLIANCE_FILE}"
        )

    df = pd.read_csv(
        COMPLIANCE_FILE
    )

    print(
        f"\nCompliance records loaded: "
        f"{len(df)}"
    )

    return df


# ==========================================================
# CREATE OVERRIDE HISTORY TABLE
# ==========================================================

def create_history_table():

    if os.path.exists(HISTORY_FILE):

        history = pd.read_csv(
            HISTORY_FILE
        )

    else:

        history = pd.DataFrame(
            columns=[
                "override_id",
                "shipment_id",
                "timestamp",
                "dispatcher",
                "previous_plan",
                "new_plan",
                "reason",
                "override_status"
            ]
        )

    return history


# ==========================================================
# VALIDATE OVERRIDE
# ==========================================================

def validate_override(
    shipment_id,
    new_plan,
    reason,
    dispatcher
):

    errors = []

    if not shipment_id:

        errors.append(
            "Shipment ID is required"
        )

    if not new_plan:

        errors.append(
            "New plan is required"
        )

    if not reason or len(
        reason.strip()
    ) < 5:

        errors.append(
            "A meaningful override reason is required"
        )

    if not dispatcher:

        errors.append(
            "Dispatcher name is required"
        )

    return errors


# ==========================================================
# APPLY DISPATCHER OVERRIDE
# ==========================================================

def apply_override(
    compliance_df,
    history_df,
    shipment_id,
    new_plan,
    reason,
    dispatcher
):

    # ------------------------------------------------------
    # Validate
    # ------------------------------------------------------

    errors = validate_override(
        shipment_id,
        new_plan,
        reason,
        dispatcher
    )

    if errors:

        print("\nOverride rejected:")

        for error in errors:

            print(
                f"- {error}"
            )

        return compliance_df, history_df, False

    # ------------------------------------------------------
    # Find shipment
    # ------------------------------------------------------

    matches = compliance_df[
        compliance_df["shipment_id"]
        .astype(str)
        == str(shipment_id)
    ]

    if matches.empty:

        print(
            f"\nShipment not found: "
            f"{shipment_id}"
        )

        return compliance_df, history_df, False

    index = matches.index[0]

    # ------------------------------------------------------
    # Determine previous plan
    # ------------------------------------------------------

    if "route_status" in compliance_df.columns:

        previous_plan = str(
            compliance_df.loc[
                index,
                "route_status"
            ]
        )

    else:

        previous_plan = "Unknown"

    # ------------------------------------------------------
    # Create history record
    # ------------------------------------------------------

    override_record = {
        "override_id":
            f"OVR-{uuid.uuid4().hex[:8].upper()}",

        "shipment_id":
            shipment_id,

        "timestamp":
            datetime.now().isoformat(
                timespec="seconds"
            ),

        "dispatcher":
            dispatcher,

        "previous_plan":
            previous_plan,

        "new_plan":
            new_plan,

        "reason":
            reason,

        "override_status":
            "Approved"
    }

    history_df = pd.concat(
        [
            history_df,
            pd.DataFrame(
                [override_record]
            )
        ],
        ignore_index=True
    )

    # ------------------------------------------------------
    # Update current compliance decision
    # ------------------------------------------------------

    if "route_status" in compliance_df.columns:

        compliance_df.loc[
            index,
            "route_status"
        ] = new_plan

    # ------------------------------------------------------
    # Mark override
    # ------------------------------------------------------

    if "dispatcher_override" not in compliance_df.columns:

        compliance_df[
            "dispatcher_override"
        ] = "No"

    if "override_reason" not in compliance_df.columns:

        compliance_df[
            "override_reason"
        ] = ""

    compliance_df.loc[
        index,
        "dispatcher_override"
    ] = "Yes"

    compliance_df.loc[
        index,
        "override_reason"
    ] = reason

    print("\n")
    print("=" * 70)
    print("DISPATCHER OVERRIDE APPLIED")
    print("=" * 70)

    print(
        f"\nShipment       : "
        f"{shipment_id}"
    )

    print(
        f"Previous plan  : "
        f"{previous_plan}"
    )

    print(
        f"New plan       : "
        f"{new_plan}"
    )

    print(
        f"Dispatcher     : "
        f"{dispatcher}"
    )

    print(
        f"Reason         : "
        f"{reason}"
    )

    print(
        f"Override ID    : "
        f"{override_record['override_id']}"
    )

    return compliance_df, history_df, True


# ==========================================================
# SAVE DATA
# ==========================================================

def save_data(
    compliance_df,
    history_df
):

    compliance_df.to_csv(
        COMPLIANCE_FILE,
        index=False
    )

    history_df.to_csv(
        HISTORY_FILE,
        index=False
    )

    print("\n")
    print("=" * 70)
    print("DATA SAVED")
    print("=" * 70)

    print(
        f"\nUpdated compliance file:\n"
        f"{COMPLIANCE_FILE}"
    )

    print(
        f"\nOverride history:\n"
        f"{HISTORY_FILE}"
    )


# ==========================================================
# DISPLAY HISTORY
# ==========================================================

def display_history(history_df):

    print("\n")
    print("=" * 70)
    print("DISPATCHER OVERRIDE HISTORY")
    print("=" * 70)

    if history_df.empty:

        print(
            "\nNo override records found."
        )

        return

    print(
        history_df.to_string(
            index=False
        )
    )


# ==========================================================
# DEMONSTRATION
# ==========================================================

def run_demo(
    compliance_df,
    history_df
):

    print("\n")
    print("=" * 70)
    print("RUNNING DISPATCHER OVERRIDE DEMONSTRATION")
    print("=" * 70)

    # ------------------------------------------------------
    # Select three shipments from the dataset
    # ------------------------------------------------------

    shipment_ids = (
        compliance_df[
            "shipment_id"
        ]
        .head(3)
        .tolist()
    )

    # ------------------------------------------------------
    # Override 1
    # ------------------------------------------------------

    if len(shipment_ids) >= 1:

        compliance_df, history_df, success = (
            apply_override(
                compliance_df,
                history_df,
                shipment_ids[0],
                "Delayed",
                "Traffic delay requires route adjustment",
                "Dispatcher_01"
            )
        )

    # ------------------------------------------------------
    # Override 2
    # ------------------------------------------------------

    if len(shipment_ids) >= 2:

        compliance_df, history_df, success = (
            apply_override(
                compliance_df,
                history_df,
                shipment_ids[1],
                "Normal",
                "Alternate route available with lower delay",
                "Dispatcher_01"
            )
        )

    # ------------------------------------------------------
    # Override 3
    # ------------------------------------------------------

    if len(shipment_ids) >= 3:

        compliance_df, history_df, success = (
            apply_override(
                compliance_df,
                history_df,
                shipment_ids[2],
                "Deviation",
                "Route deviation approved due to road closure",
                "Dispatcher_02"
            )
        )

    return compliance_df, history_df


# ==========================================================
# MAIN
# ==========================================================

def main():

    compliance_df = load_compliance_data()

    history_df = create_history_table()

    compliance_df, history_df = run_demo(
        compliance_df,
        history_df
    )

    save_data(
        compliance_df,
        history_df
    )

    display_history(
        history_df
    )

    print("\n")
    print("=" * 70)
    print(
        "DISPATCHER OVERRIDE TEST COMPLETED"
    )
    print("=" * 70)


# ==========================================================
# RUN
# ==========================================================

if __name__ == "__main__":
    main()