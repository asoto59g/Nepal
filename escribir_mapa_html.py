# -*- coding: utf-8 -*-
import json
from pathlib import Path

here = Path(__file__).resolve().parent
gj = json.loads((here / "inundacion_bhote_koshi.geojson").read_text(encoding="utf-8"))
blob = json.dumps(gj, separators=(",", ":"), ensure_ascii=False)
curvas = json.loads((here / "curvas_10m_hma.geojson").read_text(encoding="utf-8"))
curvas_blob = json.dumps(curvas, separators=(",", ":"), ensure_ascii=False)
ems = json.loads((here / "emsr927_hasta_hoy.geojson").read_text(encoding="utf-8"))
ems_blob = json.dumps(ems, separators=(",", ":"), ensure_ascii=False)

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
  .note a{color:#1d4ed8}
  .leaflet-tooltip.lab{background:#fff;border:0;box-shadow:none;font-size:11px;font-weight:600}
  .site-nav{display:flex;gap:4px;margin:0 0 10px}
  .site-nav a{font-size:12px;font-weight:600;color:#52525b;text-decoration:none;padding:4px 8px;border:1px solid #e4e4e7}
  .site-nav a.is-on{background:#18181b;color:#fff;border-color:#18181b}
  .ems-imgs{display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px;margin:8px 0 4px}
  .ems-imgs img{width:100%;height:auto;border:1px solid #e4e4e7;display:block}
  .ems-imgs span{display:block;font-size:10px;color:#71717a;margin-top:2px}
  .panel-toggle{display:none;position:absolute;z-index:1100;top:12px;left:12px;
    background:#fff;border:1px solid #e4e4e7;padding:8px 12px;font-size:13px;
    font-weight:600;cursor:pointer;font-family:inherit;color:#18181b}
  .panel-close{display:none;float:right;margin:-4px -4px 6px 8px;border:0;background:transparent;
    font-size:22px;line-height:1;cursor:pointer;color:#52525b;padding:0 4px}
  .leaflet-bottom.leaflet-left{margin:0}
  .leaflet-control-scale{
    margin:2px 0 2px 4px !important;
    background:transparent;
    padding:0;
    border:0
  }
  .leaflet-control-scale-line{
    border:2px solid #18181b;
    border-top:none;
    line-height:1.05;
    font-size:10px;
    padding:0 5px 1px;
    margin:0;
    color:#18181b;
    background:rgba(255,255,255,.9)
  }
  .leaflet-control-attribution{margin:0 2px 2px 0 !important}
  @media (max-width:720px){
    .panel-toggle{display:block}
    .panel{display:none;top:52px;left:8px;right:8px;max-width:none;
      max-height:calc(100dvh - 64px);overflow:auto;box-sizing:border-box}
    .panel.is-open{display:block}
    .panel-close{display:block}
    .leaflet-tooltip.lab{display:none}
  }
</style>
</head>
<body>
<div id="map"></div>
<button type="button" class="panel-toggle" id="panelToggle" aria-expanded="false" aria-controls="leyenda">Leyenda</button>
<aside class="panel" id="leyenda">
  <button type="button" class="panel-close" id="panelClose" aria-label="Cerrar">×</button>
  <nav class="site-nav" aria-label="Paginas">
    <a class="is-on" href="index.html">Mapa</a>
    <a href="tiempos.html">Tiempos de alerta</a>
  </nav>
  <h1>Hasta donde llego la avalancha</h1>
  <p>Tramo analizado Rasuwagadhi → Devighat HEP (Nuwakot), 58.7 km.
  Mancha naranja/roja: estimacion HAND sobre NASA HMA 8 m (fondo de valle 9–12 m y runup en ladera).</p>
  <p>Magenta: Copernicus <a href="https://mapping.emergency.copernicus.eu/activations/EMSR927/">EMSR927</a>
  GRA al 29 ago 2026. Fotointerpretacion 27 ago: Syapru Besi 111 ha (WorldView-3),
  Timure 129 ha (Legion) y Bidur 589 ha (BlackSky / Satellogic). Bharatpur aun no publicado.</p>
  <div class="ems-imgs">
    <a href="media/emsr927_aoi01_syapru_besi.jpg"><img src="media/emsr927_aoi01_syapru_besi_thumb.jpg" alt="Mapa GRA EMSR927 Syapru Besi"/><span>AOI01 Syapru Besi</span></a>
    <a href="media/emsr927_aoi02_timure.jpg"><img src="media/emsr927_aoi02_timure_thumb.jpg" alt="Mapa GRA EMSR927 Timure"/><span>AOI02 Timure</span></a>
    <a href="media/emsr927_aoi03_bidur.jpg"><img src="media/emsr927_aoi03_bidur_thumb.jpg" alt="Mapa GRA EMSR927 Bidur"/><span>AOI03 Bidur</span></a>
  </div>
  <ul class="legend">
    <li><span class="sw" style="background:#7f1d1d"></span>Nucleo del valle HAND (3.2 km²). Capa apagable.</li>
    <li><span class="sw" style="background:#f97316"></span>Runup en ladera HAND (5.1 km²). Capa apagable.</li>
    <li><span class="sw" style="background:#7c3aed"></span>EMSR927 deslizamiento (829 ha, 3 AOI)</li>
    <li><span class="sw" style="background:#b91c1c"></span>Edificio destruido / dañado (CEMS)</li>
    <li><span class="sw" style="background:#1d4ed8"></span>Eje del cauce</li>
    <li><span class="sw" style="background:#111"></span>Comunidades y hora de llegada</li>
    <li><span class="sw" style="background:#b91c1c"></span>Limite del modelo (el frente siguio a Devghat)</li>
    <li><span class="sw" style="background:#92400e;height:2px;width:18px"></span>Curvas de nivel 10 m (indice cada 50 m). Capa apagable.</li>
  </ul>
  <p class="note">El DHM situa el frente en Devghat (Chitwan) ~15:20, fuera de este mapa.
  EMSR927 clasifica el daño como mass movement / landslide, no como mancha de llanura.
  Sentinel-1/2 no delinean el corredor (GRD sin RTC; optico nublado). Corte: 29 ago 2026.</p>
</aside>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const DATA = PLACEHOLDER;
const CURVAS = CURVAS_PLACEHOLDER;
const EMS = EMS_PLACEHOLDER;
const osm = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 18, attribution: "&copy; OpenStreetMap"
});
const sat = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", {
  maxZoom: 18, attribution: "Esri"
});
const map = L.map("map", {layers: [sat]});
function isHand(f) {
  const c = f.properties.clase;
  return c === "nucleo_valle" || c === "runup_ladera";
}
function style(f) {
  const c = f.properties.clase;
  if (c === "nucleo_valle") return {color:"#7f1d1d", weight:1, fillColor:"#991b1b", fillOpacity:0.45};
  if (c === "runup_ladera") return {color:"#c2410c", weight:0.6, fillColor:"#f97316", fillOpacity:0.28};
  if (c === "eje") return {color:"#1d4ed8", weight:3, opacity:0.95};
  return {};
}
const handLayer = L.geoJSON(DATA, {
  filter: isHand,
  style,
  onEachFeature(f, layer) {
    const p = f.properties;
    if (p.area_km2) layer.bindPopup(p.clase+" · "+p.area_km2+" km²");
  }
}).addTo(map);
const gj = L.geoJSON(DATA, {
  filter(f) { return !isHand(f); },
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
const emsSlide = L.geoJSON(EMS, {
  filter(f){ return f.properties.clase === "emsr_deslizamiento"; },
  style(){ return {color:"#5b21b6", weight:1.2, fillColor:"#7c3aed", fillOpacity:0.45}; },
  onEachFeature(f, layer){
    const p = f.properties;
    layer.bindPopup("<b>EMSR927 "+p.aoi+"</b><br>"+p.obj_desc+" · "+p.area_ha+" ha<br>"+p.sensor+"<br>fotointerpretacion Copernicus GRA");
  }
}).addTo(map);
const emsBuild = L.geoJSON(EMS, {
  renderer: L.canvas({padding: 0.5}),
  filter(f){ return f.properties.clase === "emsr_edificio"; },
  pointToLayer(f, latlng){
    const d = f.properties.damage_gra;
    const fill = d === "Destroyed" ? "#b91c1c" : (d === "Damaged" ? "#ea580c" : "#ca8a04");
    return L.circleMarker(latlng, {radius:3.5, color:"#fff", weight:0.6, fillColor:fill, fillOpacity:0.95});
  },
  onEachFeature(f, layer){
    const p = f.properties;
    layer.bindPopup(p.damage_gra+" · "+(p.simplified||"edificio")+"<br>EMSR927 "+p.aoi);
  }
}).addTo(map);
const emsAoi = L.geoJSON(EMS, {
  filter(f){ return f.properties.clase === "emsr_aoi"; },
  style(){ return {color:"#2563eb", weight:2, dashArray:"6 4", fillOpacity:0}; },
  onEachFeature(f, layer){
    const p = f.properties;
    layer.bindPopup("<b>AOI0"+p.aoi_n+" "+p.locality+"</b><br>EMSR927 "+p.map_type+"<br>"+p.estado);
  }
});
L.control.layers(
  {OSM: osm, Satelite: sat},
  {
    "Mancha HAND (naranja/roja)": handLayer,
    "Curvas 10 m (HMA)": curvasLayer,
    "EMSR927 deslizamientos": emsSlide,
    "EMSR927 edificios": emsBuild,
    "EMSR927 AOI (hasta hoy)": emsAoi
  }
).addTo(map);
L.control.scale({
  position: "bottomleft",
  metric: true,
  imperial: false,
  maxWidth: 140
}).addTo(map);
map.fitBounds(handLayer.getBounds().extend(gj.getBounds()).pad(0.08));
(function(){
  const panel = document.getElementById("leyenda");
  const openBtn = document.getElementById("panelToggle");
  const closeBtn = document.getElementById("panelClose");
  function setOpen(open){
    panel.classList.toggle("is-open", open);
    openBtn.setAttribute("aria-expanded", open ? "true" : "false");
  }
  openBtn.addEventListener("click", function(){ setOpen(true); });
  closeBtn.addEventListener("click", function(){ setOpen(false); });
})();
</script>
</body>
</html>
"""
html = (html
  .replace("EMS_PLACEHOLDER", ems_blob)
  .replace("CURVAS_PLACEHOLDER", curvas_blob)
  .replace("PLACEHOLDER", blob))
dest = here / "index.html"
dest.write_text(html, encoding="utf-8")
print("wrote", dest, dest.stat().st_size)
