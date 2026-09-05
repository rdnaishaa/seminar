from pathlib import Path
from collections import Counter

import pandas as pd


# =========================
# PATH SETUP
# =========================

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "full_data"
OUTPUT_DIR = ROOT_DIR / "data" / "processed"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# =========================
# READ ALL CORRIDORS
# =========================

corridors = []

for file in sorted(DATA_DIR.glob("*.csv")):
    df = pd.read_csv(file)

    df["obs_time_utc"] = pd.to_datetime(
        df["obs_time_utc"],
        utc=True,
        errors="coerce"
    )

    # Buang timestamp invalid jika ada
    df = df.dropna(subset=["obs_time_utc"])

    # Hilangkan duplicate timestamp
    df = df.drop_duplicates(subset=["obs_time_utc"])

    # Urutkan berdasarkan waktu
    df = df.sort_values("obs_time_utc")

    corridors.append({
        "file": file.name,
        "corridor": (
            df["name"].iloc[0]
            if len(df) > 0
            else file.stem
        ),
        "rows": len(df),
        "start": df["obs_time_utc"].min(),
        "end": df["obs_time_utc"].max(),
        "timestamps": set(df["obs_time_utc"])
    })


# =========================
# ROW DISTRIBUTION
# =========================

row_counts = Counter(
    corridor["rows"]
    for corridor in corridors
)

print("\n=== DISTRIBUSI JUMLAH OBSERVASI ===")

for rows, count in sorted(
    row_counts.items(),
    reverse=True
):
    print(
        f"{rows:4d} observasi : "
        f"{count:2d} corridor"
    )


# =========================
# LONGEST CORRIDORS
# =========================

corridors_sorted = sorted(
    corridors,
    key=lambda x: x["rows"],
    reverse=True
)

print("\n=== 20 CORRIDOR DENGAN DATA TERBANYAK ===")

for i, c in enumerate(
    corridors_sorted[:20],
    start=1
):
    print(
        f"{i:2d}. "
        f"{c['corridor']:<35} "
        f"{c['rows']:4d} observasi | "
        f"{c['start']} → {c['end']}"
    )


# =========================
# SAME START DATE
# =========================

earliest_start = min(
    c["start"]
    for c in corridors
)

earliest_corridors = [
    c
    for c in corridors
    if c["start"] == earliest_start
]

print("\n=== COVERAGE AWAL DATASET ===")

print("Timestamp paling awal :", earliest_start)

print(
    "Corridor yang sudah ada sejak timestamp awal :",
    len(earliest_corridors)
)


# =========================
# TIMESTAMP COVERAGE
# =========================

timestamp_counter = Counter()

for corridor in corridors:
    for timestamp in corridor["timestamps"]:
        timestamp_counter[timestamp] += 1

coverage_df = pd.DataFrame(
    [
        {
            "timestamp": timestamp,
            "corridors_available": count
        }
        for timestamp, count
        in timestamp_counter.items()
    ]
)

coverage_df = coverage_df.sort_values(
    "timestamp"
)

print("\n=== TIMESTAMP COVERAGE ===")

print(
    "Jumlah timestamp unik :",
    len(coverage_df)
)

print(
    "Maximum corridor pada satu timestamp :",
    coverage_df["corridors_available"].max()
)

print(
    "Minimum corridor pada satu timestamp :",
    coverage_df["corridors_available"].min()
)

print(
    "Rata-rata corridor tersedia per timestamp :",
    round(
        coverage_df["corridors_available"].mean(),
        2
    )
)


# =========================
# COVERAGE THRESHOLDS
# =========================

print("\n=== JUMLAH TIMESTAMP BERDASARKAN COVERAGE ===")

thresholds = [
    96,
    90,
    80,
    70,
    60,
    50,
    40,
    30,
    20
]

for threshold in thresholds:
    count = (
        coverage_df["corridors_available"]
        >= threshold
    ).sum()

    print(
        f">= {threshold:2d} corridor : "
        f"{count:4d} timestamp"
    )


# =========================
# COMMON TIMESTAMPS
# TOP-N BEST CORRIDORS
# =========================

print("\n=== COMMON TIMESTAMPS TOP-N CORRIDORS ===")

top_n_values = [
    10,
    20,
    30,
    40,
    50,
    60,
    96
]

subset_results = []

for n in top_n_values:

    selected = corridors_sorted[:n]

    common_timestamps = set.intersection(
        *[
            c["timestamps"]
            for c in selected
        ]
    )

    subset_results.append({
        "number_of_corridors": n,
        "common_timestamps": len(
            common_timestamps
        )
    })

    print(
        f"Top {n:2d} corridor → "
        f"{len(common_timestamps):4d} "
        f"common timestamps"
    )


# =========================
# SAVE RESULTS
# =========================

coverage_output = (
    OUTPUT_DIR
    / "temporal_coverage.csv"
)

coverage_df.to_csv(
    coverage_output,
    index=False
)


subset_output = (
    OUTPUT_DIR
    / "corridor_subset_coverage.csv"
)

pd.DataFrame(
    subset_results
).to_csv(
    subset_output,
    index=False
)


print("\n=== OUTPUT ===")

print(
    "Temporal coverage →",
    coverage_output
)

print(
    "Subset coverage   →",
    subset_output
)