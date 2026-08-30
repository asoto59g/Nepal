# -*- coding: utf-8 -*-
"""S2 SCL en la cabecera USGS + cambio S1 16 vs 28 ago (cicatriz Lhende)."""
from __future__ import annotations

import json
import math
import os
from pathlib import Path

os.environ["GDAL_HTTP_UNSAFESSL"] = "YES"
os.environ["CPL_VSIL_CURL_ALLOWED_EXTENSIONS"] = ".tif,.tiff,.TIF,.jp2"
os.environ["GDAL_HTTP_TIMEOUT"] = "90"
os.environ["CPL_VSIL_CURL_USE_HEAD"] = "NO"

import numpy as np
import pyproj
import rasterio
import requests
from rasterio.control import GroundControlPoint
from rasterio.enums import Resampling
from rasterio.features import shapes
from rasterio.transform import from_gcps
from rasterio.warp import calculate_default_transform, reproject
from rasterio.windows import Window, from_bounds
from shapely.geometry import mapping, shape
from shapely.ops import unary_union

OUT = Path(__file__).resolve().parent
HEADERS = {"User-Agent": "ABC-Geomatica-Nepal/1.0"}
# USGS landslide-type M5.2, 26 ago 08:37 NPT
USGS = (85.515, 28.271)  # lon, lat
RASUWA = (85.378, 28.278)
SRC_BBOX = (85.46, 28.22, 85.58, 28.34)  # W S E N
S2_IDS = [
    "S2B_45RUM_20260824_0_L2A",
    "S2B_45RUM_20260827_0_L2A",
    "S2C_45RUM_20260829_0_L2A",
]
ID_BEFORE = "S1D_IW_GRDH_1SDV_20260816T122141_20260816T122206_004151_007980"
ID_AFTER = "S1D_IW_GRDH_1SDV_20260828T122141_20260828T122206_004326_007FA4"
COLL = "sentinel-1-grd"
WGS84 = "+proj=longlat +datum=WGS84 +no_defs"
UTM = "+proj=utm +zone=45 +datum=WGS84 +units=m +no_defs"
def dist_km(lon, lat, lon0=USGS[0], lat0=USGS[1]):
    r = 6371.0
    p1, p2 = math.radians(lat0), math.radians(lat)
    dphi = math.radians(lat - lat0)
    dl = math.radians(lon - lon0)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return round(2 * r * math.asin(min(1.0, math.sqrt(a))), 2)


SCL_NAME = {
    0: "nodata",
    1: "saturado",
    2: "sombra_oscura",
    3: "sombra_nube",
    4: "vegetacion",
    5: "no_vegetado",
    6: "agua",
    7: "sin_clasificar",
    8: "nube_media",
    9: "nube_alta",
    10: "cirros",
    11: "nieve_hielo",
}


def s2_href(iid: str, asset: str) -> str:
    url = f"https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a/items/{iid}"
    r = requests.get(url, headers=HEADERS, timeout=60)
    r.raise_for_status()
    return r.json()["assets"][asset]["href"]


def sample_scl(iid: str, lon: float, lat: float, pad_m=2500.0):
    print(f"  SCL {iid} @ {lon:.3f},{lat:.3f}", flush=True)
    href = s2_href(iid, "scl")
    print(f"    open {href.split('/')[-1]}", flush=True)
    with rasterio.open(href) as src:
        to_src = pyproj.Transformer.from_crs(WGS84, src.crs, always_xy=True)
        x, y = to_src.transform(lon, lat)
        if src.crs.is_geographic:
            d = pad_m / 111000.0
            win = from_bounds(lon - d, lat - d, lon + d, lat + d, transform=src.transform)
        else:
            win = from_bounds(x - pad_m, y - pad_m, x + pad_m, y + pad_m, transform=src.transform)
        win = win.round_offsets().round_lengths()
        if win.width <= 2 or win.height <= 2:
            return {"id": iid, "error": f"ventana vacia {win}"}
        arr = src.read(1, window=win)
        r, c = src.index(x, y)
        r0, c0 = int(win.row_off), int(win.col_off)
        pr, pc = r - r0, c - c0
        pix = int(arr[pr, pc]) if 0 <= pr < arr.shape[0] and 0 <= pc < arr.shape[1] else -1
        vals, cnt = np.unique(arr, return_counts=True)
        dist = {
            SCL_NAME.get(int(v), str(int(v))): round(100.0 * int(n) / arr.size, 1)
            for v, n in zip(vals, cnt)
        }
        cloud = (
            dist.get("nube_media", 0)
            + dist.get("nube_alta", 0)
            + dist.get("cirros", 0)
            + dist.get("sombra_nube", 0)
        )
        return {
            "id": iid,
            "pixel_centro": SCL_NAME.get(pix, str(pix)),
            "nube_pct_ventana": round(cloud, 1),
            "hielo_pct_ventana": dist.get("nieve_hielo", 0),
            "hist": dist,
        }


