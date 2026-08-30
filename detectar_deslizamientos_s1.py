# -*- coding: utf-8 -*-
"""Cicatrices (≥0.5 km²) al norte de Rasuwagadhi: S1 RTC ago 2021 vs ago 2026."""
from __future__ import annotations

import json
import os
from pathlib import Path

os.environ["GDAL_HTTP_UNSAFESSL"] = "YES"
os.environ["CPL_VSIL_CURL_ALLOWED_EXTENSIONS"] = ".tif,.tiff,.TIF"
os.environ["GDAL_HTTP_TIMEOUT"] = "90"
os.environ["CPL_VSIL_CURL_USE_HEAD"] = "NO"

import numpy as np
import pyproj
import rasterio
import requests
from rasterio.enums import Resampling
from rasterio.features import rasterize, shapes
from rasterio.warp import reproject
from rasterio.windows import from_bounds
from scipy import ndimage
from shapely.geometry import Point, box, mapping, shape
from shapely.ops import transform as shp_transform, unary_union

OUT = Path(__file__).resolve().parent
HEADERS = {"User-Agent": "ABC-Geomatica-Nepal/1.0"}
WGS84 = "+proj=longlat +datum=WGS84 +no_defs"
UTM = "+proj=utm +zone=45 +datum=WGS84 +units=m +no_defs"

RASUWA = (85.3777789, 28.2777749)  # lon, lat
RADIO_M = 50000.0
MIN_KM2 = 0.5
MAX_KM2 = 20.0
THR_DB = 6.5
MEAN_ABS_MIN = 5.5
Z_MAX = 5200.0
SLOPE_MIN = 10.0
# Órbita 85 ascendente, ~5 años, misma geometría que el par 16/28 ago 2026.
ID_BEFORE = "S1A_IW_GRDH_1SDV_20210823T122228_20210823T122253_039357_04A5F9_rtc"
ID_AFTER = "S1D_IW_GRDH_1SDV_20260828T122141_20260828T122206_004326_007FA4_rtc"
PAR_LABEL = "2021-08-23 vs 2026-08-28"
COP30_TILES = [
    OUT / "Copernicus_DSM_COG_10_N28_00_E084_00_DEM.tif",
    OUT / "Copernicus_DSM_COG_10_N28_00_E085_00_DEM.tif",
]
COP30_URLS = {
    "Copernicus_DSM_COG_10_N28_00_E084_00_DEM.tif": [
        "https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N28_00_E084_00_DEM/Copernicus_DSM_COG_10_N28_00_E084_00_DEM.tif",
        "https://copernicus-dem-30m.s3.eu-central-1.amazonaws.com/Copernicus_DSM_COG_10_N28_00_E084_00_DEM/Copernicus_DSM_COG_10_N28_00_E084_00_DEM.tif",
    ],
    "Copernicus_DSM_COG_10_N28_00_E085_00_DEM.tif": [
        "https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N28_00_E085_00_DEM/Copernicus_DSM_COG_10_N28_00_E085_00_DEM.tif",
    ],
}
# Cuadrado que envuelve el semicírculo de 50 km.
BBOX = (84.86, 28.26, 85.90, 28.74)  # W S E N


_SAS = None


def rtc_token():
    global _SAS
    if _SAS:
        return _SAS
    last = None
    for i in range(5):
        tok = requests.get(
            "https://planetarycomputer.microsoft.com/api/sas/v1/token/sentinel-1-rtc",
            headers=HEADERS,
            timeout=60,
        )
        if tok.status_code == 429:
            wait = 20 * (i + 1)
            print(f"SAS 429, espero {wait}s", flush=True)
            import time

            time.sleep(wait)
            last = tok
            continue
        tok.raise_for_status()
        token = tok.json().get("token")
        if not token:
            raise RuntimeError("SAS RTC sin token")
        _SAS = token
        return _SAS
    raise RuntimeError(f"SAS RTC 429 persistente: {getattr(last, 'status_code', None)}")


def signed_rtc_vv(item_id: str) -> str:
    url = f"https://planetarycomputer.microsoft.com/api/stac/v1/collections/sentinel-1-rtc/items/{item_id}"
    it = requests.get(url, headers=HEADERS, timeout=60)
    it.raise_for_status()
    href = it.json()["assets"]["vv"]["href"]
    return href + "?" + rtc_token()


