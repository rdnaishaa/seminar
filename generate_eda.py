#!/usr/bin/env python3
"""Regenerate EDA.md + figures/ from sample_data/tomtom_sample.csv.

Self-contained: only needs pandas, numpy, matplotlib, pillow.
The road maps use free CARTO Voyager basemap tiles (© OpenStreetMap
contributors © CARTO — keep the attribution if you reuse the figures).
Tiles are cached under figures/tiles/ so re-runs work offline.
"""

from __future__ import annotations

import io
import math
import urllib.request
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.cm as cm
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image

HERE = Path(__file__).resolve().parent
FIGS = HERE / "figures"
TILE_URL = "https://basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png"
R = 6378137.0  # web-mercator radius

RUSH_HOURS = [7, 8, 9, 17, 18, 19]  # WIB (UTC+7)


# ------------------------------------------------------------- tiny basemap
def ll2merc(lon, lat):
    lon, lat = np.asarray(lon, float), np.asarray(lat, float)
    return R * np.radians(lon), R * np.log(np.tan(np.pi / 4 + np.radians(lat) / 2))


def draw_basemap(ax, w, s, e, n, zoom=11, alpha=1.0):
    def tile_xy(lon, lat, z):
        t = 2 ** z
        lr = math.radians(lat)
        return ((lon + 180) / 360 * t,
                (1 - math.log(math.tan(lr) + 1 / math.cos(lr)) / math.pi) / 2 * t)

    x0, y1 = tile_xy(w, s, zoom)
    x1, y0 = tile_xy(e, n, zoom)
    xs = range(int(x0), int(x1) + 1)
    ys = range(int(y0), int(y1) + 1)
    cache = FIGS / "tiles"
    cache.mkdir(parents=True, exist_ok=True)
    mosaic = Image.new("RGB", (256 * len(xs), 256 * len(ys)), "white")
    for i, tx in enumerate(xs):
        for j, ty in enumerate(ys):
            p = cache / f"{zoom}_{tx}_{ty}.png"
            try:
                if not p.exists():
                    req = urllib.request.Request(
                        TILE_URL.format(z=zoom, x=tx, y=ty),
                        headers={"User-Agent": "tomtom-extract-eda/1.0"})
                    p.write_bytes(urllib.request.urlopen(req, timeout=20).read())
                mosaic.paste(Image.open(io.BytesIO(p.read_bytes())).convert("RGB"),
                             (256 * i, 256 * j))
            except Exception:
                pass  # missing tile -> white patch, keep going

    def merc_of_tile(tx, ty, z):
        t = 2 ** z
        lon = tx / t * 360 - 180
        lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * ty / t))))
        return ll2merc(lon, lat)

    x_min, y_max = merc_of_tile(min(xs), min(ys), zoom)
    x_max, y_min = merc_of_tile(max(xs) + 1, max(ys) + 1, zoom)
    ax.imshow(mosaic, extent=(x_min, x_max, y_min, y_max), alpha=alpha, zorder=1)
    bx, by = ll2merc([w, e], [s, n])
    ax.set_xlim(*bx)
    ax.set_ylim(*by)
    ax.set_xticks([]), ax.set_yticks([])


# ------------------------------------------------------------------- data
def load() -> pd.DataFrame:
    df = pd.read_csv(HERE / "sample_data/tomtom_sample.csv",
                     parse_dates=["obs_time_utc"])
    meta = pd.read_csv(HERE / "corridors.csv").set_index("station_id")
    df["name"] = df.station_id.map(meta["name"])
    df["city"] = df.station_id.map(meta["city"])
    df["hour_local"] = (df.obs_time_utc.dt.hour + 7) % 24  # WIB
    df["weekday"] = df.obs_time_utc.dt.dayofweek  # 0=Mon
    df["is_rush"] = df.hour_local.isin(RUSH_HOURS) & (df.weekday <= 4)
    return df


def md_table(frame: pd.DataFrame, floats="{:.2f}") -> str:
    f = frame.copy()
    for c in f.select_dtypes("float"):
        f[c] = f[c].map(floats.format)
    lines = ["| " + " | ".join(map(str, f.columns)) + " |",
             "|" + "---|" * len(f.columns)]
    lines += ["| " + " | ".join(map(str, r)) + " |" for r in f.to_numpy()]
    return "\n".join(lines)


