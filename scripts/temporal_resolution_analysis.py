from pathlib import Path
import pandas as pd


# =========================================================
# PATH SETUP
# =========================================================

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "full_data"
OUTPUT_DIR = ROOT_DIR / "data" / "processed"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# =========================================================
# LOAD REPRESENTATIVE LONG-COVERAGE CORRIDOR
# =========================================================
# 14 corridor terpanjang memiliki 392 common timestamps.
# Sudirman digunakan untuk menganalisis temporal grid bersama.

FILE = DATA_DIR / "tt_sudirman.csv"

df = pd.read_csv(FILE)

df["obs_time_utc"] = pd.to_datetime(
    df["obs_time_utc"],
    utc=True,
    errors="coerce"
)

df = (
    df
    .dropna(subset=["obs_time_utc"])
    .drop_duplicates(subset=["obs_time_utc"])
    .sort_values("obs_time_utc")
    .reset_index(drop=True)
)

timestamps = pd.DatetimeIndex(df["obs_time_utc"])


# =========================================================
# BASIC INFORMATION
# =========================================================

print("\n=== TEMPORAL RESOLUTION ANALYSIS ===")

print("Observed timestamps :", len(timestamps))
print("Start              :", timestamps.min())
print("End                :", timestamps.max())


# =========================================================
# ANALYZE REGULAR GRID
# =========================================================

def analyze_grid(freq, label):

    full_grid = pd.date_range(
        start=timestamps.min(),
        end=timestamps.max(),
        freq=freq,
        tz="UTC"
    )

    observed_set = set(timestamps)
    grid_set = set(full_grid)

    observed_on_grid = len(
        observed_set.intersection(grid_set)
    )

    missing_on_grid = len(
        grid_set - observed_set
    )

    coverage = (
        observed_on_grid / len(full_grid) * 100
        if len(full_grid) > 0
        else 0
    )

    print(f"\n=== {label} GRID ===")

    print("Expected timestamps :", len(full_grid))
    print("Observed on grid    :", observed_on_grid)
    print("Missing on grid     :", missing_on_grid)
    print(
        "Coverage            :",
        round(coverage, 2),
        "%"
    )

    return {
        "resolution": label,
        "expected_timestamps": len(full_grid),
        "observed_on_grid": observed_on_grid,
        "missing_on_grid": missing_on_grid,
        "coverage_percentage": round(
            coverage,
            2
        )
    }


# =========================================================
# 1-HOUR GRID
# =========================================================

result_1h = analyze_grid(
    "1h",
    "1-hour"
)


# =========================================================
# 2-HOUR GRID
# =========================================================

result_2h = analyze_grid(
    "2h",
    "2-hour"
)


# =========================================================
# 2-HOUR GRID WITH ALTERNATIVE OFFSET
# =========================================================
# Ada kemungkinan grid 2 jam lebih cocok jika dimulai
# satu jam setelah timestamp pertama.

alt_start = timestamps.min() + pd.Timedelta(hours=1)

alt_grid = pd.date_range(
    start=alt_start,
    end=timestamps.max(),
    freq="2h",
    tz="UTC"
)

observed_set = set(timestamps)
alt_set = set(alt_grid)

alt_observed = len(
    observed_set.intersection(alt_set)
)

alt_missing = len(
    alt_set - observed_set
)

alt_coverage = (
    alt_observed / len(alt_grid) * 100
    if len(alt_grid) > 0
    else 0
)

print("\n=== 2-HOUR GRID (ALTERNATIVE OFFSET) ===")

print("Grid starts         :", alt_start)
print("Expected timestamps :", len(alt_grid))
print("Observed on grid    :", alt_observed)
print("Missing on grid     :", alt_missing)
print(
    "Coverage            :",
    round(alt_coverage, 2),
    "%"
)


# =========================================================
# OBSERVATION PARITY
# =========================================================
# Mengecek apakah observasi lebih dominan berada pada
# kelompok jam genap atau ganjil.

hour_parity = (
    timestamps.hour % 2
)

