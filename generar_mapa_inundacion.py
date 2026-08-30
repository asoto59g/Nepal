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
COP30 = os.path.join(OUT, "Copernicus_DSM_COG_10_N27_00_E084_00_DEM.tif")
JSON_IN = os.path.join(OUT, "resultado_manning.json")

HMA_AEA = (
    "+proj=aea +lat_1=25 +lat_2=47 +lat_0=36 +lon_0=85 "
    "+x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"
)
WGS84 = "+proj=longlat +datum=WGS84 +no_defs"

# Profundidad / runup y semiancho maximo segun km desde Rasuwagadhi
# (ocupación HAND del valle, no tirante de pico 80–96 m en garganta).
def hw_arrays(km_corredor):
    kc = km_corredor
    h_n = np.where(kc < 20, 12.0, np.where(kc < 40, 10.0, np.where(kc < 60, 9.0, np.where(kc < 100, 7.0, 5.0))))
    h_r = np.where(kc < 20, 40.0, np.where(kc < 40, 30.0, np.where(kc < 60, 22.0, np.where(kc < 100, 16.0, 10.0))))
    w_n = np.where(kc < 20, 280.0, np.where(kc < 40, 450.0, np.where(kc < 60, 700.0, np.where(kc < 100, 900.0, 1500.0))))
    w_r = np.where(kc < 20, 450.0, np.where(kc < 40, 700.0, np.where(kc < 60, 1100.0, np.where(kc < 100, 1500.0, 2800.0))))
    return h_n, h_r, w_n, w_r


