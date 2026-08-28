# -*- coding: utf-8 -*-
"""Compact Copernicus EMSR927 GRA (AOI01+AOI02, 28 ago 2026) and export map JPEGs."""
from __future__ import annotations

import io
import json
from collections import Counter
from pathlib import Path

import fitz
from PIL import Image
from shapely.geometry import mapping, shape

HERE = Path(__file__).resolve().parent
MEDIA = HERE / "media"
SIMPLIFY_DEG = 0.000015  # ~1.5 m
COORD_DEC = 6
DAMAGE_KEEP = {"Destroyed", "Damaged", "Possibly damaged"}


def round_coords(obj, n=COORD_DEC):
    if isinstance(obj, (float, int)):
        return round(float(obj), n)
    if isinstance(obj, list):
        return [round_coords(x, n) for x in obj]
    return obj


def slim_geom(geom, simplify=False):
    if not geom:
        return geom
    g = shape(geom)
    if simplify and not g.is_empty:
        g = g.simplify(SIMPLIFY_DEG, preserve_topology=True)
    return round_coords(mapping(g))


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def feat(clase, props, geom, simplify=False):
    return {
        "type": "Feature",
        "properties": {"clase": clase, **props},
        "geometry": slim_geom(geom, simplify=simplify),
    }


def pdf_to_jpeg(pdf: Path, dest: Path, max_w: int, quality: int):
    doc = fitz.open(pdf)
    page = doc[0]
    zoom = min(2.0, max(1.0, max_w / float(page.rect.width)))
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
    img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
    if img.width > max_w:
        h = int(img.height * max_w / img.width)
        img = img.resize((max_w, h), Image.Resampling.LANCZOS)
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, "JPEG", quality=quality, optimize=True)
    print("jpeg", dest.name, dest.stat().st_size // 1024, "KB", img.size)


def main():
    feats = []
    sources = [
        {
            "aoi_n": 1,
            "aoi": "Syapru Besi",
            "event": HERE / "emsr927_aoi01" / "EMSR927_AOI01_GRA_PRODUCT_observedEventA_v1.json",
            "aoi_path": HERE / "emsr927_aoi01" / "EMSR927_AOI01_GRA_PRODUCT_areaOfInterestA_v1.json",
            "built": HERE / "emsr927_aoi01" / "EMSR927_AOI01_GRA_PRODUCT_builtUpP_v1.json",
            "pdf": HERE / "emsr927_aoi01" / "Maps" / "EMSR927_AOI01_GRA_PRODUCT_9000_map_v1.pdf",
            "jpg": MEDIA / "emsr927_aoi01_syapru_besi.jpg",
            "thumb": MEDIA / "emsr927_aoi01_syapru_besi_thumb.jpg",
            "sensor": "WorldView-3 27 ago 2026 05:05 UTC",
        },
        {
            "aoi_n": 2,
            "aoi": "Timure",
            "event": HERE / "emsr927_aoi02" / "EMSR927_AOI02_GRA_PRODUCT_observedEventA_v2.json",
            "aoi_path": HERE / "emsr927_aoi02" / "EMSR927_AOI02_GRA_PRODUCT_areaOfInterestA_v2.json",
            "built": HERE / "emsr927_aoi02" / "EMSR927_AOI02_GRA_PRODUCT_builtUpP_v2.json",
            "pdf": HERE / "emsr927_aoi02" / "Maps" / "EMSR927_AOI02_GRA_PRODUCT_8000_map_v2.pdf",
            "jpg": MEDIA / "emsr927_aoi02_timure.jpg",
            "thumb": MEDIA / "emsr927_aoi02_timure_thumb.jpg",
            "sensor": "Legion 27 ago 2026 05:05 UTC",
        },
    ]

    ha_tot = 0.0
    buildings = Counter()
    for src in sources:
        ev = load_json(src["event"])
        for f in ev.get("features", []):
            p = f.get("properties") or {}
            ha = float(p.get("area") or 0)
            ha_tot += ha
            feats.append(feat(
                "emsr_deslizamiento",
                {
                    "aoi": src["aoi"],
                    "aoi_n": src["aoi_n"],
                    "obj_desc": p.get("obj_desc"),
                    "event_type": p.get("event_type"),
                    "area_ha": round(ha, 2),
                    "det_method": p.get("det_method"),
                    "sensor": src["sensor"],
                    "fuente": "Copernicus EMSR927 GRA",
                },
                f["geometry"],
                simplify=True,
            ))
            print(src["aoi"], p.get("obj_desc"), "ha", round(ha, 2))

        aoi = load_json(src["aoi_path"])
        for f in aoi.get("features", []):
            p = f.get("properties") or {}
            feats.append(feat(
                "emsr_aoi",
                {
                    "aoi": src["aoi"],
                    "aoi_n": src["aoi_n"],
                    "locality": p.get("locality") or src["aoi"],
                    "emsr_id": p.get("emsr_id", "EMSR927"),
                    "map_type": p.get("map_type"),
                    "estado": "publicado 28 ago 2026",
                    "fuente": "Copernicus EMSR927 GRA",
                },
                f["geometry"],
            ))

        bu = load_json(src["built"])
        for f in bu.get("features", []):
            p = f.get("properties") or {}
            dmg = p.get("damage_gra")
            if dmg not in DAMAGE_KEEP:
                continue
            buildings[dmg] += 1
            feats.append(feat(
                "emsr_edificio",
                {
                    "aoi": src["aoi"],
                    "aoi_n": src["aoi_n"],
                    "damage_gra": dmg,
                    "simplified": p.get("simplified"),
                    "fuente": "Copernicus EMSR927 GRA",
                },
                f["geometry"],
            ))

        pdf_to_jpeg(src["pdf"], src["jpg"], max_w=1400, quality=82)
        pdf_to_jpeg(src["pdf"], src["thumb"], max_w=420, quality=72)

    out = {
        "type": "FeatureCollection",
        "name": "emsr927_hasta_hoy",
        "properties": {
            "corte": "2026-08-28",
            "activacion": "EMSR927",
            "publicado": ["AOI01 Syapru Besi GRA v1", "AOI02 Timure GRA v2"],
            "pendiente": ["AOI03 Bidur (en curso)", "AOI04 Bharatpur (en espera)"],
            "area_deslizamiento_ha": round(ha_tot, 2),
            "edificios": dict(buildings),
            "url": "https://mapping.emergency.copernicus.eu/activations/EMSR927/",
        },
        "features": feats,
    }
    dest = HERE / "emsr927_hasta_hoy.geojson"
    dest.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("geojson", dest.name, dest.stat().st_size // 1024, "KB", "n", len(feats), "ha", round(ha_tot, 2), dict(buildings))


if __name__ == "__main__":
    main()
