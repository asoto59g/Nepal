# -*- coding: utf-8 -*-
import json
from pathlib import Path

import requests
from shapely import wkt
from shapely.geometry import mapping

here = Path(__file__).resolve().parent
gj = json.loads((here / "inundacion_bhote_koshi.geojson").read_text(encoding="utf-8"))
man = json.loads((here / "resultado_manning.json").read_text(encoding="utf-8"))
blob = json.dumps(gj, separators=(",", ":"), ensure_ascii=False)
curvas = json.loads((here / "curvas_10m_hma.geojson").read_text(encoding="utf-8"))
curvas_blob = json.dumps(curvas, separators=(",", ":"), ensure_ascii=False)
ems = json.loads((here / "emsr927_hasta_hoy.geojson").read_text(encoding="utf-8"))

have_aoi4 = any(
    (f.get("properties") or {}).get("aoi_n") == 4
    for f in ems.get("features", [])
)
if not have_aoi4:
    try:
        r = requests.get(
            "https://rapidmapping.emergency.copernicus.eu/backend/dashboard-api/public-activations/?code=EMSR927",
            timeout=60,
            headers={"User-Agent": "ABCGeomatica-HMA/1.0"},
        )
        r.raise_for_status()
        for aoi in r.json()["results"][0]["aois"]:
            if aoi.get("number") != 4:
                continue
            geom = mapping(wkt.loads(aoi["extent"]))
            ems.setdefault("features", []).append(
                {
                    "type": "Feature",
                    "properties": {
                        "clase": "emsr_aoi",
                        "aoi": "Bharatpur",
                        "aoi_n": 4,
                        "locality": "Bharatpur",
                        "emsr_id": "EMSR927",
                        "map_type": "GRA",
                        "estado": "en espera (W) — Legion 29 ago 04:01 UTC, entrega prevista 17:01 UTC",
                        "fuente": "Copernicus EMSR927 API",
                    },
                    "geometry": geom,
                }
            )
            print("AOI04 Bharatpur (espera) añadido al geojson embebido")
    except Exception as ex:
        print("AOI04 no se pudo añadir:", ex)

ems_blob = json.dumps(ems, separators=(",", ":"), ensure_ascii=False)
origen = json.loads((here / "origen_avalancha.geojson").read_text(encoding="utf-8"))
origen_blob = json.dumps(origen, separators=(",", ":"), ensure_ascii=False)
lago = json.loads((here / "lago_escombros.geojson").read_text(encoding="utf-8"))
lago_blob = json.dumps(lago, separators=(",", ":"), ensure_ascii=False)
desliz = json.loads((here / "deslizamientos_s1_norte.geojson").read_text(encoding="utf-8"))
desliz_blob = json.dumps(desliz, separators=(",", ":"), ensure_ascii=False)
n_s1 = int((desliz.get("properties") or {}).get("n") or 0)
km2_s1 = float((desliz.get("properties") or {}).get("area_km2") or 0)

a_n = a_r = 0.0
for f in gj.get("features", []):
    c = (f.get("properties") or {}).get("clase")
    if c == "nucleo_valle":
        a_n = (f["properties"] or {}).get("area_km2") or 0
    if c == "runup_ladera":
        a_r = (f["properties"] or {}).get("area_km2") or 0
km_tot = man.get("longitud_km", 0)
ha_ems = (ems.get("properties") or {}).get("area_deslizamiento_ha", 829)
km_ras = man.get("km_rasuwagadhi")
if km_ras is None:
    km_ras = next((c["km"] for c in man.get("comunidades") or [] if c.get("id") == "rasuwagadhi"), 0)
