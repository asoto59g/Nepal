# -*- coding: utf-8 -*-
"""Perfil DEM + Manning cada 1 km: Rasuwagadhi → Devighat HEP (Nuwakot)."""
from __future__ import annotations

import heapq
import json
import math
import os
import sys
from datetime import datetime, timedelta
from io import BytesIO

# PostGIS deja PROJ_LIB apuntando a un proj.db viejo; rasterio/pyproj fallan.
import pyproj
_PROJ_DIR = pyproj.datadir.get_data_dir()
os.environ["PROJ_LIB"] = _PROJ_DIR
os.environ["PROJ_DATA"] = _PROJ_DIR
pyproj.datadir.set_data_dir(_PROJ_DIR)

import numpy as np
import rasterio
import requests
from rasterio.io import MemoryFile
from rasterio.warp import transform as rio_transform
from shapely.geometry import LineString, mapping

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
BBOX = (27.86, 85.10, 28.32, 85.42)  # S, W, N, E
HMA_NAME = "HMA_DEM8m_MOS_20170716_tile-675.tif"
HMA_URL = (
    "https://data.nsidc.earthdatacloud.nasa.gov/nsidc-cumulus-prod-protected/"
    "HMA/HMA_DEM8m_MOS/1/2002/01/28/HMA_DEM8m_MOS_20170716_tile-675.tif"
)
OSM_CACHE = os.path.join(OUT_DIR, "rios_overpass.json")
HEADERS = {"User-Agent": "ABCGeomatica-HMA/1.0 (flood-analysis Nepal 2026)"}

# Ancla: estación Syabrubesi deja de transmitir (informe técnico DHM)
T_SYA = datetime(2026, 8, 26, 8, 50)
T_BET = datetime(2026, 8, 26, 9, 20)
T_SMS = datetime(2026, 8, 26, 9, 16)
T_SISMO = datetime(2026, 8, 26, 8, 37)
T_AUTO = datetime(2026, 8, 26, 8, 38)
N_MANN = 0.040  # cauce de montaña con bloques / flujo hiperconcentrado

# Puntos de comunidad (lat, lon) — Nominatim / Wikipedia / GEM
PLACES = [
    {"id": "rasuwagadhi", "nombre": "Rasuwagadhi", "lat": 28.2777749, "lon": 85.3777789},
    {"id": "timure", "nombre": "Timure", "lat": 28.2528483, "lon": 85.3666715},
    {"id": "chilime", "nombre": "Chilime (poblado)", "lat": 28.1836181, "lon": 85.3022373},
    {"id": "syabrubesi", "nombre": "Syabrubesi", "lat": 28.1628146, "lon": 85.3378412},
    {"id": "mailung", "nombre": "Mailung (confluencia)", "lat": 28.0715070, "lon": 85.1978618},
    {"id": "betrawati", "nombre": "Betrawati", "lat": 27.9731085, "lon": 85.1859528},
    {"id": "trishuli", "nombre": "Trishuli HEP / Bazar", "lat": 27.9227451, "lon": 85.1461726},
    {"id": "bidur", "nombre": "Bidur", "lat": 27.8952600, "lon": 85.1464460},
    {"id": "devighat", "nombre": "Devighat HEP (Nuwakot)", "lat": 27.8881907, "lon": 85.1340051},
]


def haversine_m(lat1, lon1, lat2, lon2):
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(min(1.0, a)))


def round_node(lat, lon, nd=5):
    return (round(lat, nd), round(lon, nd))