def scl_window(iid: str, bbox):
    west, south, east, north = bbox
    href = s2_href(iid, "scl")
    with rasterio.open(href) as src:
        to_src = pyproj.Transformer.from_crs(WGS84, src.crs, always_xy=True)
        xs, ys = to_src.transform(
            [west, east, west, east], [south, south, north, north]
        )
        win = from_bounds(min(xs), min(ys), max(xs), max(ys), transform=src.transform)
        win = win.round_offsets().round_lengths()
        arr = src.read(1, window=win)
        return arr, src.window_transform(win), src.crs


def ice_loss_s2():
    """SCL 24 vs 27 ago: nieve/hielo que deja de serlo (sin nubes)."""
    a0, tf, crs = scl_window(S2_IDS[0], SRC_BBOX)
    a1, tf1, crs1 = scl_window(S2_IDS[1], SRC_BBOX)
    if a0.shape != a1.shape:
        tmp = np.zeros_like(a0)
        reproject(
            a1, tmp, src_transform=tf1, src_crs=crs1, dst_transform=tf, dst_crs=crs,
            resampling=Resampling.nearest, dst_nodata=0,
        )
        a1 = tmp
    cloud = {0, 3, 8, 9, 10}
    v0 = ~np.isin(a0, list(cloud))
    v1 = ~np.isin(a1, list(cloud))
    lost = v0 & v1 & (a0 == 11) & (a1 != 11)
    n = int(lost.sum())
    area_ha = round(n * abs(tf.a * tf.e) / 1e4, 2)
    best = None
    best_mask = None
    if n:
        from scipy import ndimage

        lab, nlab = ndimage.label(lost)
        to_wgs = pyproj.Transformer.from_crs(crs, WGS84, always_xy=True)
        for i in range(1, nlab + 1):
            m = lab == i
            area = float(m.sum()) * abs(tf.a * tf.e)
            if area < 4000:
                continue
            ys, xs = np.where(m)
            x = tf.c + (xs.mean() + 0.5) * tf.a
            y = tf.f + (ys.mean() + 0.5) * tf.e
            lon, lat = to_wgs.transform(x, y)
            rec = {
                "area_ha": round(area / 1e4, 2),
                "lon": round(lon, 5),
                "lat": round(lat, 5),
                "dist_km_usgs": dist_km(lon, lat),
            }
            if best is None or rec["area_ha"] > best["area_ha"]:
                best = rec
                best_mask = m
    geom = None
    if best_mask is not None:
        from shapely.ops import transform as shp_transform

        parts = []
        for gjson, val in shapes(best_mask.astype(np.uint8), mask=best_mask, transform=tf):
            if val == 1:
                parts.append(shape(gjson).buffer(0))
        if parts:
            u = unary_union(parts).simplify(20, preserve_topology=True)
            to_wgs = pyproj.Transformer.from_crs(crs, WGS84, always_xy=True).transform
            geom = mapping(shp_transform(lambda x, y, z=None: to_wgs(x, y), u))
    print("S2 ice_loss ha", area_ha, "mayor", best, flush=True)
    return {"area_ha": area_ha, "pixeles": n, "mayor": best, "geom": geom}


