# -*- coding: utf-8 -*-
"""Agua nueva en cabecera: S1 VV oscuro el 28 ago que no lo era el 16, + SCL clase 6."""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pyproj
import rasterio
from rasterio.enums import Resampling
from rasterio.features import shapes
from rasterio.warp import reproject
from shapely.geometry import mapping, shape
from shapely.ops import transform as shp_transform, unary_union
from scipy import ndimage

from detectar_origen_sentinel import (
    HEADERS,
    ID_AFTER,
    ID_BEFORE,
    OUT,
    S2_IDS,
    WGS84,
    read_geocoded,
    s2_href,
    sample_scl,
    to_db,
)
import requests

_SAS = None
ID_RTC_BEFORE = ID_BEFORE + "_rtc"
ID_RTC_AFTER = ID_AFTER + "_rtc"


def signed_rtc(item_id: str, pol: str = "vv") -> str:
    global _SAS
    url = f"https://planetarycomputer.microsoft.com/api/stac/v1/collections/sentinel-1-rtc/items/{item_id}"
    it = requests.get(url, headers=HEADERS, timeout=60).json()
    href = it["assets"][pol]["href"]
    if not _SAS:
        tok = requests.get(
            "https://planetarycomputer.microsoft.com/api/sas/v1/token/sentinel-1-rtc",
            headers=HEADERS,
            timeout=60,
        )
        tok.raise_for_status()
        body = tok.json()
        _SAS = body.get("token")
        if not _SAS:
            raise RuntimeError(f"SAS RTC sin token: {list(body)}")
    return href + "?" + _SAS


def read_rtc(href: str, bbox):
    from rasterio.windows import from_bounds

    west, south, east, north = bbox
    with rasterio.open(href) as src:
        to_src = pyproj.Transformer.from_crs(WGS84, src.crs, always_xy=True)
        xs, ys = to_src.transform(
            [west, east, west, east], [south, south, north, north]
        )
        win = from_bounds(min(xs), min(ys), max(xs), max(ys), transform=src.transform)
        win = win.round_offsets().round_lengths()
        arr = src.read(1, window=win).astype("float32")
        nodata = src.nodata
        if nodata is not None:
            arr = np.where(arr == nodata, np.nan, arr)
        tf = src.window_transform(win)
        finite = arr[np.isfinite(arr)]
        med = float(np.nanmedian(finite)) if finite.size else float("nan")
        print(
            "RTC window", arr.shape, "crs", src.crs,
            "min", round(float(np.nanmin(finite)), 3) if finite.size else None,
            "p5", round(float(np.nanpercentile(finite, 5)), 3) if finite.size else None,
            "med", round(med, 3),
            flush=True,
        )
        if finite.size and med > 0:
            arr = 10.0 * np.log10(np.where(arr > 0, arr, np.nan))
            print("RTC convertido a dB", flush=True)
        return arr, tf, src.crs

# Suhora/Satellogic 27 ago 04:22 UTC: 20.25 ha
HINDU = (85.510806, 28.294167)  # lon, lat  28°17'39.0"N  85°30'38.9"E
# Keystone (confianza media): confluencia Chhochen / Purepu
KEYSTONE = (85.55406, 28.31249)
LAKE_BBOX = (85.48, 28.25, 85.60, 28.36)  # W S E N
MIN_HA = 0.5
WATER_DB = -17.0
DROP_DB = 3.5
BEFORE_NOT_WATER = -14.0


def dist_km(lon, lat, lon0, lat0):
    r = 6371.0
    p1, p2 = math.radians(lat0), math.radians(lat)
    dphi = math.radians(lat - lat0)
    dl = math.radians(lon - lon0)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return round(2 * r * math.asin(min(1.0, math.sqrt(a))), 2)


def sample_db(arr, tf, crs, lon, lat):
    to_src = pyproj.Transformer.from_crs(WGS84, crs, always_xy=True)
    x, y = to_src.transform(lon, lat)
    r, c = rasterio.transform.rowcol(tf, x, y)
    if 0 <= r < arr.shape[0] and 0 <= c < arr.shape[1]:
        v = arr[r, c]
        return None if not np.isfinite(v) else round(float(v), 2)
    return None