def fetch_overpass():
    if os.path.exists(OSM_CACHE) and os.path.getsize(OSM_CACHE) > 1000:
        with open(OSM_CACHE, encoding="utf-8") as f:
            data = json.load(f)
        print(f"OSM cache: {len(data.get('elements', []))} ways")
        return data
    s, w, n, e = BBOX
    query = f"""
    [out:json][timeout:180];
    (
      way["waterway"="river"]({s},{w},{n},{e});
    );
    out geom;
    """
    urls = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.osm.ch/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
    ]
    last = None
    for url in urls:
        try:
            r = requests.post(
                url, data={"data": query}, headers=HEADERS, timeout=180
            )
            r.raise_for_status()
            data = r.json()
            nways = len(data.get("elements", []))
            print(f"Overpass {url}: {nways} ways")
            if nways:
                with open(OSM_CACHE, "w", encoding="utf-8") as f:
                    json.dump(data, f)
                return data
        except Exception as ex:
            last = ex
            print("Overpass fail", url, ex)
    raise RuntimeError(f"Overpass failed: {last}")


def build_graph(osm):
    adj = {}
    coords = {}

    def add_node(p):
        if p not in adj:
            adj[p] = []
            coords[p] = p

    for el in osm.get("elements", []):
        geom = el.get("geometry") or []
        if len(geom) < 2:
            continue
        prev = None
        for g in geom:
            p = round_node(g["lat"], g["lon"])
            add_node(p)
            if prev is not None and prev != p:
                d = haversine_m(prev[0], prev[1], p[0], p[1])
                adj[prev].append((p, d))
                adj[p].append((prev, d))
            prev = p

    # unir extremos cercanos (huecos OSM)
    nodes = list(adj.keys())
    # grid hash
    buckets = {}
    for p in nodes:
        key = (round(p[0], 3), round(p[1], 3))
        buckets.setdefault(key, []).append(p)
    for p in nodes:
        i, j = round(p[0], 3), round(p[1], 3)
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                for q in buckets.get((round(i + di * 0.001, 3), round(j + dj * 0.001, 3)), []):
                    if q <= p:
                        continue
                    d = haversine_m(p[0], p[1], q[0], q[1])
                    if 0 < d < 80:
                        adj[p].append((q, d))
                        adj[q].append((p, d))
    print(f"Grafo: {len(adj)} nodos")
    return adj


def nearest_node(adj, lat, lon):
    best, bd = None, 1e18
    for p in adj:
        d = haversine_m(lat, lon, p[0], p[1])
        if d < bd:
            best, bd = p, d
    return best, bd


def dijkstra(adj, start, end):
    pq = [(0.0, start)]
    dist = {start: 0.0}
    prev = {start: None}
    seen = set()
    while pq:
        d, u = heapq.heappop(pq)
        if u in seen:
            continue
        seen.add(u)
        if u == end:
            break
        for v, w in adj[u]:
            nd = d + w
            if nd < dist.get(v, 1e18):
                dist[v] = nd
                prev[v] = u
                heapq.heappush(pq, (nd, v))
    if end not in dist:
        raise RuntimeError("No hay camino fluvial entre Rasuwagadhi y Devighat")
    path = []
    cur = end
    while cur is not None:
        path.append(cur)
        cur = prev[cur]
    path.reverse()
    return path, dist[end]


def densify(path, step_m=50.0):
    out = [path[0]]
    acc = 0.0
    for a, b in zip(path, path[1:]):
        d = haversine_m(a[0], a[1], b[0], b[1])
        if d < 1:
            continue
        n = max(1, int(math.ceil(d / step_m)))
        for i in range(1, n + 1):
            t = i / n
            lat = a[0] + t * (b[0] - a[0])
            lon = a[1] + t * (b[1] - a[1])
            out.append((lat, lon))
            acc += d / n
    return out


def find_hma():
    for root, _dirs, files in os.walk(OUT_DIR):
        for fn in files:
            if fn.lower().endswith(".tif") and "HMA_DEM8m" in fn:
                path = os.path.join(root, fn)
                if os.path.getsize(path) > 50e6:
                    return path
    downloads = os.path.join(os.path.expanduser("~"), "Downloads")
    cand = os.path.join(downloads, HMA_NAME)
    if os.path.exists(cand) and os.path.getsize(cand) > 50e6:
        return cand
    return None