even_count = (hour_parity == 0).sum()
odd_count = (hour_parity == 1).sum()

print("\n=== HOUR PARITY ===")

print("Even-hour observations :", even_count)
print("Odd-hour observations  :", odd_count)


# =========================================================
# SEQUENCE ANALYSIS BY TEMPORAL STEP
# =========================================================

def sequence_analysis(step_hours, label):

    temp = pd.DataFrame({
        "timestamp": timestamps
    })

    temp["gap_hours"] = (
        temp["timestamp"]
        .diff()
        .dt.total_seconds()
        / 3600
    )

    temp["new_sequence"] = (
        temp["gap_hours"].ne(step_hours)
    )

    temp["sequence_id"] = (
        temp["new_sequence"].cumsum()
    )

    sequences = (
        temp.groupby("sequence_id")
        .agg(
            start=("timestamp", "min"),
            end=("timestamp", "max"),
            length=("timestamp", "size")
        )
        .reset_index()
    )

    sequences = sequences.sort_values(
        "length",
        ascending=False
    )

    print(f"\n=== {label} CONTINUOUS SEQUENCES ===")

    print(
        "Number of sequences :",
        len(sequences)
    )

    print(
        "Longest sequence    :",
        sequences["length"].max(),
        "steps"
    )

    print(
        "Median sequence     :",
        sequences["length"].median(),
        "steps"
    )

    return sequences


seq_1h = sequence_analysis(
    1,
    "1-hour"
)

seq_2h = sequence_analysis(
    2,
    "2-hour"
)


# =========================================================
# FORECASTING WINDOW FEASIBILITY
# =========================================================

def count_windows(
    sequences,
    input_steps,
    horizon_steps
):

    required = (
        input_steps
        + horizon_steps
    )

    return int(
        sequences["length"]
        .apply(
            lambda length:
            max(
                0,
                length - required + 1
            )
        )
        .sum()
    )


print("\n=== WINDOW COMPARISON ===")

window_results = []

for resolution, sequences, step_hours in [
    ("1-hour", seq_1h, 1),
    ("2-hour", seq_2h, 2)
]:

    for input_steps in [3, 6]:
        for horizon_steps in [1, 3]:

            samples = count_windows(
                sequences,
                input_steps,
                horizon_steps
            )

            input_duration = (
                input_steps * step_hours
            )

            horizon_duration = (
                horizon_steps * step_hours
            )

            print(
                f"{resolution:<7} | "
                f"Input {input_steps} steps "
                f"({input_duration}h) → "
                f"Horizon {horizon_steps} steps "
                f"({horizon_duration}h) "
                f"| samples = {samples}"
            )

            window_results.append({
                "resolution": resolution,
                "input_steps": input_steps,
                "input_duration_hours":
                    input_duration,
                "horizon_steps": horizon_steps,
                "horizon_duration_hours":
                    horizon_duration,
                "possible_samples": samples
            })


# =========================================================
# SAVE RESULTS
# =========================================================

resolution_results = pd.DataFrame([
    result_1h,
    result_2h,
    {
        "resolution":
            "2-hour-alternative-offset",
        "expected_timestamps":
            len(alt_grid),
        "observed_on_grid":
            alt_observed,
        "missing_on_grid":
            alt_missing,
        "coverage_percentage":
            round(alt_coverage, 2)
    }
])

resolution_output = (
    OUTPUT_DIR
    / "temporal_resolution_comparison.csv"
)

resolution_results.to_csv(
    resolution_output,
    index=False
)


window_output = (
    OUTPUT_DIR
    / "temporal_window_comparison.csv"
)

pd.DataFrame(
    window_results
).to_csv(
    window_output,
    index=False
)


seq_1h.to_csv(
    OUTPUT_DIR / "sequences_1h.csv",
    index=False
)

seq_2h.to_csv(
    OUTPUT_DIR / "sequences_2h.csv",
    index=False
)


print("\n=== OUTPUT ===")

print(
    "Resolution comparison →",
    resolution_output
)

print(
    "Window comparison     →",
    window_output
)