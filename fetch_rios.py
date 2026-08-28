# -*- coding: utf-8 -*-
import json
import os
import requests

OUT = os.path.join(os.path.dirname(__file__), "rios_overpass.json")
Q = """
[out:json][timeout:120];
(
  way["waterway"="river"](27.86,85.10,28.32,85.42);
);
out geom;
"""
HEADERS = {"User-Agent": "ABCGeomatica-HMA/1.0 (flood-analysis Nepal 2026)"}
URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.osm.ch/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

last = None
for url in URLS:
    try:
        print("try", url)
        r = requests.post(url, data={"data": Q}, headers=HEADERS, timeout=120)
        print(" status", r.status_code, "bytes", len(r.content))
        r.raise_for_status()
        data = r.json()
        n = len(data.get("elements", []))
        print(" ways", n)
        if n:
            with open(OUT, "w", encoding="utf-8") as f:
                json.dump(data, f)
            print("wrote", OUT)
            break
    except Exception as e:
        last = e
        print(" fail", e)
else:
    raise SystemExit(last)