def download_dem():
    """NASA HMA 8 m mosaic tile-675. Requiere Earthdata Login."""
    local = find_hma()
    if local:
        print("HMA local:", local, os.path.getsize(local) / 1e6, "MB")
        return local
    dest = os.path.join(OUT_DIR, HMA_NAME)
    try:
        import earthaccess

        earthaccess.login(strategy="netrc")
        results = earthaccess.search_data(
            short_name="HMA_DEM8m_MOS",
            bounding_box=(85.10, 27.86, 85.42, 28.32),
            count=5,
        )
        if not results:
            raise RuntimeError("CMR no devolvió HMA_DEM8m_MOS en el bbox")
        print("earthaccess granules:", len(results))
        earthaccess.download(results, OUT_DIR)
        local = find_hma()
        if local:
            return local
    except Exception as ex:
        print("earthaccess:", ex)
    raise RuntimeError(
        "Falta el GeoTIFF HMA 8 m (tile-675, ~348 MB). "
        "Inicia sesión en Earthdata y vuelve a pedir la descarga, "
        "o deja HMA_DEM8m_MOS_20170716_tile-675.tif en analisis_manning/."
    )


def sample_z(dem_src, pts):
    """Muestrea el DEM (HMA está en Albers custom). Evita rasterio EPSG/PROJ.db."""
    from pyproj import Transformer

    hma_aea = (
        "+proj=aea +lat_1=25 +lat_2=47 +lat_0=36 +lon_0=85 "
        "+x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"
    )
    wgs84 = "+proj=longlat +datum=WGS84 +no_defs"
    paths = dem_src if isinstance(dem_src, list) else [dem_src]
    zs = np.full(len(pts), np.nan)
    remaining = set(range(len(pts)))
    for path in paths:
        with rasterio.open(path) as src:
            dst = hma_aea
            try:
                p4 = src.crs.to_proj4() if src.crs else ""
                if p4 and "+proj=" in p4:
                    dst = p4
            except Exception:
                pass
            tf = Transformer.from_crs(wgs84, dst, always_xy=True)
            nodata = src.nodata
            idx = sorted(remaining)
            lats = [pts[i][0] for i in idx]
            lons = [pts[i][1] for i in idx]
            xs, ys = tf.transform(lons, lats)
            xy = list(zip(xs, ys))
            vals = list(src.sample(xy))
            for i, v in zip(idx, vals):
                z = float(v[0]) if v is not None else np.nan
                if nodata is not None and np.isfinite(z) and abs(z - float(nodata)) < 0.5:
                    continue
                if z <= -9000:
                    continue
                if np.isfinite(z) and -500 < z < 9000:
                    zs[i] = z
                    remaining.discard(i)
    if remaining:
        print(f"AVISO: {len(remaining)} puntos sin elevación HMA")
    return zs


def smooth(z, win=5):
    z = np.array(z, dtype=float)
    out = z.copy()
    k = win // 2
    for i in range(len(z)):
        a, b = max(0, i - k), min(len(z), i + k + 1)
        sl = z[a:b]
        sl = sl[np.isfinite(sl)]
        if len(sl):
            out[i] = float(np.median(sl))
    # forzar no creciente a gran escala: isotónica suave hacia aguas abajo
    # (el río baja; picos de ladera en DEM 30 m se recortan)
    for i in range(1, len(out)):
        if out[i] > out[i - 1] + 8:  # subida absurda >8 m en ~200 m
            out[i] = out[i - 1]
    return out


def resample_1km(pts, z):
    dist = [0.0]
    for a, b in zip(pts, pts[1:]):
        dist.append(dist[-1] + haversine_m(a[0], a[1], b[0], b[1]))
    dist = np.array(dist)
    total = dist[-1]
    nkm = int(math.floor(total / 1000.0))
    targets = np.arange(0, nkm + 1) * 1000.0
    if targets[-1] < total - 50:
        targets = np.append(targets, total)
    lats = np.interp(targets, dist, [p[0] for p in pts])
    lons = np.interp(targets, dist, [p[1] for p in pts])
    zs = np.interp(targets, dist, z)
    return targets, lats, lons, zs


def fmt_hora(dt):
    return dt.strftime("%H:%M")