ras = next((c for c in man.get("comunidades") or [] if c.get("id") == "rasuwagadhi"), {})

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
  <p>km 0 = cicatriz Langtang (S2). Rasuwagadhi ~km PANEL_KM_RASU, PANEL_HORA_RASU NPT.
  Eje PANEL_KM km hasta Bharatpur. Mancha naranja/roja: ocupacion HAND del valle
  (garganta 9–12 m), no el tirante de pico 80–96 m. HAND solo Rasuwagadhi→Bharatpur
  (HMA 8 m + COP30 al oeste).</p>
  <p>Magenta: Copernicus <a href="https://mapping.emergency.copernicus.eu/activations/EMSR927/">EMSR927</a>
  GRA al 29 ago 2026. Fotointerpretacion 27 ago: Syapru Besi 111 ha (WorldView-3),
  Timure 129 ha (Legion) y Bidur 589 ha (BlackSky / Satellogic). Bharatpur (AOI04) en espera (Legion 29 ago, entrega prevista ~17:01 UTC).</p>
  <div class="ems-imgs">
    <a href="media/emsr927_aoi01_syapru_besi.jpg"><img src="media/emsr927_aoi01_syapru_besi_thumb.jpg" alt="Mapa GRA EMSR927 Syapru Besi"/><span>AOI01 Syapru Besi</span></a>
    <a href="media/emsr927_aoi02_timure.jpg"><img src="media/emsr927_aoi02_timure_thumb.jpg" alt="Mapa GRA EMSR927 Timure"/><span>AOI02 Timure</span></a>
    <a href="media/emsr927_aoi03_bidur.jpg"><img src="media/emsr927_aoi03_bidur_thumb.jpg" alt="Mapa GRA EMSR927 Bidur"/><span>AOI03 Bidur</span></a>
  </div>
  <ul class="legend">
    <li><span class="sw" style="background:#7f1d1d"></span>Nucleo del valle HAND (PANEL_NUCLEO km²). Ocupacion 12→5 m, no pico. Capa apagable.</li>
    <li><span class="sw" style="background:#f97316"></span>Runup en ladera HAND (PANEL_RUNUP km²). Capa apagable.</li>
    <li><span class="sw" style="background:#7c3aed"></span>EMSR927 deslizamiento (PANEL_HA ha, 3 AOI publicadas)</li>
    <li><span class="sw" style="background:#b91c1c"></span>Edificio destruido / dañado (CEMS)</li>
    <li><span class="sw" style="background:#1d4ed8"></span>Eje del cauce</li>
    <li><span class="sw" style="background:#111"></span>Comunidades y hora de llegada</li>
    <li><span class="sw" style="background:#b91c1c"></span>Fin del eje (Bharatpur / Narayani)</li>
    <li><span class="sw" style="background:#92400e;height:2px;width:18px"></span>Curvas de nivel (10 m garganta, 20 m valle bajo). Capa apagable.</li>
    <li><span class="sw" style="background:#06b6d4"></span>Cicatriz S2 (hielo 24→27 ago) · 28.285°N 85.513°E</li>
    <li><span class="sw" style="background:#2563eb"></span>Lago S2 27 ago (SCL agua, 3.7 ha) · 28.293°N 85.511°E</li>
    <li><span class="sw" style="background:#1e3a8a"></span>Agua residual S1 RTC 28 ago (~2.3 ha, ya no las 20 ha)</li>
    <li><span class="sw" style="background:#ca8a04"></span>Deslizamientos S1 RTC 2021–2026, 50 km al N de Rasuwagadhi (PANEL_S1_N parches ≥0.5 km², PANEL_S1_KM2 km²). Capa apagable.</li>
  </ul>
  <p class="note">Devighat HEP (Nuwakot) no es Devghat (Chitwan). Reloj: colapso 08:37 → Rasuwagadhi 08:54 → Syabrubesi 09:09 → Betrawati 09:40 → Galchhi 11:02 → Devghat ~15:20 DHM. Caidas de estacion 08:50 / 09:20 son corte de radio, no el frente. n Manning 0.10 / 0.05 / 0.04. AOI04 Bharatpur es el recuadro azul discontinuo, sin poligonos GRA aun.
  EMSR927 clasifica el daño como mass movement / landslide. Corte: 29 ago 2026.
  El colapso de hielo/roca no está en el eje Rasuwagadhi–Trishuli: está ~13 km al este, flanco N de Langtang. Sentinel-2 (24 vs 27 ago) da el parche de 20 ha; Sentinel-1 (16 vs 28) confirma un cambio VV de −6 dB a 400 m. Nubes: 22 % el 24, 47 % el 27, 76 % el 29; no sustituyen a WV-3/Planet en el corredor.
  Lago de escombros: Satellogic 27 ago 20.25 ha en 28.294°N 85.511°E. S2 SCL ve 3.7 ha de agua nueva ese día. S1 RTC del 28 ago (12:21 UTC) ya no oscurece ese punto (−10 dB): el desagüe había empezado. Quedan ~2.3 ha oscuras 400–600 m al sur. El punto Keystone (28.312°N 85.554°E) está nublado en S2 y no es agua en S1.
  Tiempos y picos de garganta alineados a geo-pera/bhotekoshi-2026-reconstruction (metodos; no se copian vectores Planet/WV CC BY-NC).
  Deslizamientos S1: cambio RTC VV 23 ago 2021 vs 28 ago 2026 (orbita 85, ~5 años), semicirculo de 50 km al norte de Rasuwagadhi. Solo parches con |ΔVV| semilla ≥ 6.5 dB y mediana ≥ 5.5 dB (cambio grande), 0.5–20 km². No es EMSR927.</p>