def ensure_cop30():
    for path in COP30_TILES:
        if path.exists() and path.stat().st_size > 5e6:
            print("COP30 local", path.name, round(path.stat().st_size / 1e6, 1), "MB", flush=True)
            continue
        urls = COP30_URLS.get(path.name) or []
        ok = False
        for url in urls:
            try:
                print("descargando", path.name, flush=True)
                r = requests.get(url, headers=HEADERS, timeout=300, stream=True)
                r.raise_for_status()
                tmp = path.with_suffix(".tif.part")
                with open(tmp, "wb") as f:
                    for chunk in r.iter_content(1024 * 1024):
                        if chunk:
                            f.write(chunk)
                os.replace(tmp, path)
                print("COP30 escrito", path.name, round(path.stat().st_size / 1e6, 1), "MB", flush=True)
                ok = True
                break
            except Exception as ex:
                print("COP30 fail", url, ex, flush=True)
        if not ok:
            print("AVISO: falta", path.name, flush=True)


def cache_path(tag: str) -> Path:
    return OUT / f"s1_rtc_norte50_{tag}.tif"


def save_cache(path: Path, arr, tf, crs):
    profile = {
        "driver": "GTiff",
        "height": arr.shape[0],
        "width": arr.shape[1],
        "count": 1,
        "dtype": "float32",
        "crs": crs,
        "transform": tf,
        "compress": "lzw",
        "nodata": np.nan,
    }
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(arr, 1)
    print("cache", path.name, round(path.stat().st_size / 1e6, 1), "MB", flush=True)


def load_cache(path: Path):
    with rasterio.open(path) as src:
        arr = src.read(1).astype("float32")
        print("cache local", path.name, arr.shape, flush=True)
        return arr, src.transform, src.crs


def read_rtc(href: str, bbox):
    west, south, east, north = bbox
    with rasterio.open(href) as src:
        to_src = pyproj.Transformer.from_crs(WGS84, src.crs, always_xy=True)
        xs, ys = to_src.transform(
            [west, east, west, east], [south, south, north, north]
        )
        win = from_bounds(min(xs), min(ys), max(xs), max(ys), transform=src.transform)
        win = win.round_offsets().round_lengths()
        arr = src.read(1, window=win).astype("float32")
        if src.nodata is not None:
            arr = np.where(arr == src.nodata, np.nan, arr)
        tf = src.window_transform(win)
        finite = arr[np.isfinite(arr)]
        med = float(np.nanmedian(finite)) if finite.size else float("nan")
        print(
            "RTC", arr.shape, src.crs, "med", None if not finite.size else round(med, 3),
            flush=True,
        )
        if finite.size and med > 0:
            arr = 10.0 * np.log10(np.where(arr > 0, arr, np.nan))
            print("RTC → dB", flush=True)
        return arr, tf, src.crs


def semicircle_utm():
    to_utm = pyproj.Transformer.from_crs(WGS84, UTM, always_xy=True)
    x, y = to_utm.transform(RASUWA[0], RASUWA[1])
    full = Point(x, y).buffer(RADIO_M)
    north = box(x - RADIO_M - 50, y, x + RADIO_M + 50, y + RADIO_M + 50)
    return full.intersection(north), (x, y)


def raster_mask(geom_utm, tf, crs, shape_hw):
    to_r = pyproj.Transformer.from_crs(UTM, crs, always_xy=True)
    g = shp_transform(lambda x, y, z=None: to_r.transform(x, y), geom_utm)
    return rasterize(
        [(g, 1)],
        out_shape=shape_hw,
        transform=tf,
        fill=0,
        dtype="uint8",
    ).astype(bool)


def warp_to(src_arr, src_tf, src_crs, dst_tf, dst_crs, dst_shape):
    out = np.full(dst_shape, np.nan, dtype="float32")
    reproject(
        src_arr,
        out,
        src_transform=src_tf,
        src_crs=src_crs,
        dst_transform=dst_tf,
        dst_crs=dst_crs,
        resampling=Resampling.bilinear,
        src_nodata=np.nan,
        dst_nodata=np.nan,
    )
    return out


def dem_z_slope(tf, crs, hw):
    ensure_cop30()
    z = np.full(hw, np.nan, dtype="float32")
    for path in COP30_TILES:
        if not path.exists() or path.stat().st_size < 5e6:
            continue
        with rasterio.open(path) as src:
            tile = warp_to(src.read(1).astype("float32"), src.transform, src.crs, tf, crs, hw)
        fill = ~np.isfinite(z) & np.isfinite(tile) & (tile > -1000)
        z[fill] = tile[fill]
    z = np.where((z <= -1000) | ~np.isfinite(z), np.nan, z)
    dy, dx = np.gradient(z, abs(tf.e), abs(tf.a))
    slope = np.degrees(np.arctan(np.hypot(dx, dy)))
    print(
        "DEM z",
        None if not np.isfinite(z).any() else round(float(np.nanmedian(z)), 0),
        "slope med",
        None if not np.isfinite(slope).any() else round(float(np.nanmedian(slope)), 1),
        flush=True,
    )
    return z, slope