def scl_window(iid, bbox):
    west, south, east, north = bbox
    href = s2_href(iid, "scl")
    with rasterio.open(href) as src:
        to_src = pyproj.Transformer.from_crs(WGS84, src.crs, always_xy=True)
        xs, ys = to_src.transform(
            [west, east, west, east], [south, south, north, north]
        )
        from rasterio.windows import from_bounds

        win = from_bounds(min(xs), min(ys), max(xs), max(ys), transform=src.transform)
        win = win.round_offsets().round_lengths()
        arr = src.read(1, window=win)
        return arr, src.window_transform(win), src.crs


def s2_new_water():
    a0, tf, crs = scl_window(S2_IDS[0], LAKE_BBOX)
    a1, tf1, crs1 = scl_window(S2_IDS[1], LAKE_BBOX)
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
    nw = v0 & v1 & (a1 == 6) & (a0 != 6)
    n = int(nw.sum())
    area_ha = round(n * abs(tf.a * tf.e) / 1e4, 2)
    print("S2 agua nueva (SCL 6) ha", area_ha, "pix", n, flush=True)
    return nw, tf, crs, area_ha


def vectorize(mask, tf, crs, clase, extra_props=None):
    feats = []
    parts = []
    to_wgs = pyproj.Transformer.from_crs(crs, WGS84, always_xy=True)
    lab, nlab = ndimage.label(mask)
    for i in range(1, nlab + 1):
        m = lab == i
        area_m2 = float(m.sum()) * abs(tf.a * tf.e)
        if area_m2 < MIN_HA * 1e4:
            continue
        ys, xs = np.where(m)
        x = tf.c + (xs.mean() + 0.5) * tf.a
        y = tf.f + (ys.mean() + 0.5) * tf.e
        lon, lat = to_wgs.transform(x, y)
        rec = {
            "area_ha": round(area_m2 / 1e4, 2),
            "lon": round(lon, 5),
            "lat": round(lat, 5),
            "dist_km_suhora": dist_km(lon, lat, HINDU[0], HINDU[1]),
            "dist_km_keystone": dist_km(lon, lat, KEYSTONE[0], KEYSTONE[1]),
        }
        feats.append(rec)
        geom_parts = []
        for gjson, val in shapes(m.astype(np.uint8), mask=m, transform=tf):
            if val == 1:
                geom_parts.append(shape(gjson).buffer(0))
        if geom_parts:
            u = unary_union(geom_parts).simplify(20, preserve_topology=True)
            uw = shp_transform(lambda x, y, z=None: to_wgs.transform(x, y), u)
            props = {"clase": clase, **rec}
            if extra_props:
                props.update(extra_props)
            parts.append(
                {"type": "Feature", "properties": props, "geometry": mapping(uw)}
            )
    feats.sort(key=lambda r: -r["area_ha"])
    return feats, parts


