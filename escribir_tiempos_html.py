# -*- coding: utf-8 -*-
"""Genera tiempos.html a partir de resultado_manning.json."""
from __future__ import annotations

import json
from pathlib import Path

here = Path(__file__).resolve().parent
man = json.loads((here / "resultado_manning.json").read_text(encoding="utf-8"))
comm = man["comunidades"]
curva = man["curva_1km"]
frente = man["frente_por_hora"]
km_tot = man["longitud_km"]
desnivel = man["desnivel_m"]
pend = man["pendiente_media_pct"]
R1 = man["R_calibrado_m"]
R2 = man.get("R_tramo_bajo_m", R1)
n_m = man["n_manning"]

CHART_IDS = [
    "rasuwagadhi",
    "timure",
    "syabrubesi",
    "mailung",
    "betrawati",
    "devighat",
    "galchhi",
    "malekhu",
]
LABEL = {
    "rasuwagadhi": "Rasuwagadhi",
    "timure": "Timure",
    "syabrubesi": "Syabrubesi",
    "mailung": "Mailung",
    "betrawati": "Betrawati",
    "devighat": "Devighat",
    "galchhi": "Galchhi",
    "malekhu": "Malekhu",
    "muglin": "Muglin",
    "devghat": "Devghat",
    "bharatpur": "Bharatpur",
}
by_id = {c["id"]: c for c in comm}
chart_comm = [by_id[i] for i in CHART_IDS if i in by_id]


def row_class(c):
    h = c["hora_llegada"]
    if h < "09:16":
        return "danger" if c["km"] < 10 else "warning"
    if c["km"] < 50:
        return "info"
    return "ok"


def bars_svg(items):
    n = len(items)
    left, right, top, bot = 70, 870, 20, 220
    ymax = 70.0
    # After Devighat, aviso potencial > 70 min — scale to next 50.
    pot_max = max(c["aviso_potencial_min"] for c in items)
    if pot_max > 70:
        ymax = 50.0 * (int(pot_max / 50) + 1)
    inner_w = right - left
    slot = inner_w / n
    lines = []
    ticks = list(range(0, int(ymax) + 1, int(ymax / 7)))
    for t in ticks:
        y = bot - t * (bot - top) / ymax
        lines.append(
            f'<line class="grid-line" stroke="#c4c4cc" fill="none" x1="{left}" y1="{y:.1f}" x2="{right}" y2="{y:.1f}" />'
        )
    lines.append(
        f'<line class="axis-line" stroke="#a1a1aa" fill="none" x1="{left}" y1="{top}" x2="{left}" y2="{bot}" />'
    )
    lines.append(
        f'<line class="axis-line" stroke="#a1a1aa" fill="none" x1="{left}" y1="{bot}" x2="{right}" y2="{bot}" />'
    )
    ylbl = [f'<g fill="#52525b" font-size="11" font-family="Segoe UI, sans-serif">']
    for t in ticks:
        y = bot - t * (bot - top) / ymax
        txt = f"{int(t)}" if t < ymax else f"{int(t)} min"
        ylbl.append(f'<text x="{left-8}" y="{y+4:.0f}" text-anchor="end">{txt}</text>')
    ylbl.append("</g>")
    rects = ["<g>"]
    vals = ['<g text-anchor="middle">']
    xlbl = [
        '<g fill="#52525b" font-size="10" font-family="Segoe UI, sans-serif" text-anchor="middle">'
    ]
    for i, c in enumerate(items):
        cx = left + (i + 0.5) * slot
        w = min(22, slot * 0.28)
        for j, (key, color, cls) in enumerate(
            (
                ("aviso_real_min", "#b54708", "val-warn"),
                ("aviso_potencial_min", "#067647", "val-ok"),
            )
        ):
            v = max(0.0, float(c[key]))
            h = v * (bot - top) / ymax
            x = cx - w - 2 if j == 0 else cx + 2
            y = bot - h
            rects.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{color}" />'
            )
            ty = y - 3 if h > 8 else bot - 4
            vals.append(
                f'<text class="val {cls}" x="{x+w/2:.1f}" y="{ty:.1f}">{v:.0f}</text>'
            )
        xlbl.append(f'<text x="{cx:.1f}" y="{bot+20}">{LABEL.get(c["id"], c["nombre"][:10])}</text>')
    rects.append("</g>")
    vals.append("</g>")
    xlbl.append("</g>")
    return (
        f'<svg viewBox="0 0 900 280" role="img" aria-label="Minutos de aviso real vs potencial">\n'
        + "\n".join(["<g>"] + lines + ["</g>"] + ylbl + rects + vals + xlbl)
        + "\n</svg>"
    )


