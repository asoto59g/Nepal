# Nepal — Bhote Koshi, 26 agosto 2026

Análisis del pulso de detritos Rasuwagadhi → Devighat HEP (Nuwakot) tras la avalancha de hielo y roca del 26 de agosto de 2026. (Analisis 28/08/26)

Sitio: https://asoto59g.github.io/Nepal/

Las dos piezas para presentar son HTML estático. No hay servidor ni base de datos.

| Página | Archivo | Qué muestra |
| --- | --- | --- |
| Inicio | [index.html](index.html) | Mapa de inundación estimada y curvas de nivel |
| Segunda | [tiempos.html](tiempos.html) | Curva x(t), Manning 1 km y minutos de alerta perdidos |

En cada página hay un enlace a la otra (Mapa / Tiempos de alerta).


---

## index.html — mapa de inundación

Fuente de la página: este HTML (Leaflet 1.9, datos embebidos). No llama a una API propia.

**Qué se ve**

- Núcleo de valle (~3.2 km²) y runup en ladera (~5.1 km²) entre Rasuwagadhi y Devighat HEP (Nuwakot), 58.7 km de cauce.
- Eje del río, comunidades con hora de llegada (NPT) y minutos de alerta perdidos.
- Límite del modelo en Devighat HEP: el frente siguió hacia Galchhi, Malekhu, Muglin y **Devghat (Chitwan) ~15:20**. No confundir Devighat HEP (Nuwakot) con Devghat.
- Curvas de nivel cada 10 m (índice cada 50 m), capa encendible y apagable en el control de capas (arriba a la derecha). Clic en una curva muestra la cota.

**Cómo se construyó**

No hay vector público de Copernicus EMSR927 al momento del análisis. La mancha es un HAND aproximado sobre el DEM NASA HMA 8 m (`HMA_DEM8m_MOS_20170716_tile-675`, Shean 2017, cotas elipsoidales WGS84):

| Tramo | Núcleo (H / ancho) | Runup (H / ancho) |
| --- | --- | --- |
| Garganta km 0–20 | 12 m / 280 m | 40 m / 450 m |
| Medio km 20–40 | 10 m / 450 m | 30 m / 700 m |
| Bajo | 9 m / 700 m | 22 m / 1100 m |

Curvas: contornos cada 10 m del mismo DEM, recortados a ~1.5 km del cauce.

**Scripts que regeneran esta página**

1. `generar_mapa_inundacion.py` → `inundacion_bhote_koshi.geojson`
2. `generar_curvas_10m.py` → `curvas_10m_hma.geojson`
3. `escribir_mapa_html.py` → `index.html`

El GeoTIFF HMA no va en el repositorio (~348 MB, Earthdata). Hace falta en local para volver a generar curvas o la mancha.

---

## tiempos.html — minutos de alerta perdidos

Fuente de la página: este HTML (tablas y SVG; sin Leaflet). Cifras tomadas de `resultado_manning.json` / `curva_1km.csv`.

**Reloj (NPT)**

- 08:37 sismo / avalancha (USGS).
- 08:38 alerta automática hipotética (90 s después).
- 08:50 Syabrubesi deja de transmitir (ancla del modelo).
- 09:16 SMS masivo DHM.
- 09:20 Betrawati deja de transmitir (segunda ancla).

**Manning**

`V = (1/n) · R^(2/3) · S^(1/2)`, con `n = 0.040` y `R = 10.16` m, calibrado para que Syabrubesi → Betrawati = 30 min (velocidad media observada 16.7 m/s). Pendiente `S` cada 1 km sobre el perfil HMA + eje OSM. Longitud 58.68 km, desnivel 1327 m, pendiente media 2.26 %.

A las 09:16 el frente está en el km 41.6 (~3.5 km aguas arriba de Betrawati). Aguas abajo de ~km 42 los minutos perdidos son constantes: **38 min** (09:16 − 08:38).

| Lugar | km | Llegada | SMS 09:16 | Auto 08:38 | Perdidos |
| --- | --- | --- | --- | --- | --- |
| Rasuwagadhi | 0 | 08:36 | 0 | 0 | 0 |
| Timure | 4 | 08:39 | 0 | 2 | 2 |
| Syabrubesi | 15 | 08:50 | 0 | 12 | 12 |
| Mailung | 33 | 09:08 | 0 | 30 | 30 |
| Betrawati | 45 | 09:20 | 4 | 42 | **38** |
| Trishuli HEP | 54 | 09:32 | 17 | 55 | **38** |
| Devighat HEP | 58.7 | 09:40 | 25 | 63 | **38** |

Rasuwagadhi 08:36 queda ~1 min antes del sismo 08:37: el tramo alto es muy pendiente y el reloj está anclado en Syabrubesi 08:50. Manning de agua clara es de primer orden; el evento fue un flujo de detritos.

**Script que regenera las cifras:** `calcular_manning.py` (cauce: `fetch_rios.py` / `rios_overpass.json`).

---


