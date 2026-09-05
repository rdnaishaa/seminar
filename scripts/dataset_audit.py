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
# AUDIT ALL CSV FILES
# =========================

results = []

for file in sorted(DATA_DIR.glob("*.csv")):
    df = pd.read_csv(file)

    # Ubah timestamp menjadi format datetime UTC
    df["obs_time_utc"] = pd.to_datetime(
        df["obs_time_utc"],
        utc=True,
        errors="coerce"
    )

    # Buang timestamp yang gagal dibaca
    invalid_timestamp = df["obs_time_utc"].isna().sum()

    # Urutkan berdasarkan waktu
    df = df.sort_values("obs_time_utc")

    # Cek duplicate timestamp
    duplicate_count = df["obs_time_utc"].duplicated().sum()

    # Hitung jarak waktu antar-observasi
    intervals = df["obs_time_utc"].diff().dropna()

    # Berapa interval yang tepat 1 jam
    hourly_intervals = (
        intervals == pd.Timedelta(hours=1)
    ).sum()

    # Gap terbesar antar-observasi
    if len(intervals) > 0:
        largest_gap_hours = (
            intervals.max().total_seconds() / 3600
        )
    else:
        largest_gap_hours = None

    # Total missing value di semua kolom
    missing_values = df.isna().sum().sum()

    # Persentase interval yang 1 jam
    if len(intervals) > 0:
        hourly_percentage = round(
            hourly_intervals / len(intervals) * 100,
            2
        )
    else:
        hourly_percentage = None

    results.append({
        "file": file.name,
        "corridor": (
            df["name"].iloc[0]
            if len(df) > 0 and "name" in df.columns
            else file.stem
        ),
        "rows": len(df),
        "start_utc": df["obs_time_utc"].min(),
        "end_utc": df["obs_time_utc"].max(),
        "duplicates": duplicate_count,
        "invalid_timestamp": invalid_timestamp,
        "1h_intervals": hourly_intervals,
        "1h_interval_percentage": hourly_percentage,
        "largest_gap_hours": largest_gap_hours,
        "missing_values": missing_values
    })

# =========================
# CREATE AUDIT TABLE
# =========================

audit = pd.DataFrame(results)

# =========================
# PRINT DATASET SUMMARY
# =========================

print("\n=== DATASET AUDIT ===")

print("Jumlah corridor :", len(audit))
print("Total observasi :", audit["rows"].sum())
print("Minimum rows    :", audit["rows"].min())
print("Maximum rows    :", audit["rows"].max())
print("Rata-rata rows  :", round(audit["rows"].mean(), 2))
print("Tanggal awal    :", audit["start_utc"].min())
print("Tanggal akhir   :", audit["end_utc"].max())
print("Total duplicate :", audit["duplicates"].sum())
print("Invalid time    :", audit["invalid_timestamp"].sum())
print("Missing values  :", audit["missing_values"].sum())

if audit["largest_gap_hours"].notna().any():
    print(
        "Largest gap     :",
        audit["largest_gap_hours"].max(),
        "jam"
    )

# =========================
# CORRIDOR WITH LEAST DATA
# =========================

print("\n=== 10 CORRIDOR DENGAN DATA PALING SEDIKIT ===")

print(
    audit.sort_values("rows")[
        [
            "corridor",
            "rows",
            "start_utc",
            "end_utc",
            "1h_interval_percentage",
            "largest_gap_hours"
        ]
    ]
    .head(10)
    .to_string(index=False)
)

# =========================
# CORRIDOR WITH LARGEST GAPS
# =========================

print("\n=== 10 CORRIDOR DENGAN GAP TERBESAR ===")

print(
    audit.sort_values(
        "largest_gap_hours",
        ascending=False
    )[
        [
            "corridor",
            "rows",
            "largest_gap_hours",
            "1h_interval_percentage"
        ]
    ]
    .head(10)
    .to_string(index=False)
)

# =========================
# SAVE AUDIT RESULT
# =========================

output_file = OUTPUT_DIR / "dataset_audit.csv"

audit.to_csv(
    output_file,
    index=False
)

print(f"\nAudit tersimpan → {output_file}")