def vectorize(mask, tf, crs, dlt, aoi):
    to_wgs = pyproj.Transformer.from_crs(crs, WGS84, always_xy=True)
    to_utm = pyproj.Transformer.from_crs(crs, UTM, always_xy=True)
    to_ll = pyproj.Transformer.from_crs(UTM, WGS84, always_xy=True)
    lab, nlab = ndimage.label(mask)
    pix_m2 = abs(tf.a * tf.e)
    sizes = ndimage.sum(mask, lab, index=np.arange(1, nlab + 1)) if nlab else []
    keep = [
        i + 1
        for i, n in enumerate(sizes)
        if MIN_KM2 * 1e6 <= float(n) * pix_m2 <= MAX_KM2 * 1e6
    ]
    print("componentes grandes", len(keep), "/", nlab, flush=True)
    feats = []
    for i in keep:
        m = lab == i
        vals = dlt[m]
        vals = vals[np.isfinite(vals)]
        if vals.size < 20:
            continue
        mean_d = float(np.nanmean(vals))
        med_abs = float(np.nanmedian(np.abs(vals)))
        # El cuerpo entero debe cambiar fuerte: si no, es ruido/nieve soldada.
        if med_abs < MEAN_ABS_MIN:
            continue
        ys, xs = np.where(m)
        x = tf.c + (xs.mean() + 0.5) * tf.a
        y = tf.f + (ys.mean() + 0.5) * tf.e
        lon, lat = to_wgs.transform(x, y)
        geoms = []
        for gjson, val in shapes(m.astype(np.uint8), mask=m, transform=tf):
            if val == 1:
                geoms.append(shape(gjson).buffer(0))
        if not geoms:
            continue
        u = unary_union(geoms).simplify(30, preserve_topology=True)
        u_utm = shp_transform(lambda xx, yy, z=None: to_utm.transform(xx, yy), u)
        clipped = u_utm.intersection(aoi)
        if clipped.is_empty or clipped.area < MIN_KM2 * 1e6 or clipped.area > MAX_KM2 * 1e6:
            continue
        clipped_wgs = shp_transform(lambda xx, yy, z=None: to_ll.transform(xx, yy), clipped)
        feats.append(
            {
                "type": "Feature",
                "properties": {
                    "clase": "deslizamiento_s1",
                    "area_km2": round(clipped.area / 1e6, 2),
                    "lon": round(float(lon), 5),
                    "lat": round(float(lat), 5),
                    "delta_vv_db": round(mean_d, 2),
                    "delta_abs_med_db": round(med_abs, 2),
                    "sentido": "oscurece" if mean_d < 0 else "aclara",
                    "par": PAR_LABEL,
                    "orbita": 85,
                    "fuente": "Sentinel-1 RTC VV (Planetary Computer)",
                },
                "geometry": mapping(clipped_wgs.buffer(0)),
            }
        )
    feats.sort(key=lambda f: -f["properties"]["area_km2"])
    return feats


def aoi_feature(aoi_utm):
    to_wgs = pyproj.Transformer.from_crs(UTM, WGS84, always_xy=True)
    g = shp_transform(lambda x, y, z=None: to_wgs.transform(x, y), aoi_utm)
    radio_km = int(RADIO_M / 1000)
    return {
        "type": "Feature",
        "properties": {
            "clase": "aoi_semicirculo",
            "nombre": f"Semicirculo {radio_km} km al norte de Rasuwagadhi",
            "radio_km": radio_km,
            "centro": "Rasuwagadhi",
        },
        "geometry": mapping(g),
    }


