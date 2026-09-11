import pandas as pd


def get_latest_status(history):

    if history.empty:
        return pd.DataFrame()

    df = history.copy()

    latest_time = df["obs_time_utc"].max()

    latest = df[
        df["obs_time_utc"] == latest_time
    ].copy()

    return latest


def get_corridor_history(
    history,
    station_id
):

    if history.empty:
        return pd.DataFrame()

    df = history[
        history["station_id"] == station_id
    ].copy()

    df = df.sort_values(
        "obs_time_utc"
    )

    return df


def hourly_profile(
    history,
    station_id
):

    df = get_corridor_history(
        history,
        station_id
    )

    if df.empty:
        return pd.DataFrame()

    df["hour_utc"] = (
        df["obs_time_utc"].dt.hour
    )

    # WIB = UTC + 7
    df["hour_wib"] = (
        df["hour_utc"] + 7
    ) % 24

    profile = (
        df.groupby("hour_wib")
        .agg(
            avg_speed=(
                "current_speed",
                "mean"
            ),
            avg_free_flow_speed=(
                "free_flow_speed",
                "mean"
            ),
            avg_congestion_ratio=(
                "congestion_ratio",
                "mean"
            ),
            observations=(
                "current_speed",
                "count"
            )
        )
        .reset_index()
        .sort_values("hour_wib")
    )

    return profile


def get_best_worst_hour(
    history,
    station_id
):

    profile = hourly_profile(
        history,
        station_id
    )

    if profile.empty:
        return None

    # Jangan simpulkan best/worst jika
    # jumlah jam historis belum cukup
    if profile["hour_wib"].nunique() < 3:
        return None

    best = profile.loc[
        profile["avg_speed"].idxmax()
    ]

    worst = profile.loc[
        profile["avg_speed"].idxmin()
    ]

    return {
        "best_hour": int(
            best["hour_wib"]
        ),
        "best_speed": float(
            best["avg_speed"]
        ),
        "worst_hour": int(
            worst["hour_wib"]
        ),
        "worst_speed": float(
            worst["avg_speed"]
        ),
    }