def signed_vv(item_id: str) -> str:
    url = f"https://planetarycomputer.microsoft.com/api/stac/v1/collections/{COLL}/items/{item_id}"
    it = requests.get(url, headers=HEADERS, timeout=60).json()
    href = it["assets"]["vv"]["href"]
    tok = requests.get(
        f"https://planetarycomputer.microsoft.com/api/sas/v1/token/{COLL}",
        headers=HEADERS,
        timeout=60,
    ).json()["token"]
    return href + "?" + tok


def read_geocoded(href: str, bbox):
    """Recorta AOI (~20 m UTM). MPC GRD suele traer affine 4326 o GCPs."""
    from rasterio.transform import rowcol

    west, south, east, north = bbox
    pad = 0.015
    west, south, east, north = west - pad, south - pad, east + pad, north + pad
    with rasterio.open(href) as src:
        gcps, gcp_crs = src.gcps
        print(
            "S1 open", src.width, src.height, "crs", src.crs,
            "ident", src.transform.is_identity, "gcps", 0 if gcps is None else len(gcps),
            flush=True,
        )
        src_crs = src.crs
        if src_crs and not src.transform.is_identity:
            win = from_bounds(west, south, east, north, transform=src.transform)
            win = win.round_offsets().round_lengths()
            arr = src.read(1, window=win).astype("float32")
            src_tf = src.window_transform(win)
            print("S1 window affine", arr.shape, flush=True)
        else:
            gcp_tf = from_gcps(gcps)
            rows, cols = [], []
            for lon, lat in ((west, south), (west, north), (east, south), (east, north)):
                r, c = rowcol(gcp_tf, lon, lat)
                rows.append(r)
                cols.append(c)
            r0 = int(max(0, min(rows) - 80))
            r1 = int(min(src.height, max(rows) + 80))
            c0 = int(max(0, min(cols) - 80))
            c1 = int(min(src.width, max(cols) + 80))
            if (r1 - r0) < 50 or (c1 - c0) < 50:
                raise RuntimeError(f"ventana S1 degenerada {r0,r1,c0,c1}")
            win = Window.from_slices((r0, r1), (c0, c1))
            arr = src.read(1, window=win).astype("float32")
            adj = [
                GroundControlPoint(row=g.row - r0, col=g.col - c0, x=g.x, y=g.y, z=g.z)
                for g in gcps
                if r0 - 80 <= g.row <= r1 + 80 and c0 - 80 <= g.col <= c1 + 80
            ]
            if len(adj) < 6:
                adj = [
                    GroundControlPoint(row=g.row - r0, col=g.col - c0, x=g.x, y=g.y, z=g.z)
                    for g in gcps
                ]
            src_tf = from_gcps(adj)
            src_crs = gcp_crs or "EPSG:4326"
            print("S1 window gcp", arr.shape, "gcps", len(adj), "pix", r0, r1, c0, c1, flush=True)
        dst_crs = rasterio.crs.CRS.from_string(UTM)
        src_crs_obj = rasterio.crs.CRS.from_user_input(src_crs)
        bounds = rasterio.transform.array_bounds(arr.shape[0], arr.shape[1], src_tf)
        dst_tf, dw, dh = calculate_default_transform(
            src_crs_obj, dst_crs, arr.shape[1], arr.shape[0], *bounds, resolution=20,
        )
        dst = np.full((dh, dw), np.nan, dtype="float32")
        reproject(
            source=arr,
            destination=dst,
            src_transform=src_tf,
            src_crs=src_crs_obj,
            dst_transform=dst_tf,
            dst_crs=dst_crs,
            resampling=Resampling.bilinear,
            src_nodata=0,
            dst_nodata=np.nan,
        )
        print("S1 warped", dst.shape, "finite", int(np.isfinite(dst).sum()), flush=True)
        return dst, dst_tf, dst_crs


def to_db(a):
    a = np.where(a > 0, a, np.nan)
    return 10.0 * np.log10(a)