def main():
    radio_km = int(RADIO_M / 1000)
    print(f"=== S1 RTC cicatrices N Rasuwagadhi 2021→2026  r={radio_km} km ===", flush=True)
    c0, c1 = cache_path("20210823"), cache_path("20260828")
    if c0.exists() and c1.exists() and c0.stat().st_size > 1e6 and c1.stat().st_size > 1e6:
        a0, tf, crs = load_cache(c0)
        a1, tf1, crs1 = load_cache(c1)
    else:
        href0 = signed_rtc_vv(ID_BEFORE)
        href1 = signed_rtc_vv(ID_AFTER)
        print("leyendo 2021-08-23...", flush=True)
        a0, tf, crs = read_rtc(href0, BBOX)
        print("leyendo 2026-08-28...", flush=True)
        a1, tf1, crs1 = read_rtc(href1, BBOX)
        save_cache(c0, a0, tf, crs)
        save_cache(c1, a1, tf1, crs1)
    if a0.shape != a1.shape or tf != tf1:
        print("reproyectando 2026 al grid 2021", a0.shape, a1.shape, flush=True)
        a1 = warp_to(a1, tf1, crs1, tf, crs, a0.shape)
    dlt = a1 - a0
    ok = np.isfinite(a0) & np.isfinite(a1)

    aoi, _xy = semicircle_utm()
    semi = raster_mask(aoi, tf, crs, a0.shape)
    z, slope = dem_z_slope(tf, crs, a0.shape)
    terrain = np.ones(a0.shape, dtype=bool)
    if z is not None:
        terrain &= np.isfinite(z) & (z < Z_MAX)
    if slope is not None:
        terrain &= np.isfinite(slope) & (slope >= SLOPE_MIN)

    raw = ok & semi & terrain & (np.abs(dlt) >= THR_DB)
    disk = ndimage.generate_binary_structure(2, 2)
    clean = ndimage.binary_opening(raw, structure=disk, iterations=1)
    clean = ndimage.binary_closing(clean, structure=disk, iterations=2)
    lab0, n0 = ndimage.label(clean)
    sizes = ndimage.sum(clean, lab0, index=np.arange(1, n0 + 1)) if n0 else []
    pix_ha = abs(tf.a * tf.e) / 1e4
    if len(sizes):
        ha = np.array(sizes) * pix_ha
        print(
            "componentes", n0,
            "max_ha", round(float(ha.max()), 1),
            "n>50ha", int((ha >= 50).sum()),
            flush=True,
        )
    print(
        "pix raw", int(raw.sum()),
        "clean", int(clean.sum()),
        "ha clean", round(int(clean.sum()) * pix_ha, 1),
        flush=True,
    )

    scars = vectorize(clean, tf, crs, dlt, aoi)
    print(f"poligonos {MIN_KM2}–{MAX_KM2} km² y |Δ|med≥{MEAN_ABS_MIN}", len(scars), flush=True)
    for f in scars:
        p = f["properties"]
        print(
            f"  {p['area_km2']:6.2f} km²  ΔVV {p['delta_vv_db']:+.1f}  "
            f"|Δ|med {p['delta_abs_med_db']:.1f}  {p['lat']:.4f} {p['lon']:.4f}",
            flush=True,
        )

    gj = {
        "type": "FeatureCollection",
        "properties": {
            "antes": ID_BEFORE,
            "despues": ID_AFTER,
            "umbral_abs_db": THR_DB,
            "delta_abs_med_min_db": MEAN_ABS_MIN,
            "min_km2": MIN_KM2,
            "max_km2": MAX_KM2,
            "z_max_m": Z_MAX,
            "slope_min_deg": SLOPE_MIN,
            "radio_km": radio_km,
            "n": len(scars),
            "area_km2": round(sum(f["properties"]["area_km2"] for f in scars), 2),
        },
        "features": [aoi_feature(aoi)] + scars,
    }
    dest = OUT / "deslizamientos_s1_norte.geojson"
    dest.write_text(json.dumps(gj, ensure_ascii=False), encoding="utf-8")
    report = {
        "par": {"antes": ID_BEFORE, "despues": ID_AFTER, "orbita": 85, "sentido": "ascending", "anos": 5},
        "aoi": {"centro": {"lon": RASUWA[0], "lat": RASUWA[1]}, "radio_km": radio_km, "mitad": "norte"},
        "filtros": {
            "abs_delta_vv_db": THR_DB,
            "delta_abs_med_min_db": MEAN_ABS_MIN,
            "min_km2": MIN_KM2,
            "max_km2": MAX_KM2,
            "z_max_m": Z_MAX,
            "slope_min_deg": SLOPE_MIN,
        },
        "n_poligonos": len(scars),
        "area_km2": gj["properties"]["area_km2"],
        "parches": [f["properties"] for f in scars],
        "nota": (
            f"Cambio Sentinel-1 RTC VV, {PAR_LABEL}, órbita 85 ascendente (~5 años). "
            f"Semicírculo de {radio_km} km al norte de Rasuwagadhi. "
            f"Semillas |ΔVV| ≥ {THR_DB} dB; se quedan parches {MIN_KM2}–{MAX_KM2} km² "
            f"cuya mediana |ΔVV| ≥ {MEAN_ABS_MIN} dB (cambio grande, típico de cicatriz). "
            "Cota < 5200 m y pendiente ≥ 10°. No es EMSR927."
        ),
    }
    (OUT / "deslizamientos_s1_norte_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("wrote", dest.name, "n", len(scars), "km2", gj["properties"]["area_km2"], flush=True)


if __name__ == "__main__":
    main()