def line_svg(xs, ys, xlabels, ylabel, color="#b42318", y_max=None, val_fmt="{:.0f}"):
    left, right, top, bot = 70, 870, 20, 210
    n = len(xs)
    ymax = y_max if y_max is not None else max(ys) * 1.08
    if ymax <= 0:
        ymax = 1
    pts = []
    for i, yv in enumerate(ys):
        x = left + i * (right - left) / (n - 1)
        y = bot - (yv / ymax) * (bot - top)
        pts.append((x, y, yv))
    poly = " ".join(f"{x:.1f},{y:.1f}" for x, y, _ in pts)
    area = f"{pts[0][0]:.1f},{bot} " + poly + f" {pts[-1][0]:.1f},{bot}"
    yticks = 5
    step = ymax / yticks
    grid = []
    ylab = ['<g fill="#52525b" font-size="11" font-family="Segoe UI, sans-serif">']
    for i in range(yticks + 1):
        v = i * step
        y = bot - (v / ymax) * (bot - top)
        grid.append(
            f'<line class="grid-line" stroke="#c4c4cc" fill="none" x1="{left}" y1="{y:.1f}" x2="{right}" y2="{y:.1f}" />'
        )
        lab = f"{v:.0f}" if i < yticks else ylabel
        ylab.append(f'<text x="{left-8}" y="{y+4:.0f}" text-anchor="end">{lab}</text>')
    ylab.append("</g>")
    grid.append(
        f'<line class="axis-line" stroke="#a1a1aa" fill="none" x1="{left}" y1="{top}" x2="{left}" y2="{bot}" />'
    )
    grid.append(
        f'<line class="axis-line" stroke="#a1a1aa" fill="none" x1="{left}" y1="{bot}" x2="{right}" y2="{bot}" />'
    )
    circles = "<g fill='%s'>" % color + "".join(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" />' for x, y, _ in pts
    ) + "</g>"
    vals = ['<g text-anchor="middle">']
    for x, y, v in pts:
        vals.append(
            f'<text class="val val-danger" x="{x:.1f}" y="{y-8:.1f}" fill="{color}">{val_fmt.format(v)}</text>'
        )
    vals.append("</g>")
    xlab = [
        '<g fill="#52525b" font-size="11" font-family="Segoe UI, sans-serif" text-anchor="middle">'
    ]
    for i, lab in enumerate(xlabels):
        x = left + i * (right - left) / (n - 1)
        xlab.append(f'<text x="{x:.1f}" y="{bot+22}">{lab}</text>')
    xlab.append("</g>")
    fill = color.replace(")", ",0.12)").replace("rgb", "rgba") if color.startswith("rgb") else None
    # simple rgba from hex
    r = int(color[1:3], 16)
    g = int(color[3:5], 16)
    b = int(color[5:7], 16)
    return f"""<svg viewBox="0 0 900 268" role="img">
        <g>
        {"".join(grid)}
        </g>
        {"".join(ylab)}
        <polyline fill="rgba({r},{g},{b},0.12)" stroke="none" points="{area}" />
        <polyline fill="none" stroke="{color}" stroke-width="2.5" points="{poly}" />
        {circles}
        {"".join(vals)}
        {"".join(xlab)}
        </svg>"""


rows = []
for c in comm:
    if c["id"] == "chilime":
        continue
    rows.append(
        f'<tr class="{row_class(c)}"><td>{c["nombre"]}</td>'
        f'<td>{c["km"]:.1f}</td><td>{c["z"]:.0f}</td>'
        f'<td>{c["hora_llegada"]}</td>'
        f'<td>{c["aviso_real_min"]:.0f} min</td>'
        f'<td>{c["aviso_potencial_min"]:.0f} min</td>'
        f'<td>{c["minutos_perdidos"]:.0f}</td></tr>'
    )