def main():
    report = {
        "usgs_landslide": {
            "lon": USGS[0],
            "lat": USGS[1],
            "nota": "USGS M5.2 landslide-type 26 ago 2026 08:37 NPT; flanco N Langtang ~5600 m",
        },
        "rasuwagadhi": {"lon": RASUWA[0], "lat": RASUWA[1]},
        "s2_scl_usgs": [],
        "s2_scl_rasuwagadhi": [],
        "s1": {},
    }
    print("=== SCL cabecera USGS / Rasuwagadhi ===", flush=True)
    for iid in S2_IDS:
        try:
            u = sample_scl(iid, USGS[0], USGS[1])
            r = sample_scl(iid, RASUWA[0], RASUWA[1])
            print("S2 USGS", iid, u, flush=True)
            print("S2 RASU", iid, r.get("pixel_centro"), "nube", r.get("nube_pct_ventana"), flush=True)
            report["s2_scl_usgs"].append(u)
            report["s2_scl_rasuwagadhi"].append(r)
        except Exception as ex:
            print("S2 fail", iid, type(ex).__name__, ex, flush=True)
            report["s2_scl_usgs"].append({"id": iid, "error": str(ex)})

    try:
        report["s2_ice_loss_24_27"] = ice_loss_s2()
    except Exception as ex:
        print("S2 ice_loss fail", type(ex).__name__, ex, flush=True)
        report["s2_ice_loss_24_27"] = {"error": str(ex)}

    (OUT / "origen_avalancha_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    try:
        print("=== S1 16 vs 28 ago, bbox cabecera ===", flush=True)
        href0 = signed_vv(ID_BEFORE)
        href1 = signed_vv(ID_AFTER)
        print("geocode 16 ago...", flush=True)
        a0, tf, crs = read_geocoded(href0, SRC_BBOX)
        print("geocode 28 ago...", flush=True)
        a1, tf1, _ = read_geocoded(href1, SRC_BBOX)
        if a0.shape != a1.shape:
            tmp = np.full_like(a0, np.nan)
            reproject(
                a1, tmp, src_transform=tf1, src_crs=crs, dst_transform=tf, dst_crs=crs,
                resampling=Resampling.bilinear, dst_nodata=np.nan,
            )
            a1 = tmp
        d0, d1 = to_db(a0), to_db(a1)
        ratio = d1 - d0
        # colapso de hielo/roca: caida fuerte de backscatter (superficie lisa/humeda o sombra)
        # o subida (escarpe rugoso). Tomar |dB| alto.
        mag = np.abs(ratio)
        ok = np.isfinite(mag)
        thr = 3.5
        mask = ok & (mag >= thr)
        from scipy import ndimage

        lab, nlab = ndimage.label(mask)
        feats = []
        best = None
        to_wgs = pyproj.Transformer.from_crs(crs, WGS84, always_xy=True)
        for i in range(1, nlab + 1):
            m = lab == i
            area_m2 = float(m.sum()) * abs(tf.a * tf.e)
            if area_m2 < 4000:
                continue
            ys, xs = np.where(m)
            cy, cx = float(ys.mean()), float(xs.mean())
            x = tf.c + (cx + 0.5) * tf.a
            y = tf.f + (cy + 0.5) * tf.e
            lon, lat = to_wgs.transform(x, y)
            mean_db = float(np.nanmean(ratio[m]))
            rec = {
                "area_ha": round(area_m2 / 1e4, 2),
                "lon": round(lon, 5),
                "lat": round(lat, 5),
                "mean_db": round(mean_db, 2),
                "dist_km_usgs": dist_km(lon, lat),
            }
            feats.append(rec)
        feats.sort(key=lambda r: (r["dist_km_usgs"], -r["area_ha"]))
        best = max(feats, key=lambda r: r["area_ha"]) if feats else None
        cerca = next((r for r in feats if r["dist_km_usgs"] <= 3.0), None)
        gj_feats = []
        gj_feats.append(
            {
                "type": "Feature",
                "properties": {
                    "clase": "origen_usgs",
                    "nombre": "USGS M5.2 landslide 08:37 NPT",
                    "fuente": "USGS / flanco N Langtang ~5600 m",
                },
                "geometry": {"type": "Point", "coordinates": [USGS[0], USGS[1]]},
            }
        )
        if cerca:
            gj_feats.append(
                {
                    "type": "Feature",
                    "properties": {
                        "clase": "origen_s1",
                        "nombre": "Cambio S1 VV 16 vs 28 ago (mas cercano a USGS, ≤3 km)",
                        "area_ha": cerca["area_ha"],
                        "mean_db": cerca["mean_db"],
                        "dist_km_usgs": cerca["dist_km_usgs"],
                    },
                    "geometry": {"type": "Point", "coordinates": [cerca["lon"], cerca["lat"]]},
                }
            )
        ice = report.get("s2_ice_loss_24_27") or {}
        if ice.get("mayor"):
            b = ice["mayor"]
            gj_feats.append(
                {
                    "type": "Feature",
                    "properties": {
                        "clase": "origen_s2",
                        "nombre": "Mayor perdida de hielo SCL 24 vs 27 ago",
                        "area_ha": b["area_ha"],
                        "dist_km_usgs": b.get("dist_km_usgs"),
                    },
                    "geometry": {"type": "Point", "coordinates": [b["lon"], b["lat"]]},
                }
            )
        if ice.get("geom"):
            gj_feats.append(
                {
                    "type": "Feature",
                    "properties": {
                        "clase": "cicatriz_s2",
                        "nombre": "Perdida de hielo SCL 24 vs 27 (parche mayor)",
                        "area_ha": (ice.get("mayor") or {}).get("area_ha"),
                    },
                    "geometry": ice["geom"],
                }
            )
        gj = {"type": "FeatureCollection", "features": gj_feats}
        dest = OUT / "origen_avalancha.geojson"
        dest.write_text(json.dumps(gj, ensure_ascii=False), encoding="utf-8")
        report["s1"] = {
            "par": [ID_BEFORE, ID_AFTER],
            "umbral_db": thr,
            "n_parches": len(feats),
            "area_ha": round(sum(f["area_ha"] for f in feats), 2),
            "mayor": best,
            "cerca_usgs_3km": cerca,
            "parches_cerca": [f for f in feats if f["dist_km_usgs"] <= 5][:12],
            "geojson": dest.name,
        }
        print("S1 cabecera ha", report["s1"]["area_ha"], "cerca", cerca, "mayor", best, flush=True)
    except Exception as ex:
        print("S1 fail", type(ex).__name__, ex, flush=True)
        report["s1"] = {"error": str(ex)}
        ice = report.get("s2_ice_loss_24_27") or {}
        feats_fb = [
            {
                "type": "Feature",
                "properties": {
                    "clase": "origen_usgs",
                    "nombre": "USGS M5.2 landslide 08:37 NPT",
                    "fuente": "USGS / flanco N Langtang ~5600 m",
                },
                "geometry": {"type": "Point", "coordinates": [USGS[0], USGS[1]]},
            }
        ]
        if ice.get("mayor"):
            b = ice["mayor"]
            feats_fb.append(
                {
                    "type": "Feature",
                    "properties": {
                        "clase": "origen_s2",
                        "nombre": "Mayor perdida de hielo SCL 24 vs 27 ago",
                        "area_ha": b["area_ha"],
                    },
                    "geometry": {"type": "Point", "coordinates": [b["lon"], b["lat"]]},
                }
            )
        (OUT / "origen_avalancha.geojson").write_text(
            json.dumps({"type": "FeatureCollection", "features": feats_fb}, ensure_ascii=False),
            encoding="utf-8",
        )

    ice = report.get("s2_ice_loss_24_27")
    if isinstance(ice, dict):
        ice.pop("geom", None)
    (OUT / "origen_avalancha_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("wrote origen_avalancha_report.json", flush=True)


if __name__ == "__main__":
    main()
