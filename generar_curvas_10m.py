# -*- coding: utf-8 -*-
"""Curvas de nivel cada 10 m (HMA 8 m) en el corredor del cauce."""
from __future__ import annotations

import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pyproj
import rasterio
from shapely.geometry import LineString, MultiLineString, mapping

_PROJ_DIR = pyproj.datadir.get_data_dir()
os.environ["PROJ_LIB"] = _PROJ_DIR
os.environ["PROJ_DATA"] = _PROJ_DIR
pyproj.datadir.set_data_dir(_PROJ_DIR)

OUT = os.path.dirname(os.path.abspath(__file__))
HMA = os.path.join(OUT, "HMA_DEM8m_MOS_20170716_tile-675.tif")
JSON_IN = os.path.join(OUT, "resultado_manning.json")
HMA_AEA = (
    "+proj=aea +lat_1=25 +lat_2=47 +lat_0=36 +lon_0=85 "
    "+x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"
)
WGS84 = "+proj=longlat +datum=WGS84 +no_defs"


def main():
    with open(JSON_IN, encoding="utf-8") as f:
        data = json.load(f)
    km_rasuwa = float(data.get("km_rasuwagadhi") or 0)
    curva = [p for p in data["curva_1km"] if p["km"] >= km_rasuwa - 0.3]
    if len(curva) < 8:
        curva = [p for p in data["curva_1km"] if p.get("z_m", 0) < 2200]
    tf_fwd = pyproj.Transformer.from_crs(WGS84, HMA_AEA, always_xy=True)
    tf_inv = pyproj.Transformer.from_crs(HMA_AEA, WGS84, always_xy=True)
    rx, ry = [], []
    for p in curva:
        x, y = tf_fwd.transform(p["lon"], p["lat"])
        rx.append(x)
        ry.append(y)
    river = np.column_stack([rx, ry])
    from scipy.spatial import cKDTree

    tree = cKDTree(river)

    with rasterio.open(HMA) as src:
        aff = src.transform
        nodata = src.nodata if src.nodata is not None else -9999.0
        pad = 1800.0
        xmin, xmax = river[:, 0].min() - pad, river[:, 0].max() + pad
        ymin, ymax = river[:, 1].min() - pad, river[:, 1].max() + pad
        col0, row0 = ~aff * (xmin, ymax)
        col1, row1 = ~aff * (xmax, ymin)
        r0 = int(max(0, min(row0, row1)))
        r1 = int(min(src.height, max(row0, row1) + 1))
        c0 = int(max(0, min(col0, col1)))
        c1 = int(min(src.width, max(col0, col1) + 1))
        win = rasterio.windows.Window.from_slices((r0, r1), (c0, c1))
        z = src.read(1, window=win).astype(float)
        win_aff = src.window_transform(win)

    step = 2  # ~16 m, suficiente para curvas de 10 m
    z = z[::step, ::step]
    z[(z <= -9000) | (z == nodata)] = np.nan
    rows, cols = z.shape
    rr, cc = np.meshgrid(np.arange(rows) * step, np.arange(cols) * step, indexing="ij")
    xs = win_aff.c + (cc + 0.5) * win_aff.a + (rr + 0.5) * win_aff.b
    ys = win_aff.f + (cc + 0.5) * win_aff.d + (rr + 0.5) * win_aff.e
    dist, _ = tree.query(np.column_stack([xs.ravel(), ys.ravel()]), k=1)
    dist = dist.reshape(rows, cols)
    z = np.where(dist <= 1200.0, z, np.nan)

    zmin = np.nanmin(z)
    zmax = min(float(np.nanmax(z)), 2200.0)
    high = np.arange(max(400, int(np.floor(zmin / 10.0) * 10)), int(np.ceil(zmax / 10.0) * 10) + 10, 10)
    low = np.arange(int(np.floor(zmin / 20.0) * 20), 400, 20) if zmin < 400 else []
    levels = np.unique(np.concatenate([np.array(low, dtype=float), np.array(high, dtype=float)]))
    levels = levels[(levels >= zmin - 5) & (levels <= zmax + 5)]
    print("z", zmin, zmax, "n_levels", len(levels))

    fig, ax = plt.subplots()
    cs = ax.contour(xs, ys, z, levels=levels)
    plt.close(fig)

    by_elev: dict[int, list] = {}
    n_seg = 0
    for lev, segs in zip(cs.levels, cs.allsegs):
        elev = int(round(float(lev)))
        for seg in segs:
            if len(seg) < 4:
                continue
            lon, lat = tf_inv.transform(seg[:, 0], seg[:, 1])
            line = LineString(np.column_stack([lon, lat]))
            if line.length < 1e-5:
                continue
            line = line.simplify(0.00015, preserve_topology=True)  # ~16 m
            if line.is_empty or line.length < 1e-5:
                continue
            n_seg += 1
            by_elev.setdefault(elev, []).append(line)

    feats = []
    for elev in sorted(by_elev):
        geom = MultiLineString(by_elev[elev])
        gj_geom = mapping(geom)
        # 5 decimals ~ 1.1 m; keeps the HTML overlay smaller
        def _round_coords(obj):
            if isinstance(obj, (list, tuple)) and obj and isinstance(obj[0], (int, float)):
                return [round(float(obj[0]), 5), round(float(obj[1]), 5)]
            if isinstance(obj, list):
                return [_round_coords(x) for x in obj]
            return obj

        gj_geom["coordinates"] = _round_coords(gj_geom["coordinates"])
        feats.append(
            {
                "type": "Feature",
                "properties": {
                    "clase": "curva_10m",
                    "elev_m": elev,
                    "indice": elev % 50 == 0,
                },
                "geometry": gj_geom,
            }
        )
    gj = {"type": "FeatureCollection", "features": feats}
    path = os.path.join(OUT, "curvas_10m_hma.geojson")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(gj, f, separators=(",", ":"))
    print("segmentos", n_seg, "cotas", len(feats), "bytes", os.path.getsize(path))


if __name__ == "__main__":
    main()
