from pathlib import Path
import pandas as pd


# =========================
# PATH SETUP
# =========================

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "full_data"
OUTPUT_DIR = ROOT_DIR / "data" / "processed"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# =========================
# USE LONGEST-COVERAGE CORRIDOR
# =========================
# 14 corridor dengan 392 observasi memiliki timestamp yang sama.
# Kita gunakan Sudirman sebagai representasi grid waktunya.

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


# =========================
# UTC -> WIB
# =========================

df["obs_time_wib"] = (
    df["obs_time_utc"]
    .dt.tz_convert("Asia/Jakarta")
)

df["date_wib"] = df["obs_time_wib"].dt.date
df["hour_wib"] = df["obs_time_wib"].dt.hour
df["day_wib"] = df["obs_time_wib"].dt.day_name()


# =========================
# TIME GAPS
# =========================

df["gap_hours"] = (
    df["obs_time_utc"]
    .diff()
    .dt.total_seconds()
    / 3600
)


print("\n=== TEMPORAL REGULARITY ===")

print("Jumlah timestamp :", len(df))
print("Mulai UTC        :", df["obs_time_utc"].min())
print("Akhir UTC        :", df["obs_time_utc"].max())

print("Mulai WIB        :", df["obs_time_wib"].min())
print("Akhir WIB        :", df["obs_time_wib"].max())


# =========================
# GAP DISTRIBUTION
# =========================

print("\n=== DISTRIBUSI GAP ===")

gap_distribution = (
    df["gap_hours"]
    .dropna()
    .value_counts()
    .sort_index()
)

for gap, count in gap_distribution.items():
    print(
        f"{gap:6.1f} jam : "
        f"{count:4d} kali"
    )


# =========================
# OBSERVATION BY WIB HOUR
# =========================

print("\n=== OBSERVASI BERDASARKAN JAM WIB ===")

hour_distribution = (
    df["hour_wib"]
    .value_counts()
    .sort_index()
)

for hour, count in hour_distribution.items():
    print(
        f"{hour:02d}:00 WIB : "
        f"{count:3d} observasi"
    )


# =========================
# OBSERVATION BY DAY
# =========================

print("\n=== OBSERVASI BERDASARKAN HARI ===")

day_order = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday"
]

day_distribution = (
    df["day_wib"]
    .value_counts()
    .reindex(day_order)
    .fillna(0)
    .astype(int)
)

for day, count in day_distribution.items():
    print(
        f"{day:<10} : "
        f"{count:3d} observasi"
    )


# =========================
# CONTINUOUS HOURLY RUNS
# =========================

# Sequence baru dimulai setiap kali gap bukan 1 jam.

df["new_sequence"] = (
    df["gap_hours"].ne(1)
)

df["sequence_id"] = (
    df["new_sequence"]
    .cumsum()
)

sequence_summary = (
    df.groupby("sequence_id")
    .agg(
        start_wib=("obs_time_wib", "min"),
        end_wib=("obs_time_wib", "max"),
        length=("obs_time_wib", "size")
    )
    .reset_index()
)

sequence_summary = sequence_summary.sort_values(
    "length",
    ascending=False
)


print("\n=== CONTINUOUS HOURLY SEQUENCES ===")

print(
    "Jumlah sequence kontinu :",
    len(sequence_summary)
)

print(
    "Sequence terpanjang      :",
    sequence_summary["length"].max(),
    "jam"
)

print(
    "Median panjang sequence  :",
    sequence_summary["length"].median(),
    "jam"
)


print("\n=== 10 SEQUENCE TERPANJANG ===")

print(
    sequence_summary[
        [
            "start_wib",
            "end_wib",
            "length"
        ]
    ]
    .head(10)
    .to_string(index=False)
)


# =========================
# FORECAST WINDOW FEASIBILITY
# =========================

# Contoh:
# input 6 jam -> prediksi 1/3/6 jam ke depan.
# Untuk window input=6 dan horizon=3,
# minimal continuous run = 9 timestamp.

print("\n=== FORECAST WINDOW FEASIBILITY ===")

input_windows = [3, 6, 12]
horizons = [1, 3, 6]

feasibility_results = []

for input_window in input_windows:
    for horizon in horizons:

        required_length = input_window + horizon

        possible_samples = (
            sequence_summary["length"]
            .apply(
                lambda length:
                max(
                    0,
                    length - required_length + 1
                )
            )
            .sum()
        )

        feasibility_results.append({
            "input_hours": input_window,
            "horizon_hours": horizon,
            "required_continuous_hours": required_length,
            "possible_samples": int(possible_samples)
        })

        print(
            f"Input {input_window:2d}h "
            f"→ Horizon {horizon:2d}h "
            f"| minimum run {required_length:2d}h "
            f"| possible samples = {int(possible_samples)}"
        )


# =========================
# SAVE RESULTS
# =========================

sequence_output = (
    OUTPUT_DIR
    / "continuous_sequences.csv"
)

sequence_summary.to_csv(
    sequence_output,
    index=False
)


feasibility_output = (
    OUTPUT_DIR
    / "forecast_window_feasibility.csv"
)

pd.DataFrame(
    feasibility_results
).to_csv(
    feasibility_output,
    index=False
)


regularity_output = (
    OUTPUT_DIR
    / "temporal_regularity.csv"
)

df[
    [
        "obs_time_utc",
        "obs_time_wib",
        "date_wib",
        "hour_wib",
        "day_wib",
        "gap_hours",
        "sequence_id"
    ]
].to_csv(
    regularity_output,
    index=False
)


print("\n=== OUTPUT ===")

print(
    "Temporal regularity →",
    regularity_output
)

print(
    "Continuous sequence →",
    sequence_output
)

print(
    "Window feasibility  →",
    feasibility_output
)