frente_ok = [f for f in frente if f.get("km") is not None]
xs_f = [f["km"] for f in frente_ok]
xl_f = [f["hora"] for f in frente_ok]
svg_frente = line_svg(xl_f, xs_f, xl_f, f"{int(max(xs_f)+5)} km", "#b42318", y_max=max(xs_f) * 1.1, val_fmt="{:.1f}")

# velocidad cada 10 km
step_km = 10
vel_pts = [p for p in curva if abs(p["km"] % step_km) < 0.01 or p is curva[-1]]
# unique by rounded km
seen = set()
vel_u = []
for p in curva:
    k = int(round(p["km"] / step_km) * step_km)
    if k in seen:
        continue
    if abs(p["km"] - k) > 0.6 and p is not curva[-1]:
        continue
    seen.add(k)
    vel_u.append(p)
if curva[-1] not in vel_u:
    vel_u.append(curva[-1])
svg_vel = line_svg(
    [p["km"] for p in vel_u],
    [p["V_mps"] for p in vel_u],
    [f"{p['km']:.0f}" for p in vel_u],
    "m/s",
    "#175cd3",
    y_max=max(5, max(p["V_mps"] for p in vel_u) * 1.15),
    val_fmt="{:.1f}",
)

dev = by_id.get("devghat") or {}
bha = by_id.get("bharatpur") or {}
hep = by_id.get("devighat") or {}

