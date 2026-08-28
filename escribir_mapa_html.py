# -*- coding: utf-8 -*-
import json
from pathlib import Path

here = Path(__file__).resolve().parent
gj = json.loads((here / "inundacion_bhote_koshi.geojson").read_text(encoding="utf-8"))
blob = json.dumps(gj, separators=(",", ":"), ensure_ascii=False)
curvas = json.loads((here / "curvas_10m_hma.geojson").read_text(encoding="utf-8"))
curvas_blob = json.dumps(curvas, separators=(",", ":"), ensure_ascii=False)

html = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Inundacion por avalancha — Bhote Koshi 26 ago 2026</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<style>
  html,body{margin:0;height:100%;font-family:Segoe UI,system-ui,sans-serif}
  #map{position:absolute;inset:0}
  .panel{position:absolute;z-index:1000;top:12px;left:12px;max-width:360px;
    background:#fff;border:1px solid #e4e4e7;padding:14px 16px;font-size:13px;
    line-height:1.4;color:#18181b}
  .panel h1{font-size:16px;margin:0 0 6px}
  .panel p{margin:0 0 8px;color:#52525b}
  .sw{display:inline-block;width:12px;height:12px;margin-right:6px;vertical-align:-1px}
  .legend{margin:8px 0 0;padding:0;list-style:none}
  .legend li{margin:4px 0}
  .note{font-size:11px;color:#71717a;margin-top:8px}
  .leaflet-tooltip.lab{background:#fff;border:0;box-shadow:none;font-size:11px;font-weight:600}
  .site-nav{display:flex;gap:4px;margin:0 0 10px}
  .site-nav a{font-size:12px;font-weight:600;color:#52525b;text-decoration:none;padding:4px 8px;border:1px solid #e4e4e7}
  .site-nav a.is-on{background:#18181b;color:#fff;border-color:#18181b}
</style>
</head>
<body>
<div id="map"></div>
<aside class="panel">
  <nav class="site-nav" aria-label="Paginas">
    <a class="is-on" href="index.html">Mapa</a>
    <a href="tiempos.html">Tiempos de alerta</a>
  </nav>
  <h1>Hasta donde llego la avalancha</h1>
  <p>Tramo analizado Rasuwagadhi → Devighat HEP (Nuwakot), 58.7 km.
  Mancha estimada con NASA HMA 8 m: fondo de valle (9–12 m sobre el cauce)
  y runup en ladera. No es delineacion satelital Copernicus EMSR927.</p>
  <ul class="legend">
    <li><span class="sw" style="background:#7f1d1d"></span>Nucleo del valle (3.2 km²)</li>
    <li><span class="sw" style="background:#f97316"></span>Runup en ladera (5.1 km²)</li>
    <li><span class="sw" style="background:#1d4ed8"></span>Eje del cauce</li>
    <li><span class="sw" style="background:#111"></span>Comunidades y hora de llegada</li>
    <li><span class="sw" style="background:#b91c1c"></span>Limite del modelo (el frente siguio a Devghat)</li>
    <li><span class="sw" style="background:#92400e;height:2px;width:18px"></span>Curvas de nivel 10 m (indice cada 50 m). Capa apagable.</li>
  </ul>
  <p class="note">El DHM situa el frente en Devghat (Chitwan) ~15:20, fuera de este mapa.
  Copernicus reporto ~7 m en estaciones; en laderas el runup puede ser mayor.</p>
</aside>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const DATA = PLACEHOLDER;
const CURVAS = CURVAS_PLACEHOLDER;
const osm = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 18, attribution: "&copy; OpenStreetMap"
});
const sat = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", {
  maxZoom: 18, attribution: "Esri"
});
const map = L.map("map", {layers: [sat]});
function style(f) {
  const c = f.properties.clase;
  if (c === "nucleo_valle") return {color:"#7f1d1d", weight:1, fillColor:"#991b1b", fillOpacity:0.45};
  if (c === "runup_ladera") return {color:"#c2410c", weight:0.6, fillColor:"#f97316", fillOpacity:0.28};
  if (c === "eje") return {color:"#1d4ed8", weight:3, opacity:0.95};
  return {};
}
const gj = L.geoJSON(DATA, {
  style,
  pointToLayer(f, latlng) {
    const c = f.properties.clase;
    if (c === "limite_analizado") {
      return L.circleMarker(latlng, {radius:9, color:"#fff", weight:2, fillColor:"#b91c1c", fillOpacity:1});
    }
    return L.circleMarker(latlng, {radius:6, color:"#fff", weight:1.5, fillColor:"#111", fillOpacity:1});
  },
  onEachFeature(f, layer) {
    const p = f.properties;
    if (p.clase === "comunidad") {
      layer.bindPopup("<b>"+p.nombre+"</b><br>km "+p.km+" · llegada "+p.hora+" NPT<br>alerta perdida: "+p.perdidos+" min");
      layer.bindTooltip(p.nombre+" "+p.hora, {permanent:true, direction:"right", className:"lab", opacity:0.95});
    } else if (p.clase === "limite_analizado") {
      layer.bindPopup("<b>"+p.nombre+"</b><br>"+p.nota);
    } else if (p.area_km2) {
      layer.bindPopup(p.clase+" · "+p.area_km2+" km²");
    }
  }
}).addTo(map);
const curvasLayer = L.geoJSON(CURVAS, {
  renderer: L.canvas({padding: 0.5}),
  style(f) {
    const idx = f.properties.indice;
    return {
      color: idx ? "#78350f" : "#a16207",
      weight: idx ? 1.6 : 0.7,
      opacity: idx ? 0.85 : 0.55
    };
  },
  onEachFeature(f, layer) {
    const e = f.properties.elev_m;
    layer.bindPopup("Curva "+e+" m"+(f.properties.indice ? " (indice 50 m)" : ""));
  }
}).addTo(map);
L.control.layers(
  {OSM: osm, Satelite: sat},
  {"Curvas 10 m (HMA)": curvasLayer}
).addTo(map);
map.fitBounds(gj.getBounds().pad(0.08));
</script>
</body>
</html>
"""
html = html.replace("CURVAS_PLACEHOLDER", curvas_blob).replace("PLACEHOLDER", blob)
dest = here / "index.html"
dest.write_text(html, encoding="utf-8")
print("wrote", dest, dest.stat().st_size)
