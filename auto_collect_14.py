import os
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv


# ============================================================
# PATH CONFIGURATION
# ============================================================

HERE = Path(__file__).resolve().parent

CORRIDORS_PATH = HERE / "corridors.csv"

TRAIN_PATH = (
    HERE
    / "data"
    / "processed"
    / "forecasting_train_preprocessed.csv"
)

OUT_CSV = (
    HERE
    / "collected"
    / "tomtom_flow_top14.csv"
)

ENV_FILE = HERE / ".env"


# ============================================================
# TOMTOM CONFIGURATION
# ============================================================

BASE_URL = (
    "https://api.tomtom.com/traffic/services/4/"
    "flowSegmentData/absolute/10/json"
)

REQUEST_SPACING_S = 1.5

load_dotenv(
    dotenv_path=ENV_FILE,
    override=False
)


# ============================================================
# TOMTOM API REQUEST
# ============================================================

def fetch_point(key, lat, lon):

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
# LOAD FINAL 14 CORRIDORS
# ============================================================

def load_top14():

    if not CORRIDORS_PATH.exists():
        raise FileNotFoundError(
            f"corridors.csv tidak ditemukan:\n"
            f"{CORRIDORS_PATH}"
        )

    if not TRAIN_PATH.exists():
        raise FileNotFoundError(
            f"forecasting_train_preprocessed.csv "
            f"tidak ditemukan:\n"
            f"{TRAIN_PATH}"
        )

    corridors = pd.read_csv(
        CORRIDORS_PATH
    )

    train = pd.read_csv(
        TRAIN_PATH
    )

    required_corridor_columns = {
        "station_id",
        "name",
        "lat",
        "lon",
    }

    missing = (
        required_corridor_columns
        - set(corridors.columns)
    )

    if missing:
        raise ValueError(
            "Kolom corridors.csv kurang: "
            + ", ".join(sorted(missing))
        )

    if "corridor_file" not in train.columns:
        raise ValueError(
            "Kolom 'corridor_file' tidak ditemukan "
            "di forecasting_train_preprocessed.csv"
        )

    top14 = sorted(
        train["corridor_file"]
        .dropna()
        .astype(str)
        .unique()
    )

    if len(top14) != 14:
        raise ValueError(
            f"Expected 14 corridors, "
            f"found {len(top14)}"
        )

    corridors["station_id"] = (
        corridors["station_id"]
        .astype(str)
    )

    selected = corridors[
        corridors["station_id"].isin(top14)
    ].copy()

    if len(selected) != 14:
        found_ids = set(
            selected["station_id"]
            .astype(str)
        )

        missing_ids = (
            set(top14)
            - found_ids
        )

        raise ValueError(
            "Tidak semua 14 corridor ditemukan "
            "di corridors.csv.\n"
            f"Missing: {sorted(missing_ids)}"
        )

    # urutan harus sama dengan top14
    selected = (
        selected
        .set_index("station_id")
        .loc[top14]
        .reset_index()
    )

    return selected


# ============================================================
# CHECK DUPLICATE TIMESTAMP
# ============================================================

def snapshot_already_exists(timestamp_iso):

    if not OUT_CSV.exists():
        return False

    try:
        existing = pd.read_csv(
            OUT_CSV,
            usecols=[
                "obs_time_utc"
            ]
        )

    except Exception:
        return False

    return (
        timestamp_iso
        in existing["obs_time_utc"]
        .astype(str)
        .values
    )


# ============================================================
# COLLECT ONE SNAPSHOT
# ============================================================

def collect_once(corridors):

    key = os.getenv(
        "TOMTOM_API_KEY"
    )

    if not key:
        raise RuntimeError(
            "TOMTOM_API_KEY tidak ditemukan. "
            "Pastikan tersedia di .env lokal "
            "atau GitHub Actions Secret."
        )

    # Timestamp per jam
    now = (
        datetime.now(
            timezone.utc
        )
        .replace(
            minute=0,
            second=0,
            microsecond=0
        )
    )

    timestamp_iso = (
        now.isoformat()
    )

    print()
    print(
        "=============================="
    )
    print(
        f"Collection timestamp: "
        f"{timestamp_iso}"
    )
    print(
        "=============================="
    )

    # Hindari data jam yang sama masuk dua kali
    if snapshot_already_exists(
        timestamp_iso
    ):
        print(
            "Snapshot untuk timestamp ini "
            "sudah ada."
        )
        print(
            "Collection skipped untuk "
            "mencegah duplicate."
        )
        return

    rows = []

    for c in corridors.itertuples():

        try:

            data = fetch_point(
                key,
                float(c.lat),
                float(c.lon)
            )

            current_speed = data.get(
                "currentSpeed"
            )

            free_flow_speed = data.get(
                "freeFlowSpeed"
            )

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
                    4
                )

            rows.append({

                "station_id":
                    c.station_id,

                "name":
                    c.name,

                "obs_time_utc":
                    timestamp_iso,

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

                "confidence":
                    data.get(
                        "confidence"
                    ),

                "road_closure":
                    data.get(
                        "roadClosure"
                    ),

                "frc":
                    data.get(
                        "frc"
                    ),
            })

            print(
                f"[OK] "
                f"{c.station_id:<18} "
                f"{c.name:<25} "
                f"speed={current_speed}"
            )

        except Exception as exc:

            print(
                f"[FAILED] "
                f"{c.station_id} "
                f"{c.name}: "
                f"{type(exc).__name__}: "
                f"{exc}"
            )

        time.sleep(
            REQUEST_SPACING_S
        )

    if not rows:
        raise RuntimeError(
            "Tidak ada data yang berhasil "
            "dikumpulkan."
        )

    frame = pd.DataFrame(
        rows
    )

    OUT_CSV.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    frame.to_csv(
        OUT_CSV,
        mode="a",
        header=not OUT_CSV.exists(),
        index=False
    )

    print()
    print(
        "=== COLLECTION COMPLETE ==="
    )

    print(
        f"Collected : "
        f"{len(frame)}/{len(corridors)}"
    )

    print(
        f"Output    : "
        f"{OUT_CSV}"
    )

    if len(frame) < len(corridors):

        print(
            f"WARNING: "
            f"{len(corridors) - len(frame)} "
            f"corridor gagal dikumpulkan."
        )


# ============================================================
# MAIN
# ============================================================

def main():

    corridors = load_top14()

    print()
    print(
        "Final corridors selected:"
    )

    for c in corridors.itertuples():

        print(
            f"- {c.station_id}: "
            f"{c.name}"
        )

    print()
    print(
        f"Total corridors: "
        f"{len(corridors)}"
    )

    # GitHub Actions akan menjalankan
    # script ini sekali setiap jadwal.
    collect_once(
        corridors
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()