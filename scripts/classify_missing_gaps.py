from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "processed"

FILES = {
    "TRAIN": DATA_DIR / "forecasting_train_hourly_grid.csv",
    "VALIDATION": DATA_DIR / "forecasting_val_hourly_grid.csv",
    "TEST": DATA_DIR / "forecasting_test_hourly_grid.csv",
}

for split_name, path in FILES.items():

    df = pd.read_csv(path)

    df["obs_time_utc"] = pd.to_datetime(
        df["obs_time_utc"],
        utc=True
    )

    # Karena missing sinkron antar-corridor,
    # cukup lihat status per timestamp.
    status = (
        df.groupby("obs_time_utc")["is_observed"]
        .any()
        .sort_index()
    )

    missing = ~status

    # Kelompokkan consecutive missing timestamps
    groups = (missing != missing.shift()).cumsum()

    gap_lengths = (
        missing[missing]
        .groupby(groups[missing])
        .size()
    )

    print(f"\n=== {split_name} ===")

    if len(gap_lengths) == 0:
        print("Tidak ada missing gap.")
        continue

    distribution = (
        gap_lengths
        .value_counts()
        .sort_index()
    )

    print("Missing gap length distribution:")
    for length, count in distribution.items():
        print(
            f"{length:>3} hour gap : "
            f"{count} sequence(s)"
        )

    isolated = gap_lengths[gap_lengths == 1]

    print(f"\nTotal missing hours     : {gap_lengths.sum()}")
    print(f"Isolated 1h gaps        : {len(isolated)}")
    print(
        f"Hours in isolated gaps  : "
        f"{isolated.sum()}"
    )

    long_gaps = gap_lengths[gap_lengths > 1]

    print(
        f"Long gap sequences      : "
        f"{len(long_gaps)}"
    )

    if len(long_gaps) > 0:
        print(
            f"Hours inside long gaps  : "
            f"{long_gaps.sum()}"
        )
        print(
            f"Largest missing gap     : "
            f"{long_gaps.max()} hours"
        )