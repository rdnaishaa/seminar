from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
FULL_DATA_DIR = ROOT / "full_data"

OUTPUT_DIR = ROOT / "data" / "processed"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "synchronization_analysis.csv"


# ============================================================
# LOAD ALL CORRIDORS
# ============================================================

corridors = []

for file in sorted(FULL_DATA_DIR.glob("*.csv")):

    df = pd.read_csv(file)

    df["obs_time_utc"] = pd.to_datetime(
        df["obs_time_utc"],
        utc=True,
        errors="coerce"
    )

    df = df.dropna(subset=["obs_time_utc"])
    df = df.sort_values("obs_time_utc")

    if len(df) == 0:
        continue

    corridors.append({
        "name": df["name"].iloc[0],
        "rows": len(df),
        "timestamps": set(df["obs_time_utc"])
    })


# ============================================================
# SELECT TOP 14
# ============================================================

corridors = sorted(
    corridors,
    key=lambda x: x["rows"],
    reverse=True
)[:14]


# ============================================================
# COMMON RANGE
# ============================================================

start = max(
    min(c["timestamps"])
    for c in corridors
)

end = min(
    max(c["timestamps"])
    for c in corridors
)

grid = pd.date_range(
    start=start,
    end=end,
    freq="1h"
)


# ============================================================
# CHECK EVERY TIMESTAMP
# ============================================================

rows = []

for timestamp in grid:

    available = [
        c["name"]
        for c in corridors
        if timestamp in c["timestamps"]
    ]

    missing = [
        c["name"]
        for c in corridors
        if timestamp not in c["timestamps"]
    ]

    rows.append({
        "timestamp": timestamp,
        "available_corridors": len(available),
        "missing_corridors": len(missing)
    })


result = pd.DataFrame(rows)


# ============================================================
# SUMMARY
# ============================================================

print("\n=== CROSS-CORRIDOR SYNCHRONIZATION ===")

print(f"Corridors analysed : {len(corridors)}")
print(f"Hourly timestamps  : {len(grid)}")


distribution = (
    result["available_corridors"]
    .value_counts()
    .sort_index()
)


print("\n=== AVAILABLE CORRIDORS PER TIMESTAMP ===")

for available, count in distribution.items():

    print(
        f"{available:2d}/14 corridors available : "
        f"{count:4d} timestamps"
    )


# ============================================================
# CLASSIFY TIMESTAMPS
# ============================================================

all_available = (
    result["available_corridors"] == 14
).sum()

all_missing = (
    result["available_corridors"] == 0
).sum()

partial = (
    (result["available_corridors"] > 0)
    &
    (result["available_corridors"] < 14)
).sum()


print("\n=== SYNCHRONIZATION SUMMARY ===")

print(f"All 14 available : {all_available}")
print(f"All 14 missing   : {all_missing}")
print(f"Partial coverage : {partial}")


# ============================================================
# PERCENTAGE
# ============================================================

total = len(result)

print("\n=== PERCENTAGE ===")

print(
    f"Fully observed : "
    f"{all_available / total * 100:.2f}%"
)

print(
    f"Fully missing  : "
    f"{all_missing / total * 100:.2f}%"
)

print(
    f"Partial        : "
    f"{partial / total * 100:.2f}%"
)


# ============================================================
# SAVE
# ============================================================

result.to_csv(
    OUTPUT_FILE,
    index=False
)


print("\n=== OUTPUT ===")
print(f"Synchronization analysis → {OUTPUT_FILE}")