def main():
    with open(JSON_IN, encoding="utf-8") as f:
        data = json.load(f)
    curva = data["curva_1km"]
    comm = data["comunidades"]
    km_rasuwa = float(data.get("km_rasuwagadhi") or next(c["km"] for c in comm if c["id"] == "rasuwagadhi"))
    # HAND solo Rasuwagadhi→Bharatpur: no pintar 12–40 m sobre el glaciar Lhende.
    curva_hand = [p for p in curva if p["km"] >= km_rasuwa - 0.2]
    if len(curva_hand) < 8:
        curva_hand = curva

    tf_fwd = pyproj.Transformer.from_crs(WGS84, HMA_AEA, always_xy=True)
    tf_inv = pyproj.Transformer.from_crs(HMA_AEA, WGS84, always_xy=True)

    rx, ry, rz, rkm = [], [], [], []
    for p in curva_hand:
        x, y = tf_fwd.transform(p["lon"], p["lat"])
        rx.append(x)
        ry.append(y)
        rz.append(p["z_m"])
        rkm.append(p["km"] - km_rasuwa)
    river_xy = np.column_stack([rx, ry])
    river_z = np.array(rz, dtype=float)
    river_km = np.array(rkm, dtype=float)
    tree = cKDTree(river_xy)

    with rasterio.open(HMA) as src:
        aff = src.transform
        nodata = src.nodata if src.nodata is not None else -9999.0
        pad = 3000.0
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

    h_n, h_r, w_n, w_r = hw_arrays(km)

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

    # COP30: el tile HMA corta ~84.45°E; Bharatpur / Devghat quedan al borde oeste.
    if os.path.exists(COP30):
        offset = float(data.get("cop30_offset_m") or 0.0)
        west = [p for p in curva if p["lon"] < 84.55]
        if west:
            print("HAND COP30, puntos eje oeste", len(west), "offset", offset)
            with rasterio.open(COP30) as src:
                pad_deg = 0.03
                w = min(p["lon"] for p in west) - pad_deg
                e = max(p["lon"] for p in west) + pad_deg
                s = min(p["lat"] for p in west) - pad_deg
                n = max(p["lat"] for p in west) + pad_deg
                col0, row0 = ~src.transform * (w, n)
                col1, row1 = ~src.transform * (e, s)
                r0 = int(max(0, min(row0, row1)))
                r1 = int(min(src.height, max(row0, row1) + 1))
                c0 = int(max(0, min(col0, col1)))
                c1 = int(min(src.width, max(col0, col1) + 1))
                win = rasterio.windows.Window.from_slices((r0, r1), (c0, c1))
                zc = src.read(1, window=win).astype(float)
                win_aff = src.window_transform(win)
                nodata_c = src.nodata if src.nodata is not None else -32767
            step_c = 2
            zc = zc[::step_c, ::step_c]
            rows_c, cols_c = zc.shape
            rr, cc = np.meshgrid(
                np.arange(rows_c) * step_c, np.arange(cols_c) * step_c, indexing="ij"
            )
            lons_p = win_aff.c + (cc + 0.5) * win_aff.a + (rr + 0.5) * win_aff.b
            lats_p = win_aff.f + (cc + 0.5) * win_aff.d + (rr + 0.5) * win_aff.e
            xs_c, ys_c = tf_fwd.transform(lons_p.ravel(), lats_p.ravel())
            pts_c = np.column_stack([xs_c, ys_c])
            dist_c, idx_c = tree.query(pts_c, k=1)
            dist_c = dist_c.reshape(rows_c, cols_c)
            idx_c = idx_c.reshape(rows_c, cols_c)
            z_riv_c = river_z[idx_c]
            km_c = river_km[idx_c]
            z_pix_c = zc + offset
            void_c = (zc <= -1000) | (zc == nodata_c) | ~np.isfinite(zc)
            dh_c = z_pix_c - z_riv_c
            hn, hr, wn, wr = hw_arrays(km_c)
            nucleo_c = (~void_c) & (dh_c >= -2) & (dh_c <= hn) & (dist_c <= wn)
            runup_c = (~void_c) & (dh_c > hn) & (dh_c <= hr) & (dist_c <= wr)
            out_aff_c = rasterio.Affine(
                win_aff.a * step_c, win_aff.b, win_aff.c,
                win_aff.d, win_aff.e * step_c, win_aff.f,
            )

            def mask_to_polys_wgs(mask, name):
                m = mask.astype(np.uint8)
                geoms = []
                for geom, val in shapes(m, mask=m == 1, transform=out_aff_c):
                    if val != 1:
                        continue
                    g = shape(geom).buffer(0)
                    if g.is_empty:
                        continue
                    geoms.append(g)
                if not geoms:
                    return None
                u = unary_union(geoms).simplify(0.0002, preserve_topology=True)
                # área aproximada en m² (1 deg ~ 111 km)
                area_km2 = u.area * (111000 ** 2) / 1e6
                return {
                    "type": "Feature",
                    "properties": {"clase": name, "area_km2": round(area_km2, 2)},
                    "geometry": mapping(u),
                }

            extra_n = mask_to_polys_wgs(nucleo_c, "nucleo_valle")
            extra_r = mask_to_polys_wgs(runup_c, "runup_ladera")

            def merge_feat(a, b, name):
                geoms = []
                for f in (a, b):
                    if f and f.get("geometry"):
                        g = shape(f["geometry"]).buffer(0)
                        if not g.is_empty:
                            geoms.append(g)
                if not geoms:
                    return None
                u = unary_union(geoms)
                # área: si hay HMA (m projected) + WGS, usar geodesic-ish from WGS
                u_wgs = u
                area_km2 = u_wgs.area * (111000 ** 2) / 1e6
                if a and a["properties"].get("area_km2") and not b:
                    area_km2 = a["properties"]["area_km2"]
                elif a and b:
                    area_km2 = (a["properties"].get("area_km2") or 0) + (
                        b["properties"].get("area_km2") or 0
                    )
                return {
                    "type": "Feature",
                    "properties": {"clase": name, "area_km2": round(area_km2, 2)},
                    "geometry": mapping(u_wgs.buffer(0)),
                }

            f_n = merge_feat(f_n, extra_n, "nucleo_valle") or f_n
            f_r = merge_feat(f_r, extra_r, "runup_ladera") or f_r

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
                    "h_pico_m": c.get("h_pico_m"),
                    "h_hand_m": c.get("h_hand_m"),
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
                "nombre": "Limite del tramo analizado (Bharatpur / Narayani)",
                "nota": (
                    "km 0 = cicatriz Langtang (S2). Rasuwagadhi ~km "
                    f"{km_rasuwa:.0f}, frente 08:54. HAND (ocupación de valle) "
                    "solo Rasuwagadhi→Bharatpur; no es el tirante de pico 80–96 m. "
                    "DHM situó el frente en Devghat (Chitwan) ~15:20. "
                    "EMSR927 AOI04 Bharatpur seguía en espera al generar el mapa."
                ),
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
