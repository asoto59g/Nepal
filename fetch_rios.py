# -*- coding: utf-8 -*-
"""Cauce OSM: Himalaya alto + Trishuli medio + Narayani (Bharatpur)."""
import json
import os
import requests

OUT = os.path.join(os.path.dirname(__file__), "rios_overpass.json")
BBOXES = [
    (27.86, 85.10, 28.32, 85.42),
    (27.64, 84.38, 27.95, 85.16),
]
HEADERS = {"User-Agent": "ABCGeomatica-HMA/1.0 (flood-analysis Nepal 2026)"}
URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.osm.ch/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]


def query_for(s, w, n, e):
    return f"""
[out:json][timeout:180];
(
    way["waterway"="river"]({s},{w},{n},{e});
);
out geom;
"""


by_id = {}
last = None
for bbox in BBOXES:
    s, w, n, e = bbox
    Q = query_for(s, w, n, e)
    got = None
    for url in URLS:
        try:
            print("try", url, "bbox", bbox)
            r = requests.post(url, data={"data": Q}, headers=HEADERS, timeout=180)
            print(" status", r.status_code, "bytes", len(r.content))
            r.raise_for_status()
            data = r.json()
            nways = len(data.get("elements", []))
            print(" ways", nways)
            if nways:
                got = data
                break
        except Exception as ex:
            last = ex
            print(" fail", ex)
    if not got:
        raise SystemExit(f"Overpass failed {bbox}: {last}")
    for el in got.get("elements", []):
        eid = el.get("id")
        if eid is not None:
            by_id[eid] = el

out = {"elements": list(by_id.values())}
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f)
print("wrote", OUT, "ways", len(out["elements"]))
