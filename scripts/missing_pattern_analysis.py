from pathlib import Path

import pandas as pd


# ============================================================
# PATH
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

FULL_DATA_DIR = ROOT / "full_data"

OUTPUT_DIR = ROOT / "data" / "processed"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SUMMARY_FILE = OUTPUT_DIR / "missing_pattern_summary.csv"
GAPS_FILE = OUTPUT_DIR / "missing_gap_sequences.csv"


# ============================================================
# LOAD CORRIDORS
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
        "file": file,
        "name": df["name"].iloc[0],
        "rows": len(df),
        "df": df
    })


# ============================================================
# SELECT TOP 14
# ============================================================

corridors = sorted(
    corridors,
    key=lambda x: x["rows"],
    reverse=True
)

selected = corridors[:14]


print("\n=== MISSING PATTERN ANALYSIS ===")
print(f"Selected corridors : {len(selected)}")


# ============================================================
# FIND COMMON TIME RANGE
# ============================================================

start = max(
    c["df"]["obs_time_utc"].min()
    for c in selected
)

end = min(
    c["df"]["obs_time_utc"].max()
    for c in selected
)


hourly_grid = pd.date_range(
    start=start,
    end=end,
    freq="1h"
)


print(f"Common start       : {start}")
print(f"Common end         : {end}")
print(f"Expected hourly    : {len(hourly_grid)}")


# ============================================================
# ANALYZE EACH CORRIDOR
# ============================================================

summary_rows = []
gap_rows = []


for corridor in selected:

    name = corridor["name"]
    df = corridor["df"]

    observed = set(df["obs_time_utc"])

    missing_mask = [
        timestamp not in observed
        for timestamp in hourly_grid
    ]

    missing_count = sum(missing_mask)

    coverage = (
        (len(hourly_grid) - missing_count)
        / len(hourly_grid)
        * 100
    )


    # --------------------------------------------------------
    # FIND CONSECUTIVE MISSING SEQUENCES
    # --------------------------------------------------------

    gap_lengths = []

    current_gap = 0
    gap_start = None


    for timestamp, missing in zip(
        hourly_grid,
        missing_mask
    ):

        if missing:

            if current_gap == 0:
                gap_start = timestamp

            current_gap += 1

        else:

            if current_gap > 0:

                gap_end = timestamp - pd.Timedelta(hours=1)

                gap_lengths.append(current_gap)

                gap_rows.append({
                    "corridor": name,
                    "gap_start": gap_start,
                    "gap_end": gap_end,
                    "gap_length_hours": current_gap
                })

                current_gap = 0
                gap_start = None


    # handle gap at end

    if current_gap > 0:

        gap_lengths.append(current_gap)

        gap_rows.append({
            "corridor": name,
            "gap_start": gap_start,
            "gap_end": hourly_grid[-1],
            "gap_length_hours": current_gap
        })


    # --------------------------------------------------------
    # GAP STATISTICS
    # --------------------------------------------------------

    if gap_lengths:

        largest_gap = max(gap_lengths)

        one_hour_gaps = sum(
            1 for g in gap_lengths if g == 1
        )

        two_hour_gaps = sum(
            1 for g in gap_lengths if g == 2
        )

        long_gaps = sum(
            1 for g in gap_lengths if g >= 3
        )

    else:

        largest_gap = 0
        one_hour_gaps = 0
        two_hour_gaps = 0
        long_gaps = 0


    summary_rows.append({
        "corridor": name,
        "expected_hours": len(hourly_grid),
        "observed_hours": len(hourly_grid) - missing_count,
        "missing_hours": missing_count,
        "coverage_percentage": round(coverage, 2),
        "num_gap_sequences": len(gap_lengths),
        "one_hour_gaps": one_hour_gaps,
        "two_hour_gaps": two_hour_gaps,
        "long_gaps_3h_plus": long_gaps,
        "largest_missing_gap_hours": largest_gap
    })


# ============================================================
# DATAFRAMES
# ============================================================

summary_df = pd.DataFrame(summary_rows)

gaps_df = pd.DataFrame(gap_rows)


# ============================================================
# PRINT SUMMARY
# ============================================================

print("\n=== HOURLY COVERAGE PER CORRIDOR ===")

print(
    summary_df[
        [
            "corridor",
            "observed_hours",
            "missing_hours",
            "coverage_percentage",
            "largest_missing_gap_hours"
        ]
    ].to_string(index=False)
)


# ============================================================
# GLOBAL GAP DISTRIBUTION
# ============================================================

print("\n=== MISSING GAP DISTRIBUTION ===")

if not gaps_df.empty:

    distribution = (
        gaps_df["gap_length_hours"]
        .value_counts()
        .sort_index()
    )

    for length, count in distribution.items():

        print(
            f"{length:3d} hour missing gap : "
            f"{count:4d} sequences"
        )


# ============================================================
# LONGEST GAPS
# ============================================================

print("\n=== 15 LONGEST MISSING GAPS ===")

if not gaps_df.empty:

    longest = (
        gaps_df
        .sort_values(
            "gap_length_hours",
            ascending=False
        )
        .head(15)
    )

    print(
        longest.to_string(index=False)
    )


# ============================================================
# SAVE OUTPUT
# ============================================================

summary_df.to_csv(
    SUMMARY_FILE,
    index=False
)

gaps_df.to_csv(
    GAPS_FILE,
    index=False
)


print("\n=== OUTPUT ===")
print(f"Summary → {SUMMARY_FILE}")
print(f"Gaps    → {GAPS_FILE}")