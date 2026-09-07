#!/usr/bin/env python3
"""Collect TomTom Traffic Flow data for a list of road corridors.

For each point in corridors.csv, this script queries the TomTom Traffic Flow
Segment Data endpoint.

The API key is loaded from:
1. TOMTOM_API_KEY environment variable, or
2. A local .env file in the same directory as this script.

IMPORTANT:
Never commit the .env file to GitHub.

Dependencies:
    pip install requests pandas python-dotenv
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv


# ============================================================
# PATH CONFIGURATION
# ============================================================

BASE_URL = (
    "https://api.tomtom.com/traffic/services/4/"
    "flowSegmentData/absolute/10/json"
)

HERE = Path(__file__).resolve().parent

CORRIDORS = HERE / "corridors.csv"
OUT_CSV = HERE / "collected" / "tomtom_flow.csv"
RAW_DIR = HERE / "collected" / "raw"

SAVE_RAW = True

# Delay between API requests
REQUEST_SPACING_S = 1.5


# ============================================================
# LOAD ENVIRONMENT
# ============================================================

ENV_FILE = HERE / ".env"

# Load .env if available.
# Existing environment variables are NOT overwritten.
load_dotenv(dotenv_path=ENV_FILE, override=False)


# ============================================================
# TOMTOM API REQUEST
# ============================================================

def fetch_point(key: str, lat: float, lon: float) -> dict:
    """Request Traffic Flow Segment Data for one coordinate."""

    response = requests.get(
        BASE_URL,
        params={
            "point": f"{lat},{lon}",
            "unit": "KMPH",
            "key": key,
        },
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    if "flowSegmentData" not in data:
        raise ValueError(
            "TomTom response does not contain flowSegmentData"
        )

    return data["flowSegmentData"]


# ============================================================
# MAIN
# ============================================================

def main() -> int:

    # --------------------------------------------------------
    # API KEY
    # --------------------------------------------------------

    key = os.getenv("TOMTOM_API_KEY")

    if not key:
        print(
            "ERROR: TOMTOM_API_KEY not found.\n"
            f"Expected .env file at:\n{ENV_FILE}\n\n"
            "The .env file should contain:\n"
            "TOMTOM_API_KEY=your_api_key",
            file=sys.stderr,
        )
        return 1

    # --------------------------------------------------------
    # CHECK CORRIDORS FILE
    # --------------------------------------------------------

    if not CORRIDORS.exists():
        print(
            f"ERROR: corridors.csv not found:\n{CORRIDORS}",
            file=sys.stderr,
        )
        return 1

    # --------------------------------------------------------
    # LOAD CORRIDORS
    # --------------------------------------------------------

    corridors = pd.read_csv(CORRIDORS)

    required_columns = {
        "station_id",
        "name",
        "lat",
        "lon",
    }

    missing_columns = (
        required_columns - set(corridors.columns)
    )

    if missing_columns:
        print(
            "ERROR: corridors.csv is missing columns: "
            + ", ".join(sorted(missing_columns)),
            file=sys.stderr,
        )
        return 1

    # --------------------------------------------------------
    # ONE TIMESTAMP FOR THE ENTIRE GRAPH SNAPSHOT
    # --------------------------------------------------------

    now = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
    )

    OUT_CSV.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    rows = []

    print(
        f"Collecting TomTom data for "
        f"{len(corridors)} corridors..."
    )

    # --------------------------------------------------------
    # COLLECT EACH CORRIDOR
    # --------------------------------------------------------

    for c in corridors.itertuples():

        try:

            data = fetch_point(
                key,
                c.lat,
                c.lon,
            )

        except Exception as exc:

            print(
                f"{c.station_id}: FAILED "
                f"{type(exc).__name__}: {exc}",
                file=sys.stderr,
            )

            continue

        current_speed = data.get(
            "currentSpeed"
        )

        free_flow_speed = data.get(
            "freeFlowSpeed"
        )

        # ----------------------------------------------------
        # CONGESTION RATIO
        # ----------------------------------------------------

        if (
            current_speed is None
            or free_flow_speed is None
            or free_flow_speed == 0
        ):
            congestion_ratio = None

        else:

            congestion_ratio = round(
                1
                - (
                    current_speed
                    / free_flow_speed
                ),
                4,
            )

        # ----------------------------------------------------
        # ROW
        # ----------------------------------------------------

        rows.append({
            "station_id":
                c.station_id,

            "name":
                c.name,

            "obs_time_utc":
                now.isoformat(),

            "lat":
                c.lat,

            "lon":
                c.lon,

            "current_speed":
                current_speed,

            "free_flow_speed":
                free_flow_speed,

            "current_travel_time":
                data.get(
                    "currentTravelTime"
                ),

            "free_flow_travel_time":
                data.get(
                    "freeFlowTravelTime"
                ),

            "congestion_ratio":
                congestion_ratio,

            "road_closure":
                data.get(
                    "roadClosure"
                ),

            "confidence":
                data.get(
                    "confidence"
                ),

            "frc":
                data.get(
                    "frc"
                ),
        })

        # ----------------------------------------------------
        # SAVE RAW JSON
        # ----------------------------------------------------

        if SAVE_RAW:

            raw_dir = (
                RAW_DIR
                / now.strftime("%Y/%m/%d")
            )

            raw_dir.mkdir(
                parents=True,
                exist_ok=True
            )

            raw_file = (
                raw_dir
                / (
                    f"{now:%H%M%S}_"
                    f"{c.station_id}.json"
                )
            )

            raw_file.write_text(
                json.dumps(
                    data,
                    indent=2,
                ),
                encoding="utf-8",
            )

        time.sleep(
            REQUEST_SPACING_S
        )

    # --------------------------------------------------------
    # CHECK RESULT
    # --------------------------------------------------------

    if not rows:

        print(
            "ERROR: no data collected.",
            file=sys.stderr,
        )

        return 1

    # --------------------------------------------------------
    # SAVE CSV
    # --------------------------------------------------------

    frame = pd.DataFrame(rows)

    frame.to_csv(
        OUT_CSV,
        mode="a",
        header=not OUT_CSV.exists(),
        index=False,
    )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    print()
    print("=== COLLECTION COMPLETE ===")

    print(
        f"Timestamp : {now}"
    )

    print(
        f"Collected : "
        f"{len(frame)}/{len(corridors)} corridors"
    )

    print(
        f"Output    : {OUT_CSV}"
    )

    if len(frame) < len(corridors):

        print(
            f"WARNING: "
            f"{len(corridors) - len(frame)} "
            "corridor(s) failed."
        )

    return 0


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    sys.exit(main())
