import pandas as pd

from src.config import (
    CORRIDORS_PATH,
    TRAIN_PATH,
    HISTORY_PATH,
    DISPLAY_NAMES,
)


def load_top14():

    corridors = pd.read_csv(
        CORRIDORS_PATH
    )

    train = pd.read_csv(
        TRAIN_PATH
    )

    top14 = sorted(
        train["corridor_file"]
        .dropna()
        .astype(str)
        .unique()
    )

    corridors["station_id"] = (
        corridors["station_id"]
        .astype(str)
    )

    selected = corridors[
        corridors["station_id"].isin(top14)
    ].copy()

    selected = (
        selected
        .set_index("station_id")
        .loc[top14]
        .reset_index()
    )

    selected["display_name"] = (
        selected.apply(
            lambda row: (
                f"{DISPLAY_NAMES.get(row['station_id'], row['name'])}"
                f" — {row['name']}"
            ),
            axis=1
        )
    )

    return selected


def load_history():

    if not HISTORY_PATH.exists():
        return pd.DataFrame()

    df = pd.read_csv(
        HISTORY_PATH
    )

    # Parse timestamp
    if "obs_time_utc" in df.columns:

        df["obs_time_utc"] = pd.to_datetime(
            df["obs_time_utc"],
            utc=True
        )

    # Buat congestion_ratio jika belum ada
    if "congestion_ratio" not in df.columns:

        if (
            "current_speed" in df.columns
            and "free_flow_speed" in df.columns
        ):

            df["congestion_ratio"] = (
                1
                - (
                    df["current_speed"]
                    / df["free_flow_speed"]
                )
            )

            # Jaga supaya nilainya 0–1
            df["congestion_ratio"] = (
                df["congestion_ratio"]
                .clip(
                    lower=0,
                    upper=1
                )
            )

    return df