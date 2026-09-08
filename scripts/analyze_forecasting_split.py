from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "processed"

FILES = {
    "TRAIN": DATA_DIR / "forecasting_train_raw.csv",
    "VALIDATION": DATA_DIR / "forecasting_val_raw.csv",
    "TEST": DATA_DIR / "forecasting_test_raw.csv",
}


def analyze_split(name, path):
    df = pd.read_csv(path)

    df["obs_time_utc"] = pd.to_datetime(
        df["obs_time_utc"],
        utc=True
    )

    timestamps = (
        df["obs_time_utc"]
        .drop_duplicates()
        .sort_values()
        .reset_index(drop=True)
    )

    gaps = timestamps.diff().dropna()
    gap_hours = gaps.dt.total_seconds() / 3600

    print(f"\n=== {name} ===")
    print(f"Timestamps       : {len(timestamps)}")
    print(f"Start            : {timestamps.iloc[0]}")
    print(f"End              : {timestamps.iloc[-1]}")

    print("\nGap distribution:")
    print(gap_hours.value_counts().sort_index().to_string())

    print(f"\nLargest gap      : {gap_hours.max():.0f} hours")

    # Sequence baru dimulai setiap gap > 1 jam
    sequence_id = (gap_hours > 1).cumsum()

    # Timestamp pertama belum punya diff
    sequence_id = pd.concat(
        [pd.Series([0]), sequence_id],
        ignore_index=True
    )

    sequence_sizes = sequence_id.value_counts().sort_index()

    print(f"Sequences        : {len(sequence_sizes)}")
    print(f"Longest sequence : {sequence_sizes.max()} timestamps")
    print(f"Median sequence  : {sequence_sizes.median():.1f} timestamps")

    return timestamps


results = {}

for name, path in FILES.items():
    results[name] = analyze_split(name, path)


print("\n=== SPLIT BOUNDARIES ===")

train = results["TRAIN"]
val = results["VALIDATION"]
test = results["TEST"]

train_val_gap = (
    val.iloc[0] - train.iloc[-1]
).total_seconds() / 3600

val_test_gap = (
    test.iloc[0] - val.iloc[-1]
).total_seconds() / 3600

print(
    f"TRAIN -> VALIDATION : {train_val_gap:.0f} hours"
)

print(
    f"VALIDATION -> TEST  : {val_test_gap:.0f} hours"
)