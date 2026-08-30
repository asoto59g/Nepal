# Nepal — Bhote Koshi, 26 agosto 2026

<img width="1024" height="512" alt="preview" src="https://github.com/user-attachments/assets/215d272c-fcc6-41a2-962a-456144608a05" />
Análisis del pulso de detritos **cicatriz Langtang → Bharatpur (Narayani)** tras la avalancha de hielo y roca del 26 de agosto de 2026. (Análisis 30/08/26)

Sitio: https://asoto59g.github.io/Nepal/

Las dos piezas para presentar son HTML estático. No hay servidor ni base de datos.

| Página | Archivo | Qué muestra |
| --- | --- | --- |
| Inicio | [index.html](index.html) | Mapa: eje desde la cicatriz, mancha HAND Rasuwagadhi–Bharatpur, curvas, EMSR927 al 29 ago 2026 |
| Segunda | [tiempos.html](tiempos.html) | Curva x(t), Manning 1 km, pico vs HAND, minutos de alerta perdidos |

En cada página hay un enlace a la otra (Mapa / Tiempos de alerta).


---

## index.html — mapa de inundación

Fuente de la página: este HTML (Leaflet 1.9, datos embebidos). No llama a una API propia.

**Qué se ve**

- Núcleo de valle (~16.8 km²) y runup en ladera (~11.2 km²) **solo Rasuwagadhi → Bharatpur**. El eje del cauce empieza en la cicatriz Langtang (**km 0**, 08:37) y mide **200.3 km** hasta Bharatpur; Rasuwagadhi queda en **km 19 (08:54)**. La mancha naranja/roja es **ocupación HAND del valle** (12→5 m), **no** el tirante de pico (80–96 m en garganta). Capa encendible y apagable en el cajetín de capas (arriba a la derecha).
- Barra de escala métrica en la esquina inferior izquierda, pegada al borde.
- Polígonos y edificios de [Copernicus EMSR927](https://mapping.emergency.copernicus.eu/activations/EMSR927/) GRA **al 29 de agosto de 2026**: deslizamientos fotointerpretados en Syapru Besi, Timure y Bidur. Capas apagables en el control de la esquina.
- Mapas GRA oficiales en el panel (AOI01, AOI02 y AOI03). Bharatpur (AOI04) sigue **en espera (W)**: Legion adquirido el 29 ago 04:01 UTC, entrega prevista **17:01 UTC** (mañana por la mañana en Costa Rica / tarde en Nepal). El recuadro azul discontinuo en el mapa es el AOI, sin polígonos GRA.
- Eje del río, comunidades con hora de llegada (NPT) y minutos de alerta perdidos, hasta Bharatpur.
- **Devighat HEP (Nuwakot, km 77, 09:59)** no es **Devghat (Chitwan, km 196, 15:20 DHM)**. El modelo llega a Bharatpur a las **15:32**.
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

La mancha naranja/roja es un HAND aproximado sobre NASA HMA 8 m (`HMA_DEM8m_MOS_20170716_tile-675`, Shean 2017, cotas elipsoidales WGS84) y Copernicus GLO-30 (N27E084) en el borde oeste del mosaico (~84.45°E), con offset vertical **−43.9 m** al datum HMA (mediana del solape; Geopera reporta −35.5 m HMA–GLO30). No se pinta Lhende ni el glaciar: a 5600 m un HAND de 12–40 m sería basura. No sustituye a EMSR927.

| Tramo (km desde Rasuwagadhi) | Núcleo (H / ancho) | Runup (H / ancho) |
| --- | --- | --- |
| Garganta km 0–20 | 12 m / 280 m | 40 m / 450 m |
| Medio km 20–40 | 10 m / 450 m | 30 m / 700 m |
| Devighat km 40–60 | 9 m / 700 m | 22 m / 1100 m |
| Trishuli medio km 60–100 | 7 m / 900 m | 16 m / 1500 m |
| Narayani km >100 | 5 m / 1500 m | 10 m / 2800 m |

Áreas resultantes: núcleo **16.8 km²**, runup **11.2 km²**. El **tirante de pico** (80 m en la cicatriz, 96 m en Rasuwagadhi, 40 m en Syabrubesi, 20 m en Betrawati, 9 m en Galchhi) va en [tiempos.html](tiempos.html), no en la mancha.

Curvas: 10 m en garganta, 20 m bajo 400 m, recortadas a ~1.2 km del cauce.

Sentinel-1 (par 16 vs 28 ago, misma órbita) y Sentinel-2 (24 vs 27 ago, 54–78 % nubes) **no** delinean el corredor alto: el cambio S1 fiable es ~3 ha frente a la mancha HAND. En la **cabecera** sí hay señal (ver abajo).

**Scripts que regeneran esta página**

1. `calcular_manning.py` → `resultado_manning.json` / `curva_1km.csv` / `observaciones.csv` (Lhende + OSM por hitos)
2. `generar_mapa_inundacion.py` → `inundacion_bhote_koshi.geojson`
3. `generar_curvas_10m.py` → `curvas_10m_hma.geojson`
4. `preparar_emsr927.py` → `emsr927_hasta_hoy.geojson` + JPEG en `media/`
5. `detectar_origen_sentinel.py` → `origen_avalancha.geojson`
6. `detectar_lago_s1.py` → `lago_escombros.geojson`
7. `detectar_deslizamientos_s1.py` → `deslizamientos_s1_norte.geojson`
8. `escribir_mapa_html.py` → `index.html`
9. `escribir_tiempos_html.py` → `tiempos.html`

El GeoTIFF HMA (~348 MB), COP30 N27E084 y N28E085 no van en el repositorio. Los zips GRA de CEMS tampoco.

---

## Deslizamientos S1 al norte de Rasuwagadhi (2023–2026)

Capa informativa en el mapa (ámbar, apagable). No sustituye a EMSR927.

Par Sentinel-1 RTC VV, **órbita 85 ascendente**: 25 ago 2023 vs 28 ago 2026. Semicírculo de **20 km al norte** de Rasuwagadhi. Se vectorizan parches con |ΔVV| ≥ 5 dB, cota bajo 5200 m, pendiente ≥ 8° y área **≥ 0.5 km²**.

Resultado: **18 polígonos, 13.8 km²**. El más oscuro (1.05 km², −6.5 dB) cae junto a la cicatriz Langtang / lago de escombros. Tres años cubren más que el pulso del 26 ago 2026.

Script: `detectar_deslizamientos_s1.py`. Los GeoTIFF RTC locales no van al repo.

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

Fuente de la página: este HTML (tablas y SVG; sin Leaflet). Cifras tomadas de `resultado_manning.json` / `curva_1km.csv`. Observaciones (USGS, caídas de radio, DHM, Suhora, Geopera): `observaciones.csv`.

**Reloj (NPT)** — t = 0 en la cicatriz, 08:37. Las caídas de estación 08:50 / 09:20 son corte de radio, no el frente.

- 08:37 sismo / avalancha (USGS); km 0 = cicatriz S2 28.285°N 85.513°E.
- 08:38 alerta automática hipotética (90 s después).
- 08:50 Syabrubesi deja de transmitir (radio).
- 08:54 Rasuwagadhi (frontera, ~17 min).
- 09:09 Syabrubesi (frente; pico ~40 m).
- 09:16 SMS masivo DHM.
- 09:20 Betrawati deja de transmitir (radio).
- 09:40 Betrawati (frente; pico ~20 m).
- 09:59 Devighat HEP (Nuwakot).
- 11:02 Galchhi (DHM ~9 m / 30 min).
- 15:20 Devghat (Chitwan): frente DHM (ancla del tramo bajo).
- 15:32 Bharatpur (Narayani), modelo.

**Manning y detritos**

Lhende (cicatriz → Rasuwagadhi, 19 km): **avalancha de detritos** a **18.6 m/s** (67 km/h), no Manning. A partir de Rasuwagadhi: `V = (1/n) · R^(2/3) · S^(1/2)` con **n = 0.10 / 0.05 / 0.040**.

| Tramo | n | R | Ancla |
| --- | --- | --- | --- |
| Lhende | — (detritos) | — | 08:37 → 08:54 |
| Rasuwagadhi → Syabrubesi | 0.10 | **R1 = 29.7 m** | 15 min |
| Syabrubesi → Betrawati | 0.05 | **R2 = 22.4 m** | 31 min |
| Betrawati → Galchhi | 0.040 | **R3 = 10.3 m** | 82 min |
| Galchhi → Devghat / Bharatpur | 0.040 | **R4 = 25.2 m** | DHM 15:20 |

DEM: HMA 8 m + COP30 N27E084 y N28E085 (offset −43.9 m). Longitud **200.3 km** (corredor 181.3 km), desnivel corredor 1628 m.

A las 09:16 el frente está entre Syabrubesi (09:09) y Betrawati (09:40). Aguas abajo de Mailung (~km 51) los minutos perdidos son constantes: **38 min** (09:16 − 08:38).

| Lugar | km | Llegada | Pico (m) | HAND (m) | SMS 09:16 | Auto 08:38 | Perdidos |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Cicatriz Langtang | 0 | 08:37 | 80 | 0 | 0 | 0 | 0 |
| Rasuwagadhi | 19 | 08:54 | 96 | 12 | 0 | 16 | 16 |
| Timure | 22 | 08:56 | 73 | 12 | 0 | 19 | 19 |
| Syabrubesi | 33 | 09:09 | 40 | 12 | 0 | 31 | 31 |
| Mailung | 51 | 09:30 | 28 | 10 | 14 | 52 | **38** |
| Betrawati | 64 | 09:40 | 20 | 9 | 24 | 62 | **38** |
| Trishuli HEP | 72 | 09:51 | 17 | 9 | 35 | 73 | **38** |
| Devighat HEP | 77 | 09:59 | 16 | 9 | 44 | 82 | **38** |
| Galchhi | 98 | 11:02 | 9 | 7 | 106 | 144 | **38** |
| Malekhu | 121 | 12:07 | 7 | 5 | 172 | 210 | **38** |
| Muglin | 163 | 13:43 | 6 | 5 | 267 | 305 | **38** |
| Devghat (Chitwan) | 196 | 15:20 | 5 | 5 | 364 | 402 | **38** |
| Bharatpur | 200.3 | 15:32 | 5 | 5 | 377 | 415 | **38** |

El pico (Geopera/DHM) no es la mancha HAND. R de Manning se calibra a tiempos, no a aforos. Manning de agua clara es de primer orden; el evento fue un flujo de detritos.

En [tiempos.html](tiempos.html) hay tres series de altura cada 10 km: **pico**, **HAND** y **R**, más velocidad y hora NPT.

Tiempos y picos de garganta alineados a [geo-pera/bhotekoshi-2026-reconstruction](https://github.com/geo-pera/bhotekoshi-2026-reconstruction) (métodos 1D Saint-Venant). **No se copian** sus vectores Planet/WorldView (**CC BY-NC**; ABC es comercial). El corredor hasta Bharatpur, el SMS 09:16 vs 08:38 y EMSR927 siguen siendo objetivos ABC.

**Scripts:** `calcular_manning.py` (cauce: Lhende + `rios_overpass.json`) y `escribir_tiempos_html.py`.

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


