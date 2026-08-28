# -*- coding: utf-8 -*-
"""Copia el mapa a index.html (con navegacion) y los tiempos a tiempos.html."""
from pathlib import Path

here = Path(__file__).resolve().parent

times_src = here / "manning_alerta_dhm.html"
times_dst = here / "tiempos.html"
times_dst.write_bytes(times_src.read_bytes())
print("tiempos.html", times_dst.stat().st_size)

css = (
    "  .site-nav{display:flex;gap:4px;margin:0 0 10px}\n"
    "  .site-nav a{font-size:12px;font-weight:600;color:#52525b;"
    "text-decoration:none;padding:4px 8px;border:1px solid #e4e4e7}\n"
    "  .site-nav a.is-on{background:#18181b;color:#fff;border-color:#18181b}\n"
)
nav = (
    '<aside class="panel">\n'
    '  <nav class="site-nav" aria-label="Paginas">\n'
    '    <a class="is-on" href="index.html">Mapa</a>\n'
    '    <a href="tiempos.html">Tiempos de alerta</a>\n'
    "  </nav>\n"
    "  <h1>"
)
mapa = here / "mapa_inundacion_bhote_koshi.html"
text = mapa.read_text(encoding="utf-8")
if "site-nav" not in text:
    text = text.replace(
        "  .leaflet-tooltip.lab{",
        css + "  .leaflet-tooltip.lab{",
    )
    text = text.replace('<aside class="panel">\n  <h1>', nav)
idx = here / "index.html"
idx.write_text(text, encoding="utf-8")
print("index.html", idx.stat().st_size)
