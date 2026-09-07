from pathlib import Path

import pandas as pd


# ============================================================
# PATH
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

FULL_DATA_DIR = ROOT / "full_data"

OUTPUT_DIR = ROOT / "data" / "processed"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "subset_analysis.csv"


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
        "file": file.name,
        "corridor": df["name"].iloc[0],
        "rows": len(df),
        "start": df["obs_time_utc"].min(),
        "end": df["obs_time_utc"].max(),
        "timestamps": set(df["obs_time_utc"])
    })


# ============================================================
# SORT BY TEMPORAL COVERAGE
# ============================================================

corridors = sorted(
    corridors,
    key=lambda x: x["rows"],
    reverse=True
)


print("\n=== SUBSET ANALYSIS ===")
print(f"Total corridor tersedia : {len(corridors)}")


# ============================================================
# TEST DIFFERENT SUBSET SIZES
# ============================================================

subset_sizes = [10, 14, 20, 24, 30, 40, 54, 64, 80, 96]

results = []


for n in subset_sizes:

    if n > len(corridors):
        continue

    subset = corridors[:n]

    # --------------------------------------------------------
    # Find timestamps available in ALL corridors
    # --------------------------------------------------------

    common = subset[0]["timestamps"].copy()

    for corridor in subset[1:]:
        common &= corridor["timestamps"]

    common = sorted(common)

    if len(common) > 0:

        start = common[0]
        end = common[-1]

        duration_hours = (
            end - start
        ).total_seconds() / 3600

    else:

        start = None
        end = None
        duration_hours = 0


    # --------------------------------------------------------
    # Total observations contained in selected subset
    # --------------------------------------------------------

    total_rows = sum(
        corridor["rows"]
        for corridor in subset
    )


    results.append({
        "num_corridors": n,
        "common_timestamps": len(common),
        "common_start": start,
        "common_end": end,
        "duration_hours": round(duration_hours, 2),
        "total_observations": total_rows
    })


# ============================================================
# RESULT DATAFRAME
# ============================================================

result_df = pd.DataFrame(results)


print("\n=== TRADE-OFF JUMLAH CORRIDOR VS TEMPORAL COVERAGE ===")

print(
    result_df[
        [
            "num_corridors",
            "common_timestamps",
            "duration_hours",
            "total_observations"
        ]
    ].to_string(index=False)
)


# ============================================================
# SHOW TOP 14 CORRIDORS
# ============================================================

print("\n=== TOP 14 CORRIDORS DENGAN HISTORY TERPANJANG ===")

for i, corridor in enumerate(corridors[:14], start=1):

    print(
        f"{i:2d}. "
        f"{corridor['corridor']:<40} "
        f"{corridor['rows']:>4} observations"
    )


# ============================================================
# SHOW TOP 24 CORRIDORS
# ============================================================

print("\n=== TAMBAHAN CORRIDOR 15-24 ===")

for i, corridor in enumerate(corridors[14:24], start=15):

    print(
        f"{i:2d}. "
        f"{corridor['corridor']:<40} "
        f"{corridor['rows']:>4} observations"
    )


# ============================================================
# SAVE OUTPUT
# ============================================================

result_df.to_csv(
    OUTPUT_FILE,
    index=False
)


print("\n=== OUTPUT ===")
print(f"Subset analysis → {OUTPUT_FILE}")