# ----------------------------------------------------------------- figures
def fig_diurnal(df) -> None:
    jkt = df
    fig, ax = plt.subplots(figsize=(7, 3.2), dpi=150)
    piv = jkt.pivot_table(index="hour_local", columns="weekday",
                          values="congestion_ratio")
    wd = piv[[c for c in piv.columns if c <= 4]].mean(axis=1)
    we = piv[[c for c in piv.columns if c >= 5]].mean(axis=1)
    ax.plot(wd.index, wd, "o-", ms=3, label="weekday")
    ax.plot(we.index, we, "s--", ms=3, label="weekend")
    ax.set_xlabel("hour of day (local)")
    ax.set_ylabel("mean congestion ratio")
    ax.set_title(f"Diurnal congestion, {jkt.station_id.nunique()} Jabodetabek corridors (WIB)")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGS / "diurnal_congestion.png")
    plt.close(fig)


def fig_ranking(df, top=25) -> pd.DataFrame:
    rush = df[df.is_rush]
    rank = (rush.groupby("name")
            .agg(rush_congestion=("congestion_ratio", "mean"),
                 mean_speed=("current_speed", "mean"),
                 free_flow=("free_flow_speed", "mean"))
            .sort_values("rush_congestion", ascending=False)
            .reset_index())
    head = rank.head(top).set_index("name")
    fig, ax = plt.subplots(figsize=(6.8, 5.6), dpi=150)
    colors = cm.RdYlGn_r(head.rush_congestion / head.rush_congestion.max())
    ax.barh(head.index[::-1], head.rush_congestion[::-1],
            color=colors[::-1], ec="0.3", lw=0.4)
    ax.set_xlabel("mean weekday rush-hour congestion ratio (0 = free flow)")
    ax.set_title(f"Top {top} congested corridors of {df.station_id.nunique()} "
                 "(weekday rush hours, local time)")
    ax.tick_params(axis="y", labelsize=6.5)
    fig.tight_layout()
    fig.savefig(FIGS / "corridor_ranking.png")
    plt.close(fig)
    return rank


def fig_heatmap(df, top=40) -> None:
    jkt = df
    piv = jkt.pivot_table(index="name", columns="hour_local",
                          values="congestion_ratio")
    piv = piv.loc[piv.mean(axis=1).sort_values(ascending=False).index[:top]]
    fig, ax = plt.subplots(figsize=(7.5, 6.4), dpi=150)
    im = ax.imshow(piv, aspect="auto", cmap="RdYlGn_r")
    ax.set_xticks(range(0, 24, 2), piv.columns[::2])
    ax.set_yticks(range(len(piv)), piv.index, fontsize=5.5)
    ax.set_xlabel("hour of day (WIB)")
    fig.colorbar(im, label="mean congestion ratio")
    ax.set_title(f"Congestion by corridor and hour — top {top} Jabodetabek corridors")
    fig.tight_layout()
    fig.savefig(FIGS / "congestion_heatmap.png")
    plt.close(fig)


