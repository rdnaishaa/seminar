from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
FULL_DATA_DIR = ROOT / "full_data"

OUTPUT_DIR = ROOT / "data" / "processed"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "preprocessing_strategy_analysis.csv"


# ============================================================
# LOAD TOP 14 CORRIDORS
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


corridors = sorted(
    corridors,
    key=lambda x: x["rows"],
    reverse=True
)[:14]


# ============================================================
# SINCE TOP 14 ARE PERFECTLY SYNCHRONIZED,
# USE FIRST CORRIDOR AS TEMPORAL AVAILABILITY
# ============================================================

observed = corridors[0]["timestamps"]

start = min(observed)
end = max(observed)

grid = pd.date_range(
    start=start,
    end=end,
    freq="1h"
)


raw_available = pd.Series(
    [timestamp in observed for timestamp in grid],
    index=grid
)


# ============================================================
# FILL ONLY SINGLE-HOUR GAPS
# ============================================================

fill_1h = raw_available.copy()

for i in range(1, len(fill_1h) - 1):

    previous_available = fill_1h.iloc[i - 1]
    current_available = fill_1h.iloc[i]
    next_available = fill_1h.iloc[i + 1]

    if (
        previous_available
        and not current_available
        and next_available
    ):
        fill_1h.iloc[i] = True


# ============================================================
# ALL-FILLED SCENARIO
# only comparison, NOT recommended preprocessing
# ============================================================

fill_all = pd.Series(
    True,
    index=grid
)


# ============================================================
# FIND CONTINUOUS SEQUENCES
# ============================================================

def get_sequences(series):

    sequences = []
    current = 0

    for available in series:

        if available:
            current += 1

        else:

            if current > 0:
                sequences.append(current)

            current = 0

    if current > 0:
        sequences.append(current)

    return sequences


# ============================================================
# COUNT FORECAST WINDOWS
# ============================================================

def count_windows(sequences, input_steps, horizon_steps):

    required = input_steps + horizon_steps

    total = 0

    for length in sequences:

        if length >= required:

            total += (
                length
                - required
                + 1
            )

    return total


# ============================================================
# ANALYZE STRATEGIES
# ============================================================

strategies = {
    "raw": raw_available,
    "fill_1h_gap": fill_1h,
    "fill_all": fill_all
}


results = []


print("\n=== PREPROCESSING STRATEGY ANALYSIS ===")


for strategy_name, series in strategies.items():

    sequences = get_sequences(series)

    observed_steps = int(series.sum())
    missing_steps = len(series) - observed_steps

    longest = max(sequences) if sequences else 0

    median = (
        pd.Series(sequences).median()
        if sequences
        else 0
    )


    print(f"\n--- {strategy_name.upper()} ---")

    print(f"Available steps       : {observed_steps}")
    print(f"Missing steps         : {missing_steps}")
    print(f"Number of sequences   : {len(sequences)}")
    print(f"Longest sequence      : {longest}")
    print(f"Median sequence       : {median}")


    # --------------------------------------------------------
    # FORECAST WINDOW CANDIDATES
    # --------------------------------------------------------

    configurations = [
        (3, 1),
        (3, 3),
        (3, 6),
        (6, 1),
        (6, 3),
        (6, 6),
        (12, 1),
        (12, 3),
        (12, 6)
    ]


    for input_steps, horizon_steps in configurations:

        windows = count_windows(
            sequences,
            input_steps,
            horizon_steps
        )

        print(
            f"Input {input_steps:2d}h "
            f"→ Horizon {horizon_steps:2d}h "
            f"| windows = {windows}"
        )

        results.append({
            "strategy": strategy_name,
            "available_steps": observed_steps,
            "missing_steps": missing_steps,
            "num_sequences": len(sequences),
            "longest_sequence": longest,
            "median_sequence": median,
            "input_steps": input_steps,
            "horizon_steps": horizon_steps,
            "forecast_windows": windows
        })


# ============================================================
# SAVE
# ============================================================

result_df = pd.DataFrame(results)

result_df.to_csv(
    OUTPUT_FILE,
    index=False
)


print("\n=== OUTPUT ===")
print(f"Strategy analysis → {OUTPUT_FILE}")