# -*- coding: utf-8 -*-
"""Mancha de inundacion a lo largo del cauce analizado (HMA 8 m)."""
from __future__ import annotations

import json
import os

import numpy as np
import pyproj
import rasterio
from rasterio.features import shapes
from shapely.geometry import mapping, shape
from shapely.ops import transform as shp_transform, unary_union
from scipy.spatial import cKDTree

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

# Profundidad / runup y semiancho maximo segun km (flujo de detritos en garganta).
# Estaciones: ~7-9 m de subida. Wikipedia: runup hasta ~80 m en laderas.
# Nucleo = agua/lodo en el fondo del valle. Runup = ladera alcanzada por la avalancha.
def hw(km):
    if km < 20:
        return 12.0, 40.0, 280.0, 450.0  # h_nucleo, h_runup, w_nucleo, w_runup
    if km < 40:
        return 10.0, 30.0, 450.0, 700.0
    return 9.0, 22.0, 700.0, 1100.0


def main():
    with open(JSON_IN, encoding="utf-8") as f:
        data = json.load(f)
    curva = data["curva_1km"]
    comm = data["comunidades"]

    tf_fwd = pyproj.Transformer.from_crs(WGS84, HMA_AEA, always_xy=True)
    tf_inv = pyproj.Transformer.from_crs(HMA_AEA, WGS84, always_xy=True)

    rx, ry, rz, rkm = [], [], [], []
    for p in curva:
        x, y = tf_fwd.transform(p["lon"], p["lat"])
        rx.append(x)
        ry.append(y)
        rz.append(p["z_m"])
        rkm.append(p["km"])
    river_xy = np.column_stack([rx, ry])
    river_z = np.array(rz, dtype=float)
    river_km = np.array(rkm, dtype=float)
    tree = cKDTree(river_xy)

    with rasterio.open(HMA) as src:
        aff = src.transform
        nodata = src.nodata if src.nodata is not None else -9999.0
        pad = 1200.0
        xmin, xmax = river_xy[:, 0].min() - pad, river_xy[:, 0].max() + pad
        ymin, ymax = river_xy[:, 1].min() - pad, river_xy[:, 1].max() + pad
        col0, row0 = ~aff * (xmin, ymax)
        col1, row1 = ~aff * (xmax, ymin)
        r0, r1 = int(max(0, min(row0, row1))), int(min(src.height, max(row0, row1) + 1))
        c0, c1 = int(max(0, min(col0, col1))), int(min(src.width, max(col0, col1) + 1))
        win = rasterio.windows.Window.from_slices((r0, r1), (c0, c1))
        z = src.read(1, window=win)
        win_aff = src.window_transform(win)

    step = 3  # ~24 m
    z_s = z[::step, ::step]
    rows, cols = z_s.shape
    rr, cc = np.meshgrid(np.arange(rows) * step, np.arange(cols) * step, indexing="ij")
    xs = win_aff.c + (cc + 0.5) * win_aff.a + (rr + 0.5) * win_aff.b
    ys = win_aff.f + (cc + 0.5) * win_aff.d + (rr + 0.5) * win_aff.e
    pts = np.column_stack([xs.ravel(), ys.ravel()])
    dist, idx = tree.query(pts, k=1)
    dist = dist.reshape(rows, cols)
    idx = idx.reshape(rows, cols)
    z_riv = river_z[idx]
    km = river_km[idx]
    z_pix = z_s.astype(float)
    void = (z_pix <= -9000) | (z_pix == nodata) | ~np.isfinite(z_pix)
    dh = z_pix - z_riv

    h_n = np.where(km < 20, 12.0, np.where(km < 40, 10.0, 9.0))
    h_r = np.where(km < 20, 40.0, np.where(km < 40, 30.0, 22.0))
    w_n = np.where(km < 20, 280.0, np.where(km < 40, 450.0, 700.0))
    w_r = np.where(km < 20, 450.0, np.where(km < 40, 700.0, 1100.0))

    nucleo = (~void) & (dh >= -2) & (dh <= h_n) & (dist <= w_n)
    runup = (~void) & (dh > h_n) & (dh <= h_r) & (dist <= w_r)

    out_aff = rasterio.Affine(
        win_aff.a * step, win_aff.b, win_aff.c,
        win_aff.d, win_aff.e * step, win_aff.f,
    )

    def mask_to_polys(mask, name):
        m = mask.astype(np.uint8)
        geoms = []
        for geom, val in shapes(m, mask=m == 1, transform=out_aff):
            if val != 1:
                continue
            g = shape(geom).buffer(0)
            if g.is_empty or g.area < 400:
                continue
            geoms.append(g)
        if not geoms:
            return None
        u = unary_union(geoms).simplify(25, preserve_topology=True)
        u_wgs = shp_transform(lambda x, y, z=None: tf_inv.transform(x, y), u)
        u_wgs = u_wgs.buffer(0)
        return {
            "type": "Feature",
            "properties": {"clase": name, "area_km2": round(u.area / 1e6, 2)},
            "geometry": mapping(u_wgs),
        }

    f_n = mask_to_polys(nucleo, "nucleo_valle")
    f_r = mask_to_polys(runup, "runup_ladera")
    feats = [f for f in (f_n, f_r) if f]

    line_coords = [[p["lon"], p["lat"]] for p in curva]
    feats.append(
        {
            "type": "Feature",
            "properties": {"clase": "eje", "km": data["longitud_km"]},
            "geometry": {"type": "LineString", "coordinates": line_coords},
        }
    )
    for c in comm:
        feats.append(
            {
                "type": "Feature",
                "properties": {
                    "clase": "comunidad",
                    "nombre": c["nombre"],
                    "km": c["km"],
                    "hora": c["hora_llegada"],
                    "perdidos": c["minutos_perdidos"],
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [c["lon"], c["lat"]],
                },
            }
        )
    end = curva[-1]
    feats.append(
        {
            "type": "Feature",
            "properties": {
                "clase": "limite_analizado",
                "nombre": "Limite del tramo analizado (Devighat HEP)",
                "nota": "El frente continuo aguas abajo hacia Galchhi, Malekhu, Muglin y Devghat (Chitwan ~15:20).",
            },
            "geometry": {"type": "Point", "coordinates": [end["lon"], end["lat"]]},
        }
    )

    gj = {"type": "FeatureCollection", "features": feats}
    path = os.path.join(OUT, "inundacion_bhote_koshi.geojson")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(gj, f)
    a_n = f_n["properties"]["area_km2"] if f_n else 0
    a_r = f_r["properties"]["area_km2"] if f_r else 0
    print("nucleo_km2", a_n, "runup_km2", a_r)
    print("wrote", path)
    return gj, a_n, a_r, data


if __name__ == "__main__":
    main()
