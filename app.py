import streamlit as st
from streamlit_folium import st_folium

from src.data_loader import (
    load_top14,
    load_history,
)

from src.routing import (
    get_route_geometry,
)

from src.map_builder import (
    build_route_map,
)

from src.historical_analysis import (
    get_latest_status,
    hourly_profile,
    get_best_worst_hour,
)


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Historical Traffic Explorer",
    page_icon="🚦",
    layout="wide"
)


# ============================================================
# LOAD DATA
# ============================================================

@st.cache_data
def get_corridors():
    return load_top14()


corridors = get_corridors()
history = load_history()


# ============================================================
# TITLE
# ============================================================

st.title("🚦 Historical Traffic Explorer")

st.write(
    "Lihat rute perjalanan, kondisi lalu lintas pada lokasi yang dipantau, "
    "dan pola kecepatan berdasarkan data historis TomTom."
)


# ============================================================
# ROUTE SELECTION
# ============================================================

st.subheader("Pilih Perjalanan")

col1, col2 = st.columns(2)

with col1:
    origin_label = st.selectbox(
        "Lokasi awal",
        corridors["display_name"].tolist(),
        index=4
    )

with col2:
    destination_label = st.selectbox(
        "Tujuan",
        corridors["display_name"].tolist(),
        index=0
    )


origin = corridors[
    corridors["display_name"] == origin_label
].iloc[0]

destination = corridors[
    corridors["display_name"] == destination_label
].iloc[0]


st.caption(
    "🚗 Mode perjalanan: Mobil"
)


# ============================================================
# GET ROUTE
# ============================================================

route_points = None
distance_km = None
travel_time_min = None


if origin_label != destination_label:

    try:
        route = get_route_geometry(
            float(origin["lat"]),
            float(origin["lon"]),
            float(destination["lat"]),
            float(destination["lon"])
        )

        route_points = route["points"]
        distance_km = route["distance_km"]
        travel_time_min = route["travel_time_min"]

    except Exception as exc:
        st.error(
            f"Rute belum bisa ditampilkan: {exc}"
        )


# ============================================================
# ROUTE SUMMARY
# ============================================================

if distance_km is not None:

    st.subheader("Ringkasan Perjalanan")

    route_col1, route_col2 = st.columns(2)

    with route_col1:
        st.metric(
            "Jarak perjalanan",
            f"{distance_km:.1f} km"
        )

    with route_col2:
        st.metric(
            "Perkiraan waktu perjalanan",
            f"{travel_time_min:.0f} menit"
        )

    st.caption(
        "Perkiraan waktu di atas berasal dari rute kendaraan mobil "
        "yang diberikan oleh layanan routing TomTom."
    )


# ============================================================
# MAP
# ============================================================

st.subheader("Peta Perjalanan")

traffic_map = build_route_map(
    corridors,
    origin,
    destination,
    route_points
)

st_folium(
    traffic_map,
    width=None,
    height=650
)


# ============================================================
# TRAFFIC INFORMATION
# ============================================================

st.subheader("Kondisi Lalu Lintas di Lokasi Pemantauan")


if history.empty:

    st.warning(
        "Data lalu lintas belum tersedia."
    )

