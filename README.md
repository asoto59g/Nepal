# Nepal — Bhote Koshi, 26 agosto 2026

<img width="1024" height="512" alt="preview" src="https://github.com/user-attachments/assets/215d272c-fcc6-41a2-962a-456144608a05" />
Análisis del pulso de detritos Rasuwagadhi → Devighat HEP (Nuwakot) tras la avalancha de hielo y roca del 26 de agosto de 2026. (Analisis 28/08/26)

Sitio: https://asoto59g.github.io/Nepal/

Las dos piezas para presentar son HTML estático. No hay servidor ni base de datos.

| Página | Archivo | Qué muestra |
| --- | --- | --- |
| Inicio | [index.html](index.html) | Mapa: mancha HAND, curvas 10 m, polígonos e imágenes EMSR927 al 28 ago 2026 |
| Segunda | [tiempos.html](tiempos.html) | Curva x(t), Manning 1 km y minutos de alerta perdidos |

En cada página hay un enlace a la otra (Mapa / Tiempos de alerta).


---

## index.html — mapa de inundación

Fuente de la página: este HTML (Leaflet 1.9, datos embebidos). No llama a una API propia.

**Qué se ve**

- Núcleo de valle (~3.2 km²) y runup en ladera (~5.1 km²) entre Rasuwagadhi y Devighat HEP (Nuwakot), 58.7 km de cauce. **Estimación HAND**, no es la delineación Copernicus.
- Polígonos y edificios de [Copernicus EMSR927](https://mapping.emergency.copernicus.eu/activations/EMSR927/) GRA **al 28 de agosto de 2026**: deslizamientos fotointerpretados en Syapru Besi y Timure (WorldView-3 / Legion, 27 ago 05:05 UTC). Capas apagables en el control de la esquina.
- Mapas GRA oficiales en el panel (AOI01 y AOI02). Bidur (AOI03) y Bharatpur (AOI04) aún no tenían producto publicado en esa fecha.
- Eje del río, comunidades con hora de llegada (NPT) y minutos de alerta perdidos.
- Límite del modelo en Devighat HEP: el frente siguió hacia Galchhi, Malekhu, Muglin y **Devghat (Chitwan) ~15:20**. No confundir Devighat HEP (Nuwakot) con Devghat.
- Curvas de nivel cada 10 m (índice cada 50 m), capa encendible y apagable. Clic en una curva muestra la cota.

**Copernicus EMSR927 (corte 28 ago 2026)**

Ya hay vector público GRA para las dos AOI de cabecera. El evento CEMS es `6-Mass Movement` / landslide, no una mancha de llanura.

| AOI | Localidad | Estado al 28 ago | Producto | Área deslizamiento | Edificios (dest. / dañ. / pos. dañ.) |
| --- | --- | --- | --- | --- | --- |
| 01 | Syapru Besi | Publicado (F) | GRA v1, WorldView-3 | **111 ha** | 323 / 32 / 78 |
| 02 | Timure | Publicado (F) | GRA v2, Legion | **129 ha** | 372 / 33 / 26 |
| 03 | Bidur | En curso (I) | — | — | — |
| 04 | Bharatpur | En espera (W) | Legion 29 ago (previsto) | — | — |

En el repo: `emsr927_hasta_hoy.geojson` y `media/emsr927_aoi01_syapru_besi.jpg`, `media/emsr927_aoi02_timure.jpg`.

<p align="center">
<img src="media/emsr927_aoi01_syapru_besi.jpg" alt="EMSR927 AOI01 Syapru Besi GRA" width="48%" />
<img src="media/emsr927_aoi02_timure.jpg" alt="EMSR927 AOI02 Timure GRA" width="48%" />
</p>

**Cómo se construyó la mancha HAND**

La mancha naranja/roja es un HAND aproximado sobre el DEM NASA HMA 8 m (`HMA_DEM8m_MOS_20170716_tile-675`, Shean 2017, cotas elipsoidales WGS84). No sustituye a EMSR927: cubre todo el corredor hasta Devighat; CEMS solo ha publicado las AOI de cabecera.

| Tramo | Núcleo (H / ancho) | Runup (H / ancho) |
| --- | --- | --- |
| Garganta km 0–20 | 12 m / 280 m | 40 m / 450 m |
| Medio km 20–40 | 10 m / 450 m | 30 m / 700 m |
| Bajo | 9 m / 700 m | 22 m / 1100 m |

Curvas: contornos cada 10 m del mismo DEM, recortados a ~1.5 km del cauce.

Sentinel-1 (par 16 vs 28 ago, misma órbita) y Sentinel-2 (24 vs 27 ago, 54–78 % nubes) **no** delinean el corredor: el cambio S1 fiable es ~3 ha frente a ~830 ha HAND.

**Scripts que regeneran esta página**

1. `generar_mapa_inundacion.py` → `inundacion_bhote_koshi.geojson`
2. `generar_curvas_10m.py` → `curvas_10m_hma.geojson`
3. `preparar_emsr927.py` → `emsr927_hasta_hoy.geojson` + JPEG en `media/`
4. `escribir_mapa_html.py` → `index.html`

El GeoTIFF HMA no va en el repositorio (~348 MB, Earthdata). Hace falta en local para volver a generar curvas o la mancha. Los zips GRA de CEMS tampoco van al repo.

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


