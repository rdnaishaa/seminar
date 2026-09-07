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

DETAIL_FILE = OUTPUT_DIR / "imputation_comparison_detail.csv"
SUMMARY_FILE = OUTPUT_DIR / "imputation_comparison_summary.csv"


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
        "df": df
    })


corridors = sorted(
    corridors,
    key=lambda x: x["rows"],
    reverse=True
)[:14]


# ============================================================
# FEATURES
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

        series = df[feature].dropna().copy()

        timestamp_set = set(series.index)

        actual = []
        forward_predictions = []
        backward_predictions = []
        linear_predictions = []


        # ----------------------------------------------------
        # Only use points with actual t-1 and t+1
        # ----------------------------------------------------

        for timestamp in series.index:

            previous_time = (
                timestamp - pd.Timedelta(hours=1)
            )

            next_time = (
                timestamp + pd.Timedelta(hours=1)
            )

            if (
                previous_time not in timestamp_set
                or next_time not in timestamp_set
            ):
                continue


            previous_value = series.loc[previous_time]
            actual_value = series.loc[timestamp]
            next_value = series.loc[next_time]


            # -----------------------------------------------
            # THREE IMPUTATION METHODS
            # -----------------------------------------------

            forward_value = previous_value

            backward_value = next_value

            linear_value = (
                previous_value + next_value
            ) / 2


            actual.append(actual_value)

            forward_predictions.append(
                forward_value
            )

            backward_predictions.append(
                backward_value
            )

            linear_predictions.append(
                linear_value
            )


        if len(actual) == 0:
            continue


        # ----------------------------------------------------
        # CALCULATE ERROR FOR EACH METHOD
        # ----------------------------------------------------

        methods = {
            "forward_fill": forward_predictions,
            "backward_fill": backward_predictions,
            "linear_interpolation": linear_predictions
        }


        for method, prediction in methods.items():

            mae = mean_absolute_error(
                actual,
                prediction
            )

            rmse = np.sqrt(
                mean_squared_error(
                    actual,
                    prediction
                )
            )


            results.append({
                "corridor": name,
                "feature": feature,
                "method": method,
                "validation_points": len(actual),
                "mae": mae,
                "rmse": rmse
            })


# ============================================================
# DETAIL RESULTS
# ============================================================

result_df = pd.DataFrame(results)


print("\n=== IMPUTATION METHOD COMPARISON ===")

print(
    result_df.to_string(
        index=False
    )
)


# ============================================================
# GLOBAL SUMMARY
# ============================================================

summary = (
    result_df
    .groupby(
        ["feature", "method"]
    )
    .agg(
        total_validation_points=(
            "validation_points",
            "sum"
        ),
        mean_mae=(
            "mae",
            "mean"
        ),
        mean_rmse=(
            "rmse",
            "mean"
        )
    )
    .reset_index()
)


print("\n=== GLOBAL COMPARISON ===")

print(
    summary.to_string(
        index=False
    )
)


# ============================================================
# BEST METHOD
# ============================================================

print("\n=== BEST METHOD BY FEATURE ===")

for feature in features:

    feature_result = summary[
        summary["feature"] == feature
    ]

    best_mae = feature_result.loc[
        feature_result["mean_mae"].idxmin()
    ]

    best_rmse = feature_result.loc[
        feature_result["mean_rmse"].idxmin()
    ]

    print(f"\nFeature: {feature}")

    print(
        f"Best MAE  : {best_mae['method']} "
        f"({best_mae['mean_mae']:.6f})"
    )

    print(
        f"Best RMSE : {best_rmse['method']} "
        f"({best_rmse['mean_rmse']:.6f})"
    )


# ============================================================
# SAVE
# ============================================================

result_df.to_csv(
    DETAIL_FILE,
    index=False
)

summary.to_csv(
    SUMMARY_FILE,
    index=False
)


print("\n=== OUTPUT ===")

print(
    f"Detail  → {DETAIL_FILE}"
)

print(
    f"Summary → {SUMMARY_FILE}"
)