else:

    latest_status = get_latest_status(
        history
    )

    latest_timestamp = (
        latest_status["obs_time_utc"].max()
    )

    if latest_timestamp is not None:

        latest_timestamp_wib = (
            latest_timestamp
            .tz_convert("Asia/Jakarta")
        )

        st.caption(
            "Data terakhir yang tersedia: "
            f"{latest_timestamp_wib.strftime('%d %B %Y, %H:%M')} WIB"
        )


    origin_latest = latest_status[
        latest_status["station_id"]
        == origin["station_id"]
    ]

    destination_latest = latest_status[
        latest_status["station_id"]
        == destination["station_id"]
    ]


    status_col1, status_col2 = st.columns(2)


    # ========================================================
    # ORIGIN STATUS
    # ========================================================

    with status_col1:

        st.markdown(
            f"### 📍 {origin_label}"
        )

        if not origin_latest.empty:

            row = origin_latest.iloc[0]

            current_speed = float(
                row["current_speed"]
            )

            free_flow_speed = float(
                row["free_flow_speed"]
            )

            congestion_ratio = float(
                row["congestion_ratio"]
            )

            st.metric(
                "Kecepatan saat data diambil",
                f"{current_speed:.0f} km/jam"
            )

            st.metric(
                "Kecepatan saat kondisi lebih lancar",
                f"{free_flow_speed:.0f} km/jam"
            )

            st.write(
                f"Kecepatan saat data diambil sekitar "
                f"**{congestion_ratio * 100:.1f}% lebih rendah** "
                f"dibanding kondisi arus lalu lintas yang lebih bebas."
            )

        else:

            st.info(
                "Belum ada data untuk lokasi ini."
            )


    # ========================================================
    # DESTINATION STATUS
    # ========================================================

    with status_col2:

        st.markdown(
            f"### 📍 {destination_label}"
        )

        if not destination_latest.empty:

            row = destination_latest.iloc[0]

            current_speed = float(
                row["current_speed"]
            )

            free_flow_speed = float(
                row["free_flow_speed"]
            )

            congestion_ratio = float(
                row["congestion_ratio"]
            )

            st.metric(
                "Kecepatan saat data diambil",
                f"{current_speed:.0f} km/jam"
            )

            st.metric(
                "Kecepatan saat kondisi lebih lancar",
                f"{free_flow_speed:.0f} km/jam"
            )

            st.write(
                f"Kecepatan saat data diambil sekitar "
                f"**{congestion_ratio * 100:.1f}% lebih rendah** "
                f"dibanding kondisi arus lalu lintas yang lebih bebas."
            )

        else:

            st.info(
                "Belum ada data untuk lokasi ini."
            )


# ============================================================
# HISTORICAL PATTERN
# ============================================================

st.subheader(
    "Pola Lalu Lintas Berdasarkan Data Historis"
)


if history.empty:

    st.info(
        "Belum ada data historis yang dapat dianalisis."
    )

else:

    profile = hourly_profile(
        history,
        origin["station_id"]
    )

    total_timestamps = (
        history["obs_time_utc"]
        .nunique()
    )


    if total_timestamps < 3:

        st.info(
            "Data historis masih terlalu sedikit untuk "
            "menyimpulkan pola lalu lintas berdasarkan jam."
        )

    else:

        st.write(
            f"Bagian ini menunjukkan pola kecepatan pada **{origin_label}** "
            "berdasarkan data historis yang tersedia."
        )


        # ====================================================
        # CHART
        # ====================================================

        if not profile.empty:

            st.markdown(
                "#### Rata-rata Kecepatan Berdasarkan Jam"
            )

            chart_data = (
                profile[
                    [
                        "hour_wib",
                        "avg_speed"
                    ]
                ]
                .rename(
                    columns={
                        "avg_speed":
                        "Rata-rata kecepatan (km/jam)"
                    }
                )
                .set_index(
                    "hour_wib"
                )
            )

            st.line_chart(
                chart_data
            )

            st.caption(
                "Sumbu waktu menggunakan WIB. "
                "Grafik dihitung dari observasi historis yang tersedia, "
                "bukan berarti data tersedia terus-menerus tanpa jeda."
            )


        # ====================================================
        # BEST & WORST HOUR
        # ====================================================

        result = get_best_worst_hour(
            history,
            origin["station_id"]
        )


        if result:

            best_col, worst_col = st.columns(2)

            with best_col:

                st.metric(
                    "Waktu yang biasanya lebih lancar",
                    f"{result['best_hour']:02d}:00 WIB",
                    f"Rata-rata {result['best_speed']:.1f} km/jam"
                )

            with worst_col:

                st.metric(
                    "Waktu yang biasanya lebih padat",
                    f"{result['worst_hour']:02d}:00 WIB",
                    f"Rata-rata {result['worst_speed']:.1f} km/jam"
                )

            st.caption(
                "Jam di atas merupakan hasil ringkasan dari data historis "
                "pada lokasi yang dipilih. Informasi ini tidak mewakili "
                "seluruh kondisi jalan di sepanjang rute perjalanan."
            )


# ============================================================
# DATA INFORMATION
# ============================================================

st.divider()

st.subheader("Tentang Informasi di Halaman Ini")

st.write(
    "Data lalu lintas berasal dari lokasi pemantauan pada 14 koridor "
    "yang digunakan dalam penelitian. Rute perjalanan ditampilkan "
    "menggunakan mode kendaraan mobil."
)

st.write(
    "Pola historis digunakan untuk melihat kecenderungan kondisi lalu lintas "
    "pada lokasi yang dipilih. Karena pemantauan hanya dilakukan pada titik "
    "atau koridor tertentu, informasi ini tidak menunjukkan kondisi setiap "
    "ruas jalan yang dilewati sepanjang perjalanan."
)