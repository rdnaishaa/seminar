import streamlit as st
from streamlit_folium import st_folium
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

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


WIB = ZoneInfo("Asia/Jakarta")


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Historical Traffic Explorer",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# STYLING
# ============================================================

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
    }
    h1, h2, h3 {
        font-weight: 700;
    }
    div[data-testid="stMetric"] {
        background-color: rgba(151, 166, 195, 0.08);
        border: 1px solid rgba(151, 166, 195, 0.2);
        border-radius: 12px;
        padding: 14px 16px;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 0.85rem;
        opacity: 0.8;
    }
    .badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 999px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    .badge-green {
        background-color: rgba(34, 197, 94, 0.15);
        color: #16a34a;
    }
    .badge-yellow {
        background-color: rgba(234, 179, 8, 0.15);
        color: #ca8a04;
    }
    .badge-red {
        background-color: rgba(239, 68, 68, 0.15);
        color: #dc2626;
    }
    .location-card {
        border: 1px solid rgba(151, 166, 195, 0.2);
        border-radius: 14px;
        padding: 18px 20px;
        height: 100%;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# LOAD DATA
# ============================================================

@st.cache_data
def get_corridors():
    return load_top14()


@st.cache_data(ttl=300)
def get_history():
    return load_history()


corridors = get_corridors()
history = get_history()


# ============================================================
# HELPERS
# ============================================================

def congestion_badge(ratio: float):
    """Return (emoji label, css class) based on congestion ratio."""
    if ratio < 0.20:
        return "🟢 Lancar", "badge-green"
    elif ratio < 0.40:
        return "🟡 Ramai Lancar", "badge-yellow"
    else:
        return "🔴 Padat", "badge-red"


def render_location_status(label, row):
    """Render a status card for a single monitoring location."""
    current_speed = float(row["current_speed"])
    free_flow_speed = float(row["free_flow_speed"])
    congestion_ratio = float(row["congestion_ratio"])

    badge_text, badge_class = congestion_badge(congestion_ratio)

    st.markdown(
        f"""
        <div class="location-card">
            <h4 style="margin-top:0;">📍 {label}</h4>
            <span class="badge {badge_class}">{badge_text}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")

    m_col1, m_col2 = st.columns(2)

    with m_col1:
        st.metric("Kecepatan saat ini", f"{current_speed:.0f} km/jam")

    with m_col2:
        st.metric("Kecepatan kondisi lancar", f"{free_flow_speed:.0f} km/jam")

    progress_value = max(0.0, min(1.0, current_speed / free_flow_speed if free_flow_speed else 0))
    st.progress(progress_value)

    st.caption(
        f"Kecepatan saat ini sekitar **{congestion_ratio * 100:.1f}% lebih rendah** "
        "dibanding kondisi arus lalu lintas yang lebih bebas."
    )


# ============================================================
# HEADER
# ============================================================

st.title("🚦 Historical Traffic Explorer")
st.write(
    "Lihat rute perjalanan, kondisi lalu lintas pada lokasi yang dipantau, "
    "dan pola kecepatan berdasarkan data historis TomTom."
)

st.divider()


# ============================================================
# SIDEBAR — TRIP PLANNER
# ============================================================

with st.sidebar:
    st.header("🧭 Rencana Perjalanan")

    origin_label = st.selectbox(
        "📍 Lokasi awal",
        corridors["display_name"].tolist(),
        index=4,
    )

    destination_label = st.selectbox(
        "🏁 Tujuan",
        corridors["display_name"].tolist(),
        index=0,
    )

    st.divider()

    st.caption("🕒 Waktu keberangkatan")

    now_wib = datetime.now(WIB)

    selected_date = st.date_input(
        "Tanggal",
        value=now_wib.date(),
        min_value=now_wib.date(),
        max_value=now_wib.date() + timedelta(days=7),
    )

    selected_time = st.time_input(
        "Jam",
        value=now_wib.time().replace(microsecond=0),
    )

    st.divider()

    st.caption("🚗 Mode perjalanan: **Mobil**")

    if origin_label == destination_label:
        st.warning("Lokasi awal dan tujuan masih sama. Pilih tujuan yang berbeda.")


# Build depart_at (WIB) from the sidebar date + time pickers
selected_datetime = datetime.combine(
    selected_date,
    selected_time,
)

selected_datetime = selected_datetime.replace(
    tzinfo=WIB
)

depart_at = selected_datetime.isoformat()


origin = corridors[
    corridors["display_name"] == origin_label
].iloc[0]

destination = corridors[
    corridors["display_name"] == destination_label
].iloc[0]


# ============================================================
# GET ROUTE
# ============================================================

route_points = None
distance_km = None
travel_time_min = None
route_error = None

if origin_label != destination_label:

    with st.spinner("Menghitung rute perjalanan..."):
        try:
            try:
                route = get_route_geometry(
                    float(origin["lat"]),
                    float(origin["lon"]),
                    float(destination["lat"]),
                    float(destination["lon"]),
                    depart_at=depart_at,
                )
            except TypeError:
                # Fallback for routing modules that don't support
                # depart_at yet.
                route = get_route_geometry(
                    float(origin["lat"]),
                    float(origin["lon"]),
                    float(destination["lat"]),
                    float(destination["lon"]),
                )

            route_points = route["points"]
            distance_km = route["distance_km"]
            travel_time_min = route["travel_time_min"]

        except Exception as exc:
            route_error = str(exc)


# ============================================================
# TABS
# ============================================================

tab_overview, tab_status, tab_history, tab_about = st.tabs(
    [
        "🗺️ Rute & Peta",
        "📡 Kondisi Real-time",
        "📈 Pola Historis",
        "ℹ️ Tentang",
    ]
)


# ------------------------------------------------------------
# TAB 1 — ROUTE + MAP
# ------------------------------------------------------------

with tab_overview:

    if route_error:
        st.error(f"Rute belum bisa ditampilkan: {route_error}")

    if distance_km is not None:

        st.subheader("Ringkasan Perjalanan")

        route_col1, route_col2, route_col3 = st.columns(3)

        with route_col1:
            st.metric("📏 Jarak perjalanan", f"{distance_km:.1f} km")

        with route_col2:
            st.metric("⏱️ Perkiraan waktu tempuh", f"{travel_time_min:.0f} menit")

        with route_col3:
            st.metric(
                "🕒 Berangkat",
                selected_datetime.strftime("%d %b, %H:%M"),
                help="Waktu keberangkatan yang dipilih di sidebar (WIB).",
            )

        st.caption(
            "Perkiraan waktu di atas berasal dari rute kendaraan mobil "
            "yang diberikan oleh layanan routing TomTom."
        )

        st.write("")

    st.subheader("Peta Perjalanan")

    traffic_map = build_route_map(
        corridors,
        origin,
        destination,
        route_points,
    )

    st_folium(
        traffic_map,
        width=None,
        height=600,
    )


# ------------------------------------------------------------
# TAB 2 — REAL-TIME STATUS
# ------------------------------------------------------------

with tab_status:

    st.subheader("Kondisi Lalu Lintas di Lokasi Pemantauan")

    if history.empty:
        st.warning("Data lalu lintas belum tersedia.")

    else:

        latest_status = get_latest_status(history)
        latest_timestamp = latest_status["obs_time_utc"].max()

        if latest_timestamp is not None:
            latest_timestamp_wib = latest_timestamp.tz_convert(WIB)
            st.caption(
                "🔄 Data terakhir yang tersedia: "
                f"{latest_timestamp_wib.strftime('%d %B %Y, %H:%M')} WIB"
            )

        origin_latest = latest_status[
            latest_status["station_id"] == origin["station_id"]
        ]

        destination_latest = latest_status[
            latest_status["station_id"] == destination["station_id"]
        ]

        st.write("")

        status_col1, status_col2 = st.columns(2)

        with status_col1:
            if not origin_latest.empty:
                render_location_status(origin_label, origin_latest.iloc[0])
            else:
                st.info(f"📍 {origin_label}: belum ada data untuk lokasi ini.")

        with status_col2:
            if not destination_latest.empty:
                render_location_status(destination_label, destination_latest.iloc[0])
            else:
                st.info(f"📍 {destination_label}: belum ada data untuk lokasi ini.")


# ------------------------------------------------------------
# TAB 3 — HISTORICAL PATTERN
# ------------------------------------------------------------

with tab_history:

    st.subheader("Pola Lalu Lintas Berdasarkan Data Historis")

    if history.empty:
        st.info("Belum ada data historis yang dapat dianalisis.")

    else:

        profile = hourly_profile(history, origin["station_id"])
        total_timestamps = history["obs_time_utc"].nunique()

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

            if not profile.empty:

                st.markdown("#### Rata-rata Kecepatan Berdasarkan Jam")

                chart_data = (
                    profile[["hour_wib", "avg_speed"]]
                    .rename(columns={"avg_speed": "Rata-rata kecepatan (km/jam)"})
                    .set_index("hour_wib")
                )

                st.line_chart(chart_data)

                st.caption(
                    "Sumbu waktu menggunakan WIB. "
                    "Grafik dihitung dari observasi historis yang tersedia, "
                    "bukan berarti data tersedia terus-menerus tanpa jeda."
                )

            result = get_best_worst_hour(history, origin["station_id"])

            if result:

                st.write("")

                best_col, worst_col = st.columns(2)

                with best_col:
                    st.metric(
                        "🟢 Waktu yang biasanya lebih lancar",
                        f"{result['best_hour']:02d}:00 WIB",
                        f"Rata-rata {result['best_speed']:.1f} km/jam",
                    )

                with worst_col:
                    st.metric(
                        "🔴 Waktu yang biasanya lebih padat",
                        f"{result['worst_hour']:02d}:00 WIB",
                        f"Rata-rata {result['worst_speed']:.1f} km/jam",
                    )

                st.caption(
                    "Jam di atas merupakan hasil ringkasan dari data historis "
                    "pada lokasi yang dipilih. Informasi ini tidak mewakili "
                    "seluruh kondisi jalan di sepanjang rute perjalanan."
                )


# ------------------------------------------------------------
# TAB 4 — ABOUT
# ------------------------------------------------------------

with tab_about:

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