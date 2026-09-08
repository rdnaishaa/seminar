from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

CORRIDOR_PATH = ROOT / "corridors.csv"
TRAIN_PATH = ROOT / "data" / "processed" / "forecasting_train_preprocessed.csv"

corridors = pd.read_csv(CORRIDOR_PATH)
train = pd.read_csv(TRAIN_PATH)

# Corridor yang benar-benar digunakan forecasting
top14 = sorted(train["corridor_file"].unique())

print("\n=== GRAPH COORDINATE AUDIT ===")
print(f"Forecasting corridors : {len(top14)}")
print(f"corridors.csv rows    : {len(corridors)}")

print("\nColumns corridors.csv:")
print(corridors.columns.tolist())

print("\nForecasting corridor IDs:")
for c in top14:
    print("-", c)

# corridor_file biasanya berasal dari nama file,
# sedangkan corridors.csv menggunakan station_id.
# Normalisasi agar bisa dicocokkan.
def normalize_id(x):
    x = str(x)

    if x.endswith(".csv"):
        x = x[:-4]

    return x

corridors["normalized_id"] = corridors["station_id"].apply(normalize_id)

forecast_ids = [normalize_id(x) for x in top14]

selected = corridors[
    corridors["normalized_id"].isin(forecast_ids)
].copy()

print("\n=== MATCHED COORDINATES ===")
print(
    selected[
        ["station_id", "name", "city", "lat", "lon"]
    ].to_string(index=False)
)

print("\n=== CHECK ===")
print(f"Matched       : {len(selected)}/{len(top14)}")
print(f"Missing lat   : {selected['lat'].isna().sum()}")
print(f"Missing lon   : {selected['lon'].isna().sum()}")

missing = sorted(
    set(forecast_ids)
    - set(selected["normalized_id"])
)

if missing:
    print("\nUNMATCHED:")
    for x in missing:
        print("-", x)
else:
    print("\nAll forecasting corridors matched successfully.")

# Range sanity check
print("\nCoordinate range:")
print(
    f"Latitude  : {selected['lat'].min()} "
    f"to {selected['lat'].max()}"
)
print(
    f"Longitude : {selected['lon'].min()} "
    f"to {selected['lon'].max()}"
)