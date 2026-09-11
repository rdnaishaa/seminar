import os
from pathlib import Path

import requests
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]

load_dotenv(ROOT / ".env")

API_KEY = os.getenv("TOMTOM_API_KEY")

if not API_KEY:
    raise RuntimeError("TOMTOM_API_KEY tidak ditemukan")


# Contoh: Depok → Bekasi
START_LAT = -6.4
START_LON = 106.82

END_LAT = -6.24
END_LON = 106.975


url = (
    "https://api.tomtom.com/routing/1/"
    f"calculateRoute/"
    f"{START_LAT},{START_LON}:"
    f"{END_LAT},{END_LON}/json"
)


response = requests.get(
    url,
    params={
        "key": API_KEY,
        "traffic": "false",
        "routeType": "fastest",
        "travelMode": "car",
    },
    timeout=30,
)

response.raise_for_status()

data = response.json()


route = data["routes"][0]

summary = route["summary"]

points = []

for leg in route["legs"]:
    for point in leg["points"]:
        points.append(
            (
                point["latitude"],
                point["longitude"],
            )
        )


print("ROUTE BERHASIL")
print("-----------------------------")
print(f"Jumlah titik : {len(points)}")
print(
    f"Jarak        : "
    f"{summary['lengthInMeters'] / 1000:.2f} km"
)
print(
    f"Travel time  : "
    f"{summary['travelTimeInSeconds'] / 60:.1f} menit"
)

print()
print("5 titik pertama:")

for point in points[:5]:
    print(point)