</aside>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const DATA = PLACEHOLDER;
const CURVAS = CURVAS_PLACEHOLDER;
const EMS = EMS_PLACEHOLDER;
const ORIGEN = ORIGEN_PLACEHOLDER;
const LAGO = LAGO_PLACEHOLDER;
const DESLIZ = DESLIZ_PLACEHOLDER;
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
const origenPoly = L.geoJSON(ORIGEN, {
  filter(f){ return f.properties.clase === "cicatriz_s2"; },
  style(){ return {color:"#0e7490", weight:2, fillColor:"#06b6d4", fillOpacity:0.45}; },
  onEachFeature(f, layer){
    const p = f.properties;
    layer.bindPopup("<b>"+p.nombre+"</b><br>"+p.area_ha+" ha · Sentinel-2 SCL 24 vs 27 ago");
  }
}).addTo(map);
const origenPts = L.geoJSON(ORIGEN, {
  filter(f){ return f.geometry && f.geometry.type === "Point"; },
  pointToLayer(f, latlng){
    const c = f.properties.clase;
    const fill = c === "origen_usgs" ? "#eab308" : (c === "origen_s1" ? "#84cc16" : "#06b6d4");
    const r = c === "origen_s2" ? 9 : 7;
    return L.circleMarker(latlng, {radius:r, color:"#fff", weight:2, fillColor:fill, fillOpacity:1});
  },
  onEachFeature(f, layer){
    const p = f.properties;
    let extra = "";
    if (p.area_ha) extra += "<br>"+p.area_ha+" ha";
    if (p.mean_db != null) extra += "<br>ΔVV "+p.mean_db+" dB";
    if (p.dist_km_usgs != null) extra += "<br>"+p.dist_km_usgs+" km del USGS";
    layer.bindPopup("<b>"+p.nombre+"</b>"+extra);
  }
}).addTo(map);
const lagoPoly = L.geoJSON(LAGO, {
  filter(f){ return f.geometry && f.geometry.type !== "Point"; },
  style(f){
    const c = f.properties.clase;
    if (c === "lago_s2_scl") return {color:"#1d4ed8", weight:2, fillColor:"#2563eb", fillOpacity:0.55};
    return {color:"#1e3a8a", weight:1.5, fillColor:"#1e40af", fillOpacity:0.5};
  },
  onEachFeature(f, layer){
    const p = f.properties;
    const src = p.clase === "lago_s2_scl" ? "Sentinel-2 SCL 24→27 ago (agua nueva)" : "Sentinel-1 RTC VV 16 vs 28 ago (oscuro)";
    layer.bindPopup("<b>Agua "+(p.area_ha||"?")+" ha</b><br>"+src);
  }
}).addTo(map);
const lagoPts = L.geoJSON(LAGO, {
  filter(f){ return f.geometry && f.geometry.type === "Point"; },
  pointToLayer(f, latlng){
    return L.circleMarker(latlng, {radius:8, color:"#fff", weight:2, fillColor:"#3b82f6", fillOpacity:1});
  },
  onEachFeature(f, layer){
    layer.bindPopup("<b>"+f.properties.nombre+"</b>");
  }
}).addTo(map);
const deslizLayer = L.geoJSON(DESLIZ, {
  style(f){
    const c = f.properties.clase;
    if (c === "aoi_semicirculo") return {color:"#a16207", weight:2, dashArray:"6 4", fillOpacity:0};
    return {color:"#a16207", weight:1.2, fillColor:"#ca8a04", fillOpacity:0.40};
  },
  onEachFeature(f, layer){
    const p = f.properties;
    if (p.clase === "aoi_semicirculo") {
      layer.bindPopup("<b>"+p.nombre+"</b><br>radio "+p.radio_km+" km");
      return;
    }
    const sent = p.sentido || "";
    layer.bindPopup(
      "<b>Cambio S1 RTC "+(p.area_km2||"?")+" km²</b><br>ΔVV "+p.delta_vv_db+" dB ("+sent+")<br>"+
      (p.par||"2023 vs 2026")+" · órbita "+(p.orbita||85)+"<br>informativo; no es EMSR927"
    );
  }
}).addTo(map);
L.control.layers(
  {OSM: osm, Satelite: sat},
  {
    "Mancha HAND (naranja/roja)": handLayer,
    "Curvas 10 m (HMA)": curvasLayer,
    "EMSR927 deslizamientos": emsSlide,
    "EMSR927 edificios": emsBuild,
    "EMSR927 AOI (hasta hoy)": emsAoi,
    "Origen hielo/roca (S1/S2)": origenPoly,
    "Puntos origen USGS/S1/S2": origenPts,
    "Lago de escombros (S1/S2)": lagoPoly,
    "Puntos lago reportados": lagoPts,
    "Deslizamientos S1 2021–2026 (50 km N Rasuwagadhi)": deslizLayer
  }
).addTo(map);
L.control.scale({
  position: "bottomleft",
  metric: true,
  imperial: false,
  maxWidth: 140
}).addTo(map);
map.fitBounds(handLayer.getBounds().extend(gj.getBounds()).extend(origenPts.getBounds()).pad(0.08));
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
  .replace("PANEL_KM_RASU", f"{float(km_ras):.0f}")
  .replace("PANEL_HORA_RASU", str(ras.get("hora_llegada") or "08:54"))
  .replace("PANEL_KM", f"{km_tot:.1f}")
  .replace("PANEL_NUCLEO", f"{a_n:.1f}")
  .replace("PANEL_RUNUP", f"{a_r:.1f}")
  .replace("PANEL_HA", f"{float(ha_ems):.0f}")
  .replace("EMS_PLACEHOLDER", ems_blob)
  .replace("CURVAS_PLACEHOLDER", curvas_blob)
  .replace("ORIGEN_PLACEHOLDER", origen_blob)
  .replace("LAGO_PLACEHOLDER", lago_blob)
  .replace("DESLIZ_PLACEHOLDER", desliz_blob)
  .replace("PANEL_S1_N", str(n_s1))
  .replace("PANEL_S1_KM2", f"{km2_s1:.1f}")
  .replace("PLACEHOLDER", blob))
dest = here / "index.html"
dest.write_text(html, encoding="utf-8")
print("wrote", dest, dest.stat().st_size)