html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Minutos de alerta perdidos — Bhote Koshi 26 ago 2026</title>
  <style>
    :root {{
      --text: #18181b; --muted: #52525b; --line: #e4e4e7; --bg: #fafafa;
      --card: #fff; --danger: #b42318; --danger-bg: #fef3f2;
      --warning: #b54708; --warning-bg: #fffaeb; --success: #067647;
      --info: #175cd3; --info-bg: #eff8ff;
    }}
    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; padding: 0; }}
    body {{
      font-family: "Segoe UI", system-ui, sans-serif;
      color: var(--text); background: var(--bg); line-height: 1.45;
    }}
    .page {{ max-width: 980px; margin: 0 auto; padding: 32px 24px 64px; }}
    header {{ border-bottom: 1px solid var(--line); padding-bottom: 16px; margin-bottom: 24px; }}
    .org {{ font-size: 12px; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); margin: 0 0 8px; }}
    h1 {{ font-size: 24px; font-weight: 650; margin: 0 0 8px; }}
    h2 {{ font-size: 16px; font-weight: 650; margin: 32px 0 8px; }}
    p.lead, p.caption {{ color: var(--muted); font-size: 14px; margin: 0 0 16px; }}
    p.caption {{ font-size: 12px; }}
    p.caption a {{ color: var(--info); }}
    .alert {{ background: var(--danger-bg); border-left: 3px solid var(--danger); padding: 14px 16px; margin: 20px 0; }}
    .alert strong {{ color: var(--danger); display: block; margin-bottom: 4px; }}
    .alert p {{ margin: 0; font-size: 14px; }}
    .stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 20px 0; }}
    .stat {{ background: var(--card); border: 1px solid var(--line); padding: 14px 16px; }}
    .stat .v {{ font-size: 22px; font-weight: 650; }}
    .stat .l {{ font-size: 12px; color: var(--muted); margin-top: 4px; }}
    .stat.danger .v {{ color: var(--danger); }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; background: var(--card); margin: 8px 0 20px; }}
    th, td {{ padding: 8px 10px; border-bottom: 1px solid var(--line); text-align: right; }}
    th:first-child, td:first-child {{ text-align: left; }}
    th {{ font-weight: 600; color: var(--muted); font-size: 12px; }}
    tbody tr:nth-child(even) {{ background: #f4f4f5; }}
    tr.danger td:first-child {{ color: var(--danger); font-weight: 600; }}
    tr.warning td:first-child {{ color: var(--warning); font-weight: 600; }}
    tr.info td:first-child {{ color: var(--info); font-weight: 600; }}
    tr.ok td:first-child {{ color: var(--success); font-weight: 600; }}
    .chart {{ background: var(--card); border: 1px solid var(--line); padding: 16px 12px 8px; margin: 8px 0 20px; }}
    .legend {{ display: flex; gap: 16px; font-size: 12px; color: var(--muted); margin: 0 12px 8px; flex-wrap: wrap; }}
    .legend span::before {{ content: ""; display: inline-block; width: 10px; height: 10px; margin-right: 6px; vertical-align: -1px; }}
    .sw-warn::before {{ background: var(--warning); }}
    .sw-ok::before {{ background: var(--success); }}
    .sw-danger::before {{ background: var(--danger); }}
    .sw-info::before {{ background: var(--info); }}
    .cards {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin: 16px 0; }}
    .card {{ background: var(--card); border: 1px solid var(--line); padding: 16px; }}
    .card h3 {{ margin: 0 0 8px; font-size: 14px; }}
    .card p {{ margin: 0; font-size: 14px; color: var(--muted); }}
    footer {{ border-top: 1px solid var(--line); margin-top: 28px; padding-top: 12px; font-size: 12px; color: var(--muted); }}
    svg {{ display: block; width: 100%; height: auto; }}
    svg .grid-line {{ stroke: #d4d4d8; stroke-width: 1; }}
    svg .axis-line {{ stroke: #a1a1aa; stroke-width: 1.25; }}
    svg .val {{ font-size: 10px; font-weight: 650; font-family: "Segoe UI", system-ui, sans-serif; fill: #18181b; }}
    svg .val-warn {{ fill: #b54708; }}
    svg .val-ok {{ fill: #067647; }}
    svg .val-danger {{ fill: #b42318; }}
    svg .val-info {{ fill: #175cd3; }}
    .site-nav {{ display: flex; gap: 4px; margin: 0 0 12px; }}
    .site-nav a {{ font-size: 12px; font-weight: 600; color: var(--muted); text-decoration: none; padding: 4px 10px; border: 1px solid var(--line); background: var(--card); }}
    .site-nav a.is-on {{ background: var(--text); color: #fff; border-color: var(--text); }}
    @media (max-width: 720px) {{ .stats, .cards {{ grid-template-columns: 1fr 1fr; }} }}
  </style>
</head>
<body>
  <article class="page">
    <header>
      <nav class="site-nav" aria-label="Paginas">
        <a href="index.html">Mapa</a>
        <a class="is-on" href="tiempos.html">Tiempos de alerta</a>
      </nav>
      <p class="org">ABC Geomática Agrícola · Nepal · 26 agosto 2026</p>
      <h1>Minutos de alerta perdidos — Bhote Koshi a Bharatpur</h1>
      <p class="lead">
        Manning cada 1 km, Rasuwagadhi → Bharatpur. Tramo alto (HMA 8 m) calibrado
        a Syabrubesi 08:50 y Betrawati 09:20. Tramo bajo (Trishuli–Narayani) calibrado
        a Devghat ~15:20 DHM. SMS 09:16. Alerta automática hipotética 08:38.
      </p>
    </header>

    <div class="alert">
      <strong>Cuando salieron los SMS el frente ya iba a Betrawati</strong>
      <p>
        A las 09:16 el modelo sitúa el frente ~3.5 km aguas arriba de Betrawati.
        Rasuwagadhi, Timure, Syabrubesi y Mailung ya habían sido alcanzados.
        Aguas abajo de Devighat HEP el pulso sigue hasta Devghat (Chitwan) y
        Bharatpur: el SMS llega {hep.get('aviso_real_min', 25):.0f}–{bha.get('aviso_real_min', 0):.0f}
        min antes, pero se perdieron {hep.get('minutos_perdidos', 38):.0f} min fijos
        respecto a una alerta a las 08:38.
      </p>
    </div>

    <p class="caption">
      Delineación satelital oficial al 29 ago 2026: Copernicus
      <a href="https://mapping.emergency.copernicus.eu/activations/EMSR927/">EMSR927</a>
      GRA (Syapru Besi, Timure y Bidur). Bharatpur (AOI04) aún no publicado
      (Legion 29 ago 04:01 UTC; entrega prevista 17:01 UTC). Polígonos en el
      <a href="index.html">mapa</a>.
    </p>

    <div class="stats">
      <div class="stat"><div class="v">{km_tot:.1f} km</div><div class="l">Cauce HMA + COP30 + OSM</div></div>
      <div class="stat"><div class="v">{desnivel:,.0f} m</div><div class="l">Desnivel ({pend:.2f} %)</div></div>
      <div class="stat"><div class="v">{R1:.1f} / {R2:.1f} m</div><div class="l">R1 garganta / R2 valle (n = {n_m:.3f})</div></div>
      <div class="stat danger"><div class="v">38 min</div><div class="l">Retraso del SMS vs 08:38</div></div>
    </div>

    <h2>Minutos de aviso por comunidad</h2>
    <p class="caption">
      Aviso real = llegada − 09:16 (0 si el SMS llegó tarde). Aviso potencial
      = llegada − 08:38. Minutos perdidos = potencial − real. Chilime poblado
      queda fuera del cauce y no se grafica.
    </p>
    <div class="chart">
      <div class="legend">
        <span class="sw-warn">Aviso real (SMS 09:16), min</span>
        <span class="sw-ok">Aviso si alerta a 08:38, min</span>
      </div>
      {bars_svg(chart_comm)}
    </div>

    <table>
      <thead>
        <tr>
          <th>Lugar</th><th>km</th><th>z (m)</th><th>Llegada</th>
          <th>SMS 09:16</th><th>Auto 08:38</th><th>Perdidos</th>
        </tr>
      </thead>
      <tbody>
        {"".join(rows)}
      </tbody>
    </table>

    <h2>Dónde estaba el frente a cada hora</h2>
    <p class="caption">
      Eje X: hora NPT. Eje Y: km desde Rasuwagadhi. Garganta anclada a
      Syabrubesi 08:50 y Betrawati 09:20; valle bajo a Devghat 15:20 (DHM).
    </p>
    <div class="chart">
      <div class="legend">
        <span class="sw-danger">Frente (km desde Rasuwagadhi)</span>
      </div>
      {svg_frente}
    </div>

    <h2>Velocidad Manning por tramo (cada 10 km)</h2>
    <p class="caption">
      V = (1/n) R<sup>2/3</sup> S<sup>1/2</sup>. R1 = {R1:.2f} m hasta Devighat HEP;
      R2 = {R2:.2f} m después (con R1 el frente llegaría a Devghat ~18:19;
      R2 adelanta el tramo bajo a la ancla DHM 15:20).
      Picos locales son ruido del DEM, no un segundo pulso.
    </p>
    <div class="chart">
      <div class="legend">
        <span class="sw-info">Velocidad (m/s)</span>
      </div>
      {svg_vel}
    </div>

    <div class="cards">
      <div class="card">
        <h3>Zona alta: casi sin margen</h3>
        <p>
          Rasuwagadhi cae ~08:36 en el modelo. Timure minutos después.
          Syabrubesi 12 min si la alerta saliera a las 08:38; con el SMS de
          las 09:16, cero. El tramo HAND original terminaba en Devighat HEP
          ({hep.get('km', 58.7):.1f} km, {hep.get('hora_llegada', '09:40')}).
        </p>
      </div>
      <div class="card">
        <h3>Tramo bajo: Devghat y Bharatpur</h3>
        <p>
          Devghat (Chitwan) {dev.get('hora_llegada', '15:20')} NPT (ancla DHM ~15:20).
          Bharatpur {bha.get('hora_llegada', '—')} NPT, km {bha.get('km', '—')}.
          Copernicus AOI04 sigue en espera. El retraso del SMS vs 08:38 permanece
          en 38 min en todo lo que el agua alcanza después de las 09:16.
        </p>
      </div>
    </div>

    <footer>
      {man.get('fuente_dem', '')}. {man.get('nota_devighat', '')}
      {man.get('nota_r2', '')}
      Delineacion satelital oficial: EMSR927 GRA AOI01–03; AOI04 Bharatpur pendiente
      (Legion 29 ago). ABC Geomática Agrícola SRL, 29 ago 2026.
    </footer>
  </article>
</body>
</html>
"""

dest = here / "tiempos.html"
dest.write_text(html, encoding="utf-8")
print("wrote", dest, dest.stat().st_size)
