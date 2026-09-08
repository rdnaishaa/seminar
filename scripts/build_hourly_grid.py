from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "processed"

FILES = {
    "train": DATA_DIR / "forecasting_train_raw.csv",
    "val": DATA_DIR / "forecasting_val_raw.csv",
    "test": DATA_DIR / "forecasting_test_raw.csv",
}

for split_name, path in FILES.items():

    df = pd.read_csv(path)

    df["obs_time_utc"] = pd.to_datetime(
        df["obs_time_utc"],
        utc=True
    )

    corridors = sorted(df["corridor_file"].unique())

    start = df["obs_time_utc"].min()
    end = df["obs_time_utc"].max()

    # Buat timestamp setiap 1 jam
    hourly_times = pd.date_range(
        start=start,
        end=end,
        freq="1h"
    )

    # Kombinasi seluruh timestamp x 14 corridor
    full_index = pd.MultiIndex.from_product(
        [hourly_times, corridors],
        names=["obs_time_utc", "corridor_file"]
    )

    original = df.set_index(
        ["obs_time_utc", "corridor_file"]
    )

    grid = original.reindex(full_index).reset_index()

    # Tandai apakah baris asli atau missing hasil grid
    grid["is_observed"] = grid["current_speed"].notna()

    total_hours = len(hourly_times)
    observed_hours = (
        grid.loc[grid["is_observed"], "obs_time_utc"]
        .nunique()
    )
    missing_hours = total_hours - observed_hours

    print(f"\n=== {split_name.upper()} ===")
    print(f"Corridors      : {len(corridors)}")
    print(f"Hourly steps   : {total_hours}")
    print(f"Observed hours : {observed_hours}")
    print(f"Missing hours  : {missing_hours}")
    print(
        f"Coverage       : "
        f"{observed_hours / total_hours * 100:.2f}%"
    )

    output = DATA_DIR / f"forecasting_{split_name}_hourly_grid.csv"

    grid.to_csv(output, index=False)

    print(f"Saved          : {output.name}")