def main():
    report = {
        "puntos": {
            "suhora_satellogic": {
                "lon": HINDU[0],
                "lat": HINDU[1],
                "ha_reportada": 20.25,
                "fecha_optica": "2026-08-27T04:22:00Z",
            },
            "keystone_inferido": {
                "lon": KEYSTONE[0],
                "lat": KEYSTONE[1],
                "nota": "confluencia Chhochen/Purepu, confianza media",
            },
        },
        "nota": (
            "S1 28 ago 12:21 UTC: el lago bajo ya desbordaba ese dia; "
            "China dice vaciado el 30 ago. Buscamos agua nueva (VV oscuro) "
            "que no lo era el 16 ago."
        ),
    }
    print("=== SCL en puntos reportados ===", flush=True)
    for name, pt in (("suhora", HINDU), ("keystone", KEYSTONE)):
        report.setdefault("s2_scl", {})[name] = []
        for iid in S2_IDS:
            try:
                u = sample_scl(iid, pt[0], pt[1], pad_m=1500.0)
                print(name, iid, u.get("pixel_centro"), "agua", (u.get("hist") or {}).get("agua"), flush=True)
                report["s2_scl"][name].append(u)
            except Exception as ex:
                print("SCL fail", name, iid, ex, flush=True)

    try:
        nw, tf_s2, crs_s2, ha_s2 = s2_new_water()
        s2_feats, s2_gj = vectorize(nw, tf_s2, crs_s2, "lago_s2_scl")
        report["s2_agua_nueva_ha"] = ha_s2
        report["s2_parches"] = s2_feats[:10]
        print("S2 parches", s2_feats[:5], flush=True)
    except Exception as ex:
        print("S2 water fail", type(ex).__name__, ex, flush=True)
        s2_gj = []
        report["s2_agua_nueva"] = {"error": str(ex)}

    s1_gj = []
    print("=== S1 RTC VV agua nueva 16 vs 28 ===", flush=True)
    try:
        href0 = signed_rtc(ID_RTC_BEFORE)
        href1 = signed_rtc(ID_RTC_AFTER)
        print("geocode RTC 16 ago...", flush=True)
        a0, tf, crs = read_rtc(href0, LAKE_BBOX)
        print("geocode RTC 28 ago...", flush=True)
        a1, tf1, _ = read_rtc(href1, LAKE_BBOX)
        if a0.shape != a1.shape:
            tmp = np.full_like(a0, np.nan)
            reproject(
                a1, tmp, src_transform=tf1, src_crs=crs, dst_transform=tf, dst_crs=crs,
                resampling=Resampling.bilinear, dst_nodata=np.nan,
            )
            a1 = tmp
        d0, d1 = a0, a1
        ratio = d1 - d0
        report["s1_muestras"] = {
            "suhora": {
                "vv_16db": sample_db(d0, tf, crs, *HINDU),
                "vv_28db": sample_db(d1, tf, crs, *HINDU),
            },
            "keystone": {
                "vv_16db": sample_db(d0, tf, crs, *KEYSTONE),
                "vv_28db": sample_db(d1, tf, crs, *KEYSTONE),
            },
        }
        print("muestras dB", report["s1_muestras"], flush=True)

        ok = np.isfinite(d0) & np.isfinite(d1)
        mask = (
            ok
            & (d1 < WATER_DB)
            & (ratio <= -DROP_DB)
            & (d0 > BEFORE_NOT_WATER)
        )
        print("pix agua", int(mask.sum()), "ha", round(int(mask.sum()) * 400 / 1e4, 2), flush=True)
        s1_feats, s1_gj = vectorize(
            mask, tf, crs, "lago_s1",
            extra_props={"umbral_db": WATER_DB, "caida_db": DROP_DB, "par": "16vs28"},
        )
        report["s1_parches"] = s1_feats[:12]
        report["s1_n_parches"] = len(s1_feats)
        report["s1_area_ha"] = round(sum(f["area_ha"] for f in s1_feats), 2)
        print("S1 parches", s1_feats[:8], flush=True)
        s1_gj = [
            f for f in s1_gj
            if (f["properties"].get("dist_km_suhora") or 99) <= 1.0
            or (f["properties"].get("dist_km_keystone") or 99) <= 1.0
        ]
        cerca = [f for f in s1_feats if f["dist_km_suhora"] <= 1.0]
        if not cerca:
            mask2 = ok & (d1 < -15.0) & (ratio <= -2.5) & (d0 > -13.0)
            f2, g2 = vectorize(
                mask2, tf, crs, "lago_s1_lax",
                extra_props={"umbral_db": -15.0, "caida_db": 2.5, "par": "16vs28"},
            )
            print("S1 lax parches", f2[:8], flush=True)
            report["s1_parches_lax"] = f2[:12]
            s1_gj = s1_gj + g2
    except Exception as ex:
        print("S1 fail", type(ex).__name__, ex, flush=True)
        report["s1"] = {"error": str(ex)}

    gj_feats = list(s1_gj) + list(s2_gj)
    gj_feats.append(
        {
            "type": "Feature",
            "properties": {
                "clase": "lago_reportado",
                "nombre": "Suhora/Satellogic 27 ago 20.25 ha",
            },
            "geometry": {"type": "Point", "coordinates": [HINDU[0], HINDU[1]]},
        }
    )
    gj_feats.append(
        {
            "type": "Feature",
            "properties": {
                "clase": "lago_reportado",
                "nombre": "Keystone inferido Chhochen/Purepu",
            },
            "geometry": {"type": "Point", "coordinates": [KEYSTONE[0], KEYSTONE[1]]},
        }
    )
    dest = OUT / "lago_escombros.geojson"
    dest.write_text(json.dumps({"type": "FeatureCollection", "features": gj_feats}, ensure_ascii=False), encoding="utf-8")
    (OUT / "lago_escombros_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("wrote", dest.name, "feats", len(gj_feats), flush=True)


if __name__ == "__main__":
    main()
