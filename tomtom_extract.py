#!/usr/bin/env python3
"""Collect TomTom Traffic Flow data for a list of road corridors.

For each point in corridors.csv this queries the TomTom *Traffic Flow Segment
Data* endpoint, which returns current speed, free-flow speed, travel times and
road closure state for the road segment nearest to that point. Results are
appended to a timestamped CSV (one row per corridor per run) plus, optionally,
the raw JSON responses for full provenance.

The API key is NEVER stored in this repository. Export it as an environment
variable before running (see README.md for how to obtain one):

    export TOMTOM_API_KEY="your-key-here"
    python tomtom_extract.py

Run it on a schedule (cron, systemd timer, GitHub Action) to build a
time-series. TomTom's free tier (2,500 requests/day) comfortably covers the
64-corridor Jabodetabek list at hourly cadence (64 x 24 = 1,536 requests/day).

Dependencies: requests, pandas  (pip install requests pandas)
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

BASE_URL = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"
HERE = Path(__file__).resolve().parent
CORRIDORS = HERE / "corridors.csv"
OUT_CSV = HERE / "collected" / "tomtom_flow.csv"
RAW_DIR = HERE / "collected" / "raw"
SAVE_RAW = True          # keep raw JSON responses (recommended for provenance)
REQUEST_SPACING_S = 1.5  # polite spacing; also keeps free-tier QPS happy


def fetch_point(key: str, lat: float, lon: float) -> dict:
    """One flowSegmentData call. Raises for HTTP errors."""
    r = requests.get(
        BASE_URL,
        params={"point": f"{lat},{lon}", "unit": "KMPH", "key": key},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["flowSegmentData"]


def main() -> int:
    key = os.environ.get("TOMTOM_API_KEY")
    if not key:
        print("ERROR: set the TOMTOM_API_KEY environment variable first "
              "(see README.md).", file=sys.stderr)
        return 1

    corridors = pd.read_csv(CORRIDORS)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for c in corridors.itertuples():
        try:
            d = fetch_point(key, c.lat, c.lon)
        except Exception as exc:  # noqa: BLE001 - log and continue
            print(f"  {c.station_id}: FAILED {type(exc).__name__}: {exc}",
                  file=sys.stderr)
            continue
        cur, free = d.get("currentSpeed"), d.get("freeFlowSpeed")
        rows.append({
            "station_id": c.station_id,
            "name": c.name,
            "obs_time_utc": now.isoformat(),
            "lat": c.lat,
            "lon": c.lon,
            "current_speed": cur,                 # km/h
            "free_flow_speed": free,              # km/h
            "current_travel_time": d.get("currentTravelTime"),    # s
            "free_flow_travel_time": d.get("freeFlowTravelTime"), # s
            # congestion ratio: 0 = free flow, 1 = fully stopped
            "congestion_ratio": (None if not cur or not free
                                 else round(1 - cur / free, 4)),
            "road_closure": d.get("roadClosure"),
            "confidence": d.get("confidence"),
            "frc": d.get("frc"),                  # functional road class
        })
        if SAVE_RAW:
            raw = RAW_DIR / now.strftime("%Y/%m/%d")
            raw.mkdir(parents=True, exist_ok=True)
            (raw / f"{now:%H%M%S}_{c.station_id}.json").write_text(
                json.dumps(d, indent=2))
        time.sleep(REQUEST_SPACING_S)

    if not rows:
        print("no data collected", file=sys.stderr)
        return 1
    frame = pd.DataFrame(rows)
    frame.to_csv(OUT_CSV, mode="a", header=not OUT_CSV.exists(), index=False)
    print(f"{now} collected {len(frame)}/{len(corridors)} corridors "
          f"-> {OUT_CSV}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
