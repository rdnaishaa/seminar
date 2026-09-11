from pathlib import Path

import pandas as pd


# ============================================================
# PATH CONFIG
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

TRAIN_PATH = (
    ROOT
    / "data"
    / "processed"
    / "forecasting_train_preprocessed.csv"
)

FULL_DATA_DIR = (
    ROOT
    / "full_data"
)

COLLECTED_PATH = (
    ROOT
    / "collected"
    / "tomtom_flow_top14.csv"
)

OUTPUT_DIR = (
    ROOT
    / "data"
    / "web"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "historical_top14.csv"
)


# ============================================================
# LOAD TOP 14 CORRIDOR IDS
# ============================================================

def load_top14_ids():

    train = pd.read_csv(
        TRAIN_PATH
    )

    top14 = sorted(
        train["corridor_file"]
        .dropna()
        .astype(str)
        .unique()
    )

    if len(top14) != 14:
        raise ValueError(
            f"Expected 14 corridor, found {len(top14)}"
        )

    return top14


# ============================================================
# LOAD OLD HISTORICAL DATA
# ============================================================

def load_old_history(
    top14
):

    frames = []

    print()
    print("Loading historical full_data...")
    print()

    for station_id in top14:

        file_path = (
            FULL_DATA_DIR
            / f"{station_id}.csv"
        )

        if not file_path.exists():

            print(
                f"[MISSING] {station_id}"
            )

            continue


        df = pd.read_csv(
            file_path
        )


        # Tambahkan station_id karena
        # file lama tidak punya kolom ini
        df["station_id"] = (
            station_id
        )


        # Pastikan timestamp terbaca
        df["obs_time_utc"] = (
            pd.to_datetime(
                df["obs_time_utc"],
                utc=True
            )
        )


        frames.append(
            df
        )


        print(
            f"[OK] {station_id}: "
            f"{len(df)} rows"
        )


    if not frames:

        return pd.DataFrame()


    old_history = pd.concat(
        frames,
        ignore_index=True
    )


    return old_history


# ============================================================
# LOAD NEW COLLECTOR DATA
# ============================================================

def load_new_history():

    if not COLLECTED_PATH.exists():

        print()
        print(
            "Collector data belum ditemukan."
        )

        return pd.DataFrame()


    df = pd.read_csv(
        COLLECTED_PATH
    )


    df["obs_time_utc"] = (
        pd.to_datetime(
            df["obs_time_utc"],
            utc=True
        )
    )


    return df


# ============================================================
# STANDARDIZE COLUMNS
# ============================================================

def standardize_columns(
    df
):

    if df.empty:
        return df


    required_columns = [
        "station_id",
        "obs_time_utc",
        "name",
        "current_speed",
        "free_flow_speed",
        "current_travel_time",
        "free_flow_travel_time",
        "congestion_ratio",
        "road_closure",
        "confidence",
    ]


    # Kalau collector punya kolom ekstra,
    # kita cukup ambil kolom yang dibutuhkan web
    available = [
        col
        for col in required_columns
        if col in df.columns
    ]


    df = df[
        available
    ].copy()


    # Kalau congestion_ratio belum ada,
    # hitung dari current/free flow speed
    if (
        "congestion_ratio"
        not in df.columns
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

        df["congestion_ratio"] = (
            df["congestion_ratio"]
            .clip(
                lower=0,
                upper=1
            )
        )


    return df


# ============================================================
# BUILD FINAL HISTORICAL DATASET
# ============================================================

def build_historical_top14():

    top14 = load_top14_ids()


    print(
        "========================================="
    )

    print(
        "BUILD HISTORICAL TOP 14"
    )

    print(
        "========================================="
    )


    old_history = (
        load_old_history(
            top14
        )
    )


    new_history = (
        load_new_history()
    )


    old_history = (
        standardize_columns(
            old_history
        )
    )

    new_history = (
        standardize_columns(
            new_history
        )
    )


    frames = []


    if not old_history.empty:

        frames.append(
            old_history
        )


    if not new_history.empty:

        frames.append(
            new_history
        )


    if not frames:

        raise RuntimeError(
            "Tidak ada historical data."
        )


    combined = pd.concat(
        frames,
        ignore_index=True
    )


    # ========================================================
    # FILTER 14 CORRIDORS
    # ========================================================

    combined = combined[
        combined["station_id"]
        .isin(top14)
    ].copy()


    # ========================================================
    # REMOVE DUPLICATES
    # ========================================================

    combined = (
        combined
        .sort_values(
            [
                "obs_time_utc",
                "station_id"
            ]
        )
        .drop_duplicates(
            subset=[
                "obs_time_utc",
                "station_id"
            ],
            keep="last"
        )
        .reset_index(
            drop=True
        )
    )


    # ========================================================
    # SAVE
    # ========================================================

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )


    combined.to_csv(
        OUTPUT_PATH,
        index=False
    )


    # ========================================================
    # SUMMARY
    # ========================================================

    print()
    print(
        "========================================="
    )

    print(
        "DONE"
    )

    print(
        "========================================="
    )


    print(
        f"Rows           : {len(combined)}"
    )

    print(
        f"Corridors      : "
        f"{combined['station_id'].nunique()}"
    )

    print(
        f"First timestamp: "
        f"{combined['obs_time_utc'].min()}"
    )

    print(
        f"Last timestamp : "
        f"{combined['obs_time_utc'].max()}"
    )

    print(
        f"Output         : "
        f"{OUTPUT_PATH}"
    )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    build_historical_top14()