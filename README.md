# Nepal — Bhote Koshi, 26 agosto 2026

<img width="1024" height="512" alt="preview" src="https://github.com/user-attachments/assets/215d272c-fcc6-41a2-962a-456144608a05" />
Análisis del pulso de detritos Rasuwagadhi → Bharatpur (Narayani) tras la avalancha de hielo y roca del 26 de agosto de 2026. (Análisis 29/08/26)

Sitio: https://asoto59g.github.io/Nepal/

Las dos piezas para presentar son HTML estático. No hay servidor ni base de datos.

| Página | Archivo | Qué muestra |
| --- | --- | --- |
| Inicio | [index.html](index.html) | Mapa: mancha HAND Rasuwagadhi–Bharatpur, curvas, EMSR927 al 29 ago 2026 |
| Segunda | [tiempos.html](tiempos.html) | Curva x(t), Manning 1 km y minutos de alerta perdidos |

En cada página hay un enlace a la otra (Mapa / Tiempos de alerta).


---

## index.html — mapa de inundación

Fuente de la página: este HTML (Leaflet 1.9, datos embebidos). No llama a una API propia.

**Qué se ve**

- Núcleo de valle (~17.4 km²) y runup en ladera (~11.0 km²) entre Rasuwagadhi y Bharatpur, **181.4 km** de cauce. **Estimación HAND**, no es la delineación Copernicus. Capa encendible y apagable en el cajetín de capas (arriba a la derecha).
- Barra de escala métrica en la esquina inferior izquierda, pegada al borde.
- Polígonos y edificios de [Copernicus EMSR927](https://mapping.emergency.copernicus.eu/activations/EMSR927/) GRA **al 29 de agosto de 2026**: deslizamientos fotointerpretados en Syapru Besi, Timure y Bidur. Capas apagables en el control de la esquina.
- Mapas GRA oficiales en el panel (AOI01, AOI02 y AOI03). Bharatpur (AOI04) sigue **en espera (W)**: Legion adquirido el 29 ago 04:01 UTC, entrega prevista **17:01 UTC** (mañana por la mañana en Costa Rica / tarde en Nepal). El recuadro azul discontinuo en el mapa es el AOI, sin polígonos GRA.
- Eje del río, comunidades con hora de llegada (NPT) y minutos de alerta perdidos, hasta Bharatpur.
- **Devighat HEP (Nuwakot, km 58, 09:39)** no es **Devghat (Chitwan, km 178, 15:20 DHM)**. El modelo de dos tramos llega a Bharatpur a las **15:33**.
- Curvas de nivel (10 m en garganta, 20 m bajo 400 m), capa encendible y apagable. Clic en una curva muestra la cota.

**Copernicus EMSR927 (corte 29 ago 2026)**

Ya hay vector público GRA para las tres AOI del corredor alto y medio. El evento CEMS es `6-Mass Movement` / landslide, no una mancha de llanura. Total **829 ha**.

| AOI | Localidad | Estado al 29 ago | Producto | Área deslizamiento | Edificios (dest. / dañ. / pos. dañ.) |
| --- | --- | --- | --- | --- | --- |
| 01 | Syapru Besi | Publicado (F) | GRA v1, WorldView-3 27 ago 05:05 UTC | **111 ha** | 323 / 32 / 78 |
| 02 | Timure | Publicado (F) | GRA v2, Legion 27 ago 05:05 UTC | **129 ha** | 372 / 33 / 26 |
| 03 | Bidur | Publicado (F) | GRA v1, BlackSky 12:09 UTC / Satellogic 04:22 UTC (27 ago) | **589 ha** | 1826 / 220 / 297 |
| 04 | Bharatpur | En espera (W) | Legion 29 ago 04:01 UTC (entrega prevista 17:01 UTC) | — | — |

En el repo: `emsr927_hasta_hoy.geojson` y JPEG en `media/`.

<p align="center">
<img src="media/emsr927_aoi01_syapru_besi.jpg" alt="EMSR927 AOI01 Syapru Besi GRA" width="32%" />
<img src="media/emsr927_aoi02_timure.jpg" alt="EMSR927 AOI02 Timure GRA" width="32%" />
<img src="media/emsr927_aoi03_bidur.jpg" alt="EMSR927 AOI03 Bidur GRA" width="32%" />
</p>

**Cómo se construyó la mancha HAND**

La mancha naranja/roja es un HAND aproximado sobre NASA HMA 8 m (`HMA_DEM8m_MOS_20170716_tile-675`, Shean 2017, cotas elipsoidales WGS84) y Copernicus GLO-30 (N27E084) en el borde oeste del mosaico (~84.45°E), con offset vertical −49 m al datum HMA. No sustituye a EMSR927. El tile HMA cubre casi todo el corredor; Bharatpur ciudad queda ~2 km al oeste del borde.

| Tramo | Núcleo (H / ancho) | Runup (H / ancho) |
| --- | --- | --- |
| Garganta km 0–20 | 12 m / 280 m | 40 m / 450 m |
| Medio km 20–40 | 10 m / 450 m | 30 m / 700 m |
| Devighat km 40–60 | 9 m / 700 m | 22 m / 1100 m |
| Trishuli medio km 60–100 | 7 m / 900 m | 16 m / 1500 m |
| Narayani km >100 | 5 m / 1500 m | 10 m / 2800 m |

Áreas resultantes: núcleo **17.4 km²**, runup **11.0 km²** (el tramo bajo es valle abierto; no es comparable 1:1 con las 3.2 + 5.1 km² de solo la garganta).

Curvas: 10 m en garganta, 20 m bajo 400 m, recortadas a ~1.2 km del cauce.

Sentinel-1 (par 16 vs 28 ago, misma órbita) y Sentinel-2 (24 vs 27 ago, 54–78 % nubes) **no** delinean el corredor alto: el cambio S1 fiable es ~3 ha frente a la mancha HAND. En la **cabecera** sí hay señal (ver abajo).

**Scripts que regeneran esta página**

1. `calcular_manning.py` → `resultado_manning.json` / `curva_1km.csv` (cauce OSM por hitos)
2. `generar_mapa_inundacion.py` → `inundacion_bhote_koshi.geojson`
3. `generar_curvas_10m.py` → `curvas_10m_hma.geojson`
4. `preparar_emsr927.py` → `emsr927_hasta_hoy.geojson` + JPEG en `media/`
5. `detectar_origen_sentinel.py` → `origen_avalancha.geojson`
6. `detectar_lago_s1.py` → `lago_escombros.geojson`
7. `escribir_mapa_html.py` → `index.html`
8. `escribir_tiempos_html.py` → `tiempos.html`

El GeoTIFF HMA (~348 MB) y el COP30 N27E084 no van en el repositorio. Los zips GRA de CEMS tampoco.

---

## Origen del colapso (Sentinel-1 / Sentinel-2)

El punto USGS (landslide-type M 5.2, 08:37 NPT) está en **28.271°N, 85.515°E**, ~13 km al este de Rasuwagadhi, flanco norte de Langtang — **fuera** del bbox del corredor que se usó antes (ese bbox cortaba en 85.42°E).

| Fuente | Fecha | Qué se ve en 28.271 / 85.515 |
| --- | --- | --- |
| S2 45RUM | 24 ago | Nube 22 % en 2.5 km; pixel USGS = sombra de nube; 48 % hielo |
| S2 45RUM | 27 ago | Nube 47 %; pixel USGS = nieve/hielo |
| S2 45RUM | 29 ago | Nube 76 %; no usable |
| S1 IW GRD ascendente | 16 vs 28 ago | Misma órbita; sí cubre la cabecera |

**Punto de cicatriz (mejor estimación Sentinel):** **28.285°N, 85.513°E** (~1.6 km al norte del USGS).

- Sentinel-2 SCL 24 vs 27 ago: parche de **20.2 ha** donde la clase nieve/hielo desaparece (sin nubes en ambos días). Total de pérdida de hielo en la ventana: 103 ha (incluye fusión/estacional y posible mala clasificación).
- Sentinel-1 VV 16 vs 28 ago: parche de **3.8 ha** a 1.27 km del USGS, **−6.0 dB** (caída de backscatter, compatible con hielo que se va o superficie húmeda). A ~400 m del centroide S2. Hay más parches ±ΔVV a 1.6–1.9 km (escarpe rugoso / sombra).

No hay escena S1 posterior al 28 ago (corte 30 ago). S2 no mapea el corredor fluvial (Geopera: cielo conjunto 2.1 %). La delineación de daños en garganta sigue siendo EMSR927 / HAND, no Sentinel.

---

## Lago de escombros (S1 RTC / S2 SCL)

Dos lagos nuevos se reportaron tras el colapso (NDMA: 19.80 ha y 7.28 ha). Suhora/Satellogic (27 ago 04:22 UTC, 70 cm) sitúa uno de **20.25 ha** en **28°17′39.0″N, 85°30′38.9″E** (28.29417°N, 85.51081°E). Un segundo punto (Keystone, confianza media) está en 28.312°N, 85.554°E (confluencia Chhochen/Purepu). China informó el 30 ago que el lago bajo se vació y el alto perdió más de la mitad.

**Sentinel-1 no reconstruye el polígono de 20 ha.** No hay pasada el 27. El RTC VV del 28 ago 12:21 UTC, en el punto Suhora, pasa de −11.3 a **−10.2 dB** (no es agua abierta; agua calma suele ir < −17 dB). Encaja con el desbordamiento reportado esa mañana: para la tarde el espejo principal ya no está.

Lo que sí se vectoriza:

| Capa | Fecha | Área | Centro | Notas |
| --- | --- | --- | --- | --- |
| S2 SCL clase agua (nueva vs 24 ago) | 27 ago | **3.72 ha** | 28.29313°N, 85.51058°E | 120 m del punto Suhora. Pixel centro: suelo el 24, **agua el 27**, suelo otra vez el 29. SCL subestima vs 20 ha óptico (nubes/hielo en superficie). |
| S1 RTC VV oscuro y caída ≥3.5 dB | 16 vs 28 ago | **2.3 ha** (3 parches) | ~28.290°N, 85.512°E | 370–620 m al sur de Suhora. Agua residual o lecho húmedo, no el lago del 27. |
| Keystone | 27–29 ago | — | 28.312°N, 85.554°E | S2 nubes altas. S1 −6.4 → −9.9 dB: no es agua. |

El GRD sin calibrar no sirve para umbral de agua (DN ~+18 dB). Hay que usar **sentinel-1-rtc**. Script: `detectar_lago_s1.py` → `lago_escombros.geojson`.

---

## tiempos.html — minutos de alerta perdidos

Fuente de la página: este HTML (tablas y SVG; sin Leaflet). Cifras tomadas de `resultado_manning.json` / `curva_1km.csv`.

**Reloj (NPT)**

- 08:37 sismo / avalancha (USGS).
- 08:38 alerta automática hipotética (90 s después).
- 08:50 Syabrubesi deja de transmitir (ancla del modelo).
- 09:16 SMS masivo DHM.
- 09:20 Betrawati deja de transmitir (segunda ancla).

- 09:39 Devighat HEP (Nuwakot), modelo (fin de la garganta).
- 15:20 Devghat (Chitwan): frente DHM (ancla del tramo bajo).
- 15:33 Bharatpur (Narayani), modelo.

**Manning**

`V = (1/n) · R^(2/3) · S^(1/2)`, `n = 0.040`. **R1 = 10.05 m** calibrado para Syabrubesi → Betrawati = 30 min. **R2 = 18.95 m** aguas abajo de Devighat HEP para que Devghat coincida con DHM ~15:20 (con R1 solo el modelo llegaba ~18:19: el valle es más tendido). Eje OSM forzado por hitos (si no, el camino más corto se sale de la garganta). DEM: HMA 8 m + COP30 N27E084. Longitud **181.4 km**, desnivel 1638 m.

A las 09:16 el frente está ~km 42. Aguas abajo de ~km 42 los minutos perdidos son constantes: **38 min** (09:16 − 08:38).

| Lugar | km | Llegada | SMS 09:16 | Auto 08:38 | Perdidos |
| --- | --- | --- | --- | --- | --- |
| Rasuwagadhi | 0 | 08:36 | 0 | 0 | 0 |
| Timure | 3 | 08:38 | 0 | 0 | 0 |
| Syabrubesi | 15 | 08:50 | 0 | 12 | 12 |
| Mailung | 32 | 09:06 | 0 | 29 | 29 |
| Betrawati | 45 | 09:20 | 4 | 42 | **38** |
| Trishuli HEP | 53 | 09:31 | 15 | 53 | **38** |
| Devighat HEP | 58 | 09:39 | 24 | 62 | **38** |
| Galchhi | 79 | 10:15 | 60 | 98 | **38** |
| Malekhu | 105 | 11:25 | 129 | 167 | **38** |
| Muglin | 144 | 13:21 | 246 | 284 | **38** |
| Devghat (Chitwan) | 178 | 15:20 | 364 | 402 | **38** |
| Bharatpur | 181.4 | 15:33 | 377 | 415 | **38** |

Rasuwagadhi 08:36 queda ~1 min antes del sismo 08:37: el tramo alto es muy pendiente y el reloj está anclado en Syabrubesi 08:50. Manning de agua clara es de primer orden; el evento fue un flujo de detritos.

En [tiempos.html](tiempos.html) el gráfico de velocidad (cada 10 km) lleva la hora NPT de llegada del frente. Debajo, el **tirante hidráulico** en los mismos puntos: R de Manning (10.05 m / 18.95 m) y tirante HAND de valle (12→5 m).

**Scripts:** `calcular_manning.py` (cauce: `fetch_rios.py` / `rios_overpass.json`) y `escribir_tiempos_html.py`.

---

## Aviso cuando EMSR927 publique algo nuevo

Un workflow de GitHub Actions (`Vigilar EMSR927`) consulta la API de Copernicus cada 2 h. Si Bharatpur u otra AOI cambia de estado, sube de versión o aparece el zip GRA:

1. Abre un [issue](https://github.com/asoto59g/Nepal/issues) con etiqueta `emsr927` y te lo asigna (notificación GitHub; el correo de GitHub llega si tienes Issues activado en [notification settings](https://github.com/settings/notifications)).
2. Envía un correo a `oasotob@yahoo.com`.

El mapa no se actualiza solo. Tras el aviso: bajar el zip GRA, `python preparar_emsr927.py` y `python escribir_mapa_html.py`.

**Correo SMTP (obligatorio para el punto 2).** En el repo: Settings → Secrets and variables → Actions, crear:

| Secreto | Valor |
| --- | --- |
| `SMTP_PASSWORD` | Contraseña de aplicación de Yahoo (no la clave normal). [Generarla](https://login.yahoo.com/account/security) con verificación en dos pasos. |

Opcionales si no usas Yahoo: `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USER`, `MAIL_TO`, `MAIL_FROM`.

También se puede lanzar a mano: Actions → Vigilar EMSR927 → Run workflow.

---