def minutos(a, b):
    return (b - a).total_seconds() / 60.0


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    osm = fetch_overpass()
    adj = build_graph(osm)
    start_p, ds = nearest_node(adj, PLACES[0]["lat"], PLACES[0]["lon"])
    end_p, de = nearest_node(adj, PLACES[-1]["lat"], PLACES[-1]["lon"])
    print(f"Start snap {ds:.0f} m  End snap {de:.0f} m")
    path, length = dijkstra(adj, start_p, end_p)
    print(f"Camino {len(path)} nodos, {length/1000:.2f} km")
    dense = densify(path, 50.0)
    print(f"Densificado {len(dense)} pts")

    dem = download_dem()
    z_raw = sample_z(dem, dense)
    z_arr = np.array(z_raw, dtype=float)
    ok = np.isfinite(z_arr)
    if (~ok).any() and ok.any():
        idx = np.arange(len(z_arr))
        z_arr[~ok] = np.interp(idx[~ok], idx[ok], z_arr[ok])
        print(f"Huecos HMA interpolados: {int((~ok).sum())} / {len(z_arr)}")
    z = smooth(z_arr, 7)
    km, lats, lons, zs = resample_1km(dense, z)

    # tramos de 1 km
    segs = []
    for i in range(len(km) - 1):
        dx = float(km[i + 1] - km[i])
        dz = float(zs[i] - zs[i + 1])
        s = max(dz / dx, 1e-4)  # pendiente mínima 0.01 %
        segs.append(
            {
                "km_ini": round(km[i] / 1000.0, 3),
                "km_fin": round(km[i + 1] / 1000.0, 3),
                "dx_m": dx,
                "z_ini": round(float(zs[i]), 1),
                "z_fin": round(float(zs[i + 1]), 1),
                "dz_m": round(dz, 1),
                "S": s,
                "S_pct": round(s * 100, 3),
                "lat": float(lats[i]),
                "lon": float(lons[i]),
            }
        )

    # snap comunidades al km más cercano
    comm = []
    for pl in PLACES:
        best_i, bd = 0, 1e18
        for i, (la, lo) in enumerate(zip(lats, lons)):
            d = haversine_m(pl["lat"], pl["lon"], la, lo)
            if d < bd:
                best_i, bd = i, d
        comm.append(
            {
                **pl,
                "km": round(float(km[best_i]) / 1000.0, 2),
                "z": round(float(zs[best_i]), 1),
                "snap_m": round(bd, 0),
                "idx": best_i,
            }
        )
        print(f"{pl['nombre']}: km {km[best_i]/1000:.2f}  snap {bd:.0f} m  z={zs[best_i]:.0f}")

    sya = next(c for c in comm if c["id"] == "syabrubesi")
    bet = next(c for c in comm if c["id"] == "betrawati")
    i0, i1 = sya["idx"], bet["idx"]
    if i1 <= i0:
        raise RuntimeError("Syabrubesi no está aguas arriba de Betrawati en el perfil")

    # Calibrar R para que Syabrubesi→Betrawati = 30 min
    # dt = n * dx / (R^(2/3) * sqrt(S))
    suma = 0.0
    for seg in segs[i0:i1]:
        suma += seg["dx_m"] / math.sqrt(seg["S"])
    # 1800 = n * suma / R^(2/3)
    r23 = N_MANN * suma / 1800.0
    R = r23 ** 1.5
    print(f"R calibrado n={N_MANN}: {R:.2f} m  (Syabrubesi->Betrawati = 30 min)")

    # velocidades y tiempos acumulados desde km 0
    t_s = 0.0
    for seg in segs:
        v = (1.0 / N_MANN) * (R ** (2.0 / 3.0)) * math.sqrt(seg["S"])
        dt = seg["dx_m"] / v
        seg["V_mps"] = round(v, 2)
        seg["V_kmh"] = round(v * 3.6, 1)
        seg["dt_s"] = round(dt, 1)
        seg["t_ini_s"] = t_s
        t_s += dt
        seg["t_fin_s"] = t_s

    # tiempo en cada estación km (inicio de tramo)
    t_at = [0.0]
    for seg in segs:
        t_at.append(seg["t_fin_s"])
    t_at = np.array(t_at)

    # anclar: Syabrubesi = 08:50
    t_sya = t_at[sya["idx"]]
    t_bet_model = t_at[bet["idx"]]
    print(
        f"Modelo Syabrubesi->Betrawati: {(t_bet_model - t_sya)/60:.2f} min "
        f"(objetivo 30)"
    )

    def hora_desde_sya(t_sec_from_origin):
        return T_SYA + timedelta(seconds=t_sec_from_origin - t_sya)

    # curva cada km
    curva = []
    for i, (k, la, lo, zz) in enumerate(zip(km, lats, lons, zs)):
        h = hora_desde_sya(t_at[i])
        v = segs[i]["V_mps"] if i < len(segs) else segs[-1]["V_mps"]
        lead_sms = minutos(T_SMS, h)  # >0 si llega DESPUÉS del SMS
        lead_auto = minutos(T_AUTO, h)
        actual = max(0.0, lead_sms)
        potential = max(0.0, lead_auto)
        perdido = potential - actual
        curva.append(
            {
                "km": round(float(k) / 1000.0, 2),
                "lat": round(float(la), 6),
                "lon": round(float(lo), 6),
                "z_m": round(float(zz), 1),
                "S_pct": segs[i]["S_pct"] if i < len(segs) else None,
                "V_mps": v,
                "V_kmh": round(v * 3.6, 1),
                "hora": fmt_hora(h),
                "hora_iso": h.isoformat(),
                "min_desde_sismo": round(minutos(T_SISMO, h), 1),
                "aviso_sms_min": round(lead_sms, 1),
                "aviso_auto_min": round(lead_auto, 1),
                "aviso_real_min": round(actual, 1),
                "aviso_potencial_min": round(potential, 1),
                "minutos_perdidos": round(perdido, 1),
            }
        )

    # comunidades
    for c in comm:
        h = hora_desde_sya(t_at[c["idx"]])
        lead_sms = minutos(T_SMS, h)
        lead_auto = minutos(T_AUTO, h)
        actual = max(0.0, lead_sms)
        potential = max(0.0, lead_auto)
        c["hora_llegada"] = fmt_hora(h)
        c["min_desde_sismo"] = round(minutos(T_SISMO, h), 1)
        c["aviso_sms_min"] = round(lead_sms, 1)
        c["aviso_auto_08_38_min"] = round(lead_auto, 1)
        c["aviso_real_min"] = round(actual, 1)
        c["aviso_potencial_min"] = round(potential, 1)
        c["minutos_perdidos"] = round(potential - actual, 1)
        c["V_local_mps"] = segs[c["idx"]]["V_mps"] if c["idx"] < len(segs) else segs[-1]["V_mps"]

    # frente a horas clave
    horas_clave = [
        ("08:37", T_SISMO),
        ("08:38", T_AUTO),
        ("08:40", datetime(2026, 8, 26, 8, 40)),
        ("08:50", T_SYA),
        ("09:00", datetime(2026, 8, 26, 9, 0)),
        ("09:15", datetime(2026, 8, 26, 9, 15)),
        ("09:16", T_SMS),
        ("09:20", T_BET),
        ("09:30", datetime(2026, 8, 26, 9, 30)),
        ("09:40", datetime(2026, 8, 26, 9, 40)),
        ("10:00", datetime(2026, 8, 26, 10, 0)),
    ]
    frente = []
    for label, t in horas_clave:
        # km donde hora_desde_sya(t_at) == t  → t_at = t_sya + (t-T_SYA)
        target = t_sya + (t - T_SYA).total_seconds()
        if target < t_at[0] - 1:
            km_f, estado = None, "antes de Rasuwagadhi (aún en Tíbet / Lhende)"
        elif target > t_at[-1] + 1:
            km_f, estado = round(float(km[-1]) / 1000, 2), "ya pasó Devighat HEP"
        else:
            km_f = round(float(np.interp(target, t_at, km) / 1000.0), 2)
            estado = f"km {km_f}"
        frente.append({"hora": label, "km": km_f, "donde": estado})

    dist_sb = (km[bet["idx"]] - km[sya["idx"]]) / 1000.0
    v_obs = (km[bet["idx"]] - km[sya["idx"]]) / 1800.0
    z0, z1 = float(zs[0]), float(zs[-1])

    summary = {
        "fuente_dem": "NASA HMA 8 m mosaic tile-675 (Shean 2017; elipsoide WGS84)",
        "cauce": "OpenStreetMap waterway=river, camino mínimo Rasuwagadhi→Devighat HEP",
        "longitud_km": round(float(km[-1]) / 1000.0, 2),
        "z_rasuwagadhi_m": round(z0, 1),
        "z_devighat_m": round(z1, 1),
        "desnivel_m": round(z0 - z1, 1),
        "pendiente_media_pct": round(100.0 * (z0 - z1) / float(km[-1]), 3),
        "n_manning": N_MANN,
        "R_calibrado_m": round(R, 2),
        "calibracion": (
            "R ajustado para que el tiempo modelo Syabrubesi→Betrawati sea 30 min "
            "(estación Syabrubesi deja de transmitir 08:50; Betrawati 09:20). "
            "Última lectura Syabrubesi 08:40 = 1.62 m (bajo umbral); el frente "
            "llegó entre 08:40 y 08:50."
        ),
        "v_obs_syabrubesi_betrawati_mps": round(v_obs, 2),
        "v_obs_kmh": round(v_obs * 3.6, 1),
        "dist_syabrubesi_betrawati_km": round(dist_sb, 2),
        "sms_dhm": "09:15–09:16 NPT, 679.295 mensajes (informe técnico DHM / Kathmandu Post 27 ago 2026)",
        "alerta_auto_hipotetica": "08:38 NPT (90 s tras señal sísmica 08:37)",
        "nota_devighat": (
            "Devighat HEP en Nuwakot (27.888°N, 85.134°E), NO Devghat (Chitwan) "
            "donde el pico fue a las 16:00 y el frente ~15:20."
        ),
        "comunidades": comm,
        "frente_por_hora": frente,
        "curva_1km": curva,
        "tramos": segs,
    }

    json_path = os.path.join(OUT_DIR, "resultado_manning.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # GeoJSON del eje
    line = LineString([(xy[1], xy[0]) for xy in zip(lons, lats)])
    gj = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "eje Bhote Koshi–Trishuli", "km": summary["longitud_km"]},
                "geometry": mapping(line),
            }
        ],
    }
    for c in comm:
        gj["features"].append(
            {
                "type": "Feature",
                "properties": {k: c[k] for k in c if k != "idx"},
                "geometry": {"type": "Point", "coordinates": [c["lon"], c["lat"]]},
            }
        )
    gj_path = os.path.join(OUT_DIR, "eje_comunidades.geojson")
    with open(gj_path, "w", encoding="utf-8") as f:
        json.dump(gj, f, ensure_ascii=False)

    csv_path = os.path.join(OUT_DIR, "curva_1km.csv")
    with open(csv_path, "w", encoding="utf-8") as f:
        cols = list(curva[0].keys())
        f.write(",".join(cols) + "\n")
        for row in curva:
            f.write(",".join(str(row[c]) for c in cols) + "\n")

    print("Escrito", json_path)
    print("Longitud", summary["longitud_km"], "km  desnivel", summary["desnivel_m"], "m")
    print("R", summary["R_calibrado_m"], "m")
    for c in comm:
        print(
            f"  {c['nombre']:28s} km {c['km']:5.1f}  {c['hora_llegada']}  "
            f"perdidos {c['minutos_perdidos']:.0f} min  "
            f"real {c['aviso_real_min']:.0f}  potencial {c['aviso_potencial_min']:.0f}"
        )


if __name__ == "__main__":
    main()