def _draw_corridors(ax, geo, cong, vmax, label_top=0):
    cmap = plt.get_cmap("RdYlGn_r")
    labeled = set(cong.sort_values(ascending=False).head(label_top).index)
    for sid, g in geo.groupby("station_id"):
        g = g.sort_values("seq")
        x, y = ll2merc(g.lon.to_numpy(), g.lat.to_numpy())
        c = cong.get(sid, np.nan)
        ax.plot(x, y, lw=2.6, solid_capstyle="round", zorder=5,
                color="0.55" if np.isnan(c) else cmap(min(c / vmax, 1.0)))
        if sid in labeled and "name" in g:
            ax.annotate(g.name.iloc[0], (x[len(x) // 2], y[len(y) // 2]),
                        fontsize=6, xytext=(4, 4), textcoords="offset points",
                        zorder=7,
                        bbox=dict(fc="white", alpha=0.7, ec="none", pad=0.6))


def fig_map(df) -> None:
    """Jabodetabek network map (full 96-corridor network incl. outer ring)."""
    geo = pd.read_csv(HERE / "sample_data/corridor_geometry.csv")
    meta = pd.read_csv(HERE / "corridors.csv").set_index("station_id")
    geo["city"] = geo.station_id.map(meta["city"])
    cong = df[df.is_rush].groupby("station_id")["congestion_ratio"].mean()
    vmax = float(cong.max())

    jgeo = geo[geo.city == "Jabodetabek"]
    fig, ax = plt.subplots(figsize=(8.5, 7.5), dpi=150)
    draw_basemap(ax, 106.48, -6.70, 107.20, -6.04, zoom=10)
    _draw_corridors(ax, jgeo, cong, vmax, label_top=12)
    sm = cm.ScalarMappable(cmap=plt.get_cmap("RdYlGn_r"),
                           norm=plt.Normalize(0, vmax))
    fig.colorbar(sm, ax=ax, shrink=0.7,
                 label="mean weekday rush-hour congestion ratio")
    n = jgeo.station_id.nunique()
    ax.set_title(f"TomTom network over Jabodetabek — {n} corridors, weekday "
                 "rush-hour congestion\n(basemap © OpenStreetMap contributors © CARTO)",
                 fontsize=10)
    fig.tight_layout()
    fig.savefig(FIGS / "road_map.png")
    plt.close(fig)


# ---------------------------------------------------------------- markdown
def write_md(df, rank) -> None:
    n_days = df.obs_time_utc.dt.date.nunique()
    overview = (df.groupby("name")
                .agg(rows=("current_speed", "size"),
                     mean_speed=("current_speed", "mean"),
                     free_flow=("free_flow_speed", "mean"),
                     mean_congestion=("congestion_ratio", "mean"),
                     max_congestion=("congestion_ratio", "max"))
                .sort_values("mean_congestion", ascending=False)
                .reset_index())
    md = f"""# TomTom Traffic Data — Exploratory Data Analysis (Jabodetabek)

*Auto-generated by `generate_eda.py` from `sample_data/tomtom_sample.csv`
({len(df):,} hourly observations, {df.station_id.nunique()} Jabodetabek
corridors, {df.obs_time_utc.min():%Y-%m-%d} → {df.obs_time_utc.max():%Y-%m-%d},
{n_days} days). Hours shown in WIB (UTC+7).*

## 1. What one observation looks like

Each hourly poll of one corridor yields one row (see
`sample_data/sample_flow_response.json` for the raw API response):

{md_table(df.sort_values('obs_time_utc').tail(3)[
    ['station_id', 'obs_time_utc', 'current_speed', 'free_flow_speed',
     'congestion_ratio', 'confidence']])}

`congestion_ratio = 1 − current_speed / free_flow_speed` — 0 means free flow,
0.5 means traffic at half the free-flow speed.

## 2. Corridor overview (top 15 by mean congestion)

{md_table(overview.head(15))}

## 3. Diurnal pattern

Jakarta's twin rush hours are clearly visible, and weekends flatten the
morning peak far more than the evening one:

![diurnal congestion](figures/diurnal_congestion.png)

## 4. Corridor ranking (weekday rush hours)

![corridor ranking](figures/corridor_ranking.png)

Top 10 of {df.station_id.nunique()}:

{md_table(rank.head(10))}

## 5. Corridor × hour heatmap

![heatmap](figures/congestion_heatmap.png)

## 6. Road network on the map

Corridor polylines (returned by the API itself) drawn over a real basemap,
colored by weekday rush-hour congestion:

![road map](figures/road_map.png)

## Notes & caveats

- TomTom flow data is **real-time only** — no historical API exists on the
  free tier, so a time-series must be built by polling on a schedule.
- `confidence` < 1 means fewer probe vehicles; treat low-confidence rows with
  care.
- Corridors were added in stages (14 → 64), so early dates cover fewer
  corridors; per-corridor row counts differ. Full per-corridor history:
  `full_data/<station_id>.csv`.
- This sample covers ~3 weeks; seasonal effects (rainy season, Ramadan,
  school holidays) need longer collection.
- Basemap tiles: © OpenStreetMap contributors © CARTO. Traffic data:
  © TomTom — check the [TomTom developer terms](https://developer.tomtom.com/terms-and-conditions)
  before redistributing collected data.
"""
    (HERE / "EDA.md").write_text(md)
    print("EDA.md written")


if __name__ == "__main__":
    FIGS.mkdir(exist_ok=True)
    frame = load()
    fig_diurnal(frame)
    ranking = fig_ranking(frame)
    fig_heatmap(frame)
    fig_map(frame)
    write_md(frame, ranking)
    print("done — figures/ + EDA.md regenerated")
