import pandas as pd

from src.config import (
    CORRIDORS_PATH,
    TRAIN_PATH,
    HISTORY_PATH,
    DISPLAY_NAMES,
)


# ============================================================
# LIVE COLLECTOR PATH
# ============================================================

COLLECTED_PATH = (
    HISTORY_PATH.parents[2]
    / "collected"
    / "tomtom_flow_top14.csv"
)


# ============================================================
# LOAD 14 CORRIDORS
# ============================================================

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


# ============================================================
# PREPARE TRAFFIC DATA
# ============================================================

def prepare_history(df):

    if df.empty:
        return df

    df = df.copy()

    # Parse timestamp
    if "obs_time_utc" in df.columns:

        df["obs_time_utc"] = pd.to_datetime(
            df["obs_time_utc"],
            utc=True,
            errors="coerce"
        )

    # Pastikan station_id string
    if "station_id" in df.columns:

        df["station_id"] = (
            df["station_id"]
            .astype(str)
        )

    # Buat congestion_ratio jika belum ada
    if (
        "congestion_ratio" not in df.columns
        and "current_speed" in df.columns
        and "free_flow_speed" in df.columns
    ):

        df["congestion_ratio"] = (
            1
            - (
                df["current_speed"]
                / df["free_flow_speed"]
            )
        )

    # Jaga congestion ratio 0–1
    if "congestion_ratio" in df.columns:

        df["congestion_ratio"] = (
            pd.to_numeric(
                df["congestion_ratio"],
                errors="coerce"
            )
            .clip(
                lower=0,
                upper=1
            )
        )

    return df


# ============================================================
# LOAD HISTORICAL + NEW COLLECTOR DATA
# ============================================================

def load_history():

    datasets = []

    # --------------------------------------------------------
    # Historical dataset
    # --------------------------------------------------------

    if HISTORY_PATH.exists():

        historical = pd.read_csv(
            HISTORY_PATH
        )

        historical = prepare_history(
            historical
        )

        datasets.append(
            historical
        )


    # --------------------------------------------------------
    # Automatic collector dataset
    # --------------------------------------------------------

    if COLLECTED_PATH.exists():

        collected = pd.read_csv(
            COLLECTED_PATH
        )

        collected = prepare_history(
            collected
        )

        datasets.append(
            collected
        )


    # --------------------------------------------------------
    # No data
    # --------------------------------------------------------

    if not datasets:

        return pd.DataFrame()


    # --------------------------------------------------------
    # Merge
    # --------------------------------------------------------

    df = pd.concat(
        datasets,
        ignore_index=True,
        sort=False
    )


    # --------------------------------------------------------
    # Remove invalid rows
    # --------------------------------------------------------

    if "obs_time_utc" in df.columns:

        df = df.dropna(
            subset=["obs_time_utc"]
        )


    # --------------------------------------------------------
    # Remove duplicates
    #
    # Kalau timestamp + koridor sudah ada di historical,
    # versi collector terbaru dipertahankan.
    # --------------------------------------------------------

    if (
        "station_id" in df.columns
        and "obs_time_utc" in df.columns
    ):

        df = df.drop_duplicates(
            subset=[
                "station_id",
                "obs_time_utc"
            ],
            keep="last"
        )


    # --------------------------------------------------------
    # Sort chronologically
    # --------------------------------------------------------

    if (
        "station_id" in df.columns
        and "obs_time_utc" in df.columns
    ):

        df = df.sort_values(
            [
                "obs_time_utc",
                "station_id"
            ]
        )


    return df.reset_index(
        drop=True
    )