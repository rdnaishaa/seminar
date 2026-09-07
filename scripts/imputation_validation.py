from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error


# ============================================================
# PATH
# ============================================================

ROOT = Path(__file__).resolve().parents[1]
FULL_DATA_DIR = ROOT / "full_data"

OUTPUT_DIR = ROOT / "data" / "processed"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

RESULT_FILE = OUTPUT_DIR / "imputation_validation.csv"


# ============================================================
# SELECT TOP 14 CORRIDORS
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


corridors = sorted(
    corridors,
    key=lambda x: x["rows"],
    reverse=True
)[:14]


# ============================================================
# FEATURES TO VALIDATE
# ============================================================

features = [
    "current_speed",
    "congestion_ratio"
]


# ============================================================
# VALIDATION
# ============================================================

results = []


for corridor in corridors:

    name = corridor["name"]

    df = corridor["df"].copy()

    df = df.set_index("obs_time_utc")

    for feature in features:

        series = df[feature].copy()

        # ----------------------------------------------------
        # Find timestamps where:
        # previous hour exists
        # current hour exists
        # next hour exists
        # ----------------------------------------------------

        valid_points = []

        timestamps = series.index

        timestamp_set = set(timestamps)

        for timestamp in timestamps:

            prev_time = timestamp - pd.Timedelta(hours=1)
            next_time = timestamp + pd.Timedelta(hours=1)

            if (
                prev_time in timestamp_set
                and next_time in timestamp_set
            ):
                valid_points.append(timestamp)


        if len(valid_points) == 0:
            continue


        actual_values = []
        predicted_values = []


        for timestamp in valid_points:

            prev_time = timestamp - pd.Timedelta(hours=1)
            next_time = timestamp + pd.Timedelta(hours=1)

            prev_value = series.loc[prev_time]
            actual_value = series.loc[timestamp]
            next_value = series.loc[next_time]

            # -----------------------------------------------
            # Linear interpolation
            # -----------------------------------------------

            predicted_value = (
                prev_value + next_value
            ) / 2


            actual_values.append(actual_value)
            predicted_values.append(predicted_value)


        # ----------------------------------------------------
        # METRICS
        # ----------------------------------------------------

        mae = mean_absolute_error(
            actual_values,
            predicted_values
        )

        rmse = np.sqrt(
            mean_squared_error(
                actual_values,
                predicted_values
            )
        )


        results.append({
            "corridor": name,
            "feature": feature,
            "validation_points": len(valid_points),
            "mae": mae,
            "rmse": rmse
        })


# ============================================================
# RESULTS
# ============================================================

result_df = pd.DataFrame(results)


print("\n=== IMPUTATION VALIDATION ===")

print(
    result_df.to_string(
        index=False
    )
)


# ============================================================
# GLOBAL SUMMARY
# ============================================================

print("\n=== GLOBAL SUMMARY ===")

summary = (
    result_df
    .groupby("feature")
    .agg(
        total_validation_points=("validation_points", "sum"),
        mean_mae=("mae", "mean"),
        mean_rmse=("rmse", "mean")
    )
    .reset_index()
)

print(
    summary.to_string(
        index=False
    )
)


# ============================================================
# SAVE
# ============================================================

result_df.to_csv(
    RESULT_FILE,
    index=False
)

print("\n=== OUTPUT ===")
print(f"Validation result → {RESULT_FILE}")