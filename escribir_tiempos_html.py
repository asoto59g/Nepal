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
desnivel = man.get("desnivel_corredor_m") or man["desnivel_m"]
pend = man["pendiente_media_pct"]
R1 = man.get("R1_m") or man["R_calibrado_m"]
R4 = man.get("R4_m") or man.get("R_tramo_bajo_m", R1)
R2 = man.get("R2_m") or R4
R3 = man.get("R3_m") or R4
R_lhende = man.get("R_lhende_m")
v_lhende = man.get("v_lhende_mps")
if v_lhende is None:
    v_lhende = 18.6
n_g = man.get("n_garganta", 0.10)
n_m = man.get("n_medio", man.get("n_manning", 0.05))
n_v = man.get("n_valle", 0.040)
km_ras = man.get("km_rasuwagadhi") or 0

CHART_IDS = [
    "origen",
    "rasuwagadhi",
    "timure",
    "syabrubesi",
    "betrawati",
    "galchhi",
    "devghat",
    "bharatpur",
]
LABEL = {
    "origen": "Cicatriz",
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
    if c["id"] in ("origen", "rasuwagadhi", "timure"):
        return "danger"
    if h < "09:16":
        return "warning"
    if c.get("km_corredor", c["km"] - km_ras) < 50:
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


def _xy_pts(ys, n, left, right, top, bot, ymax):
    pts = []
    for i, yv in enumerate(ys):
        x = left + i * (right - left) / (n - 1)
        y = bot - (float(yv) / ymax) * (bot - top)
        pts.append((x, y, float(yv)))
    return pts


def _hex_rgb(color):
    return int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)


def line_svg(
    xs,
    ys,
    xlabels,
    ylabel,
    color="#b42318",
    y_max=None,
    val_fmt="{:.0f}",
    xlabels2=None,
    series=None,
):
    """Una o más series. series=[{ys, color, fmt, label}] si se quiere dual."""
    left, right, top, bot = 70, 870, 20, 210
    n = len(xlabels)
    series = series or [{"ys": ys, "color": color, "fmt": val_fmt}]
    ymax = y_max
    if ymax is None:
        ymax = max(max(s["ys"]) for s in series) * 1.08
    if ymax <= 0:
        ymax = 1
    view_h = 290 if xlabels2 else 268
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
    drawn = []
    for si, s in enumerate(series):
        col = s["color"]
        fmt = s.get("fmt", val_fmt)
        pts = _xy_pts(s["ys"], n, left, right, top, bot, ymax)
        poly = " ".join(f"{x:.1f},{y:.1f}" for x, y, _ in pts)
        area = f"{pts[0][0]:.1f},{bot} " + poly + f" {pts[-1][0]:.1f},{bot}"
        r, g, b = _hex_rgb(col)
        circles = f"<g fill='{col}'>" + "".join(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" />' for x, y, _ in pts
        ) + "</g>"
        vals = ['<g text-anchor="middle">']
        dy = -8 if si == 0 else 14
        for x, y, v in pts:
            vals.append(
                f'<text class="val" x="{x:.1f}" y="{y+dy:.1f}" fill="{col}">{fmt.format(v)}</text>'
            )
        vals.append("</g>")
        drawn.append(
            f'<polyline fill="rgba({r},{g},{b},0.10)" stroke="none" points="{area}" />'
            f'<polyline fill="none" stroke="{col}" stroke-width="2.5" points="{poly}" />'
            f"{circles}{''.join(vals)}"
        )
    xlab = [
        '<g fill="#52525b" font-size="10" font-family="Segoe UI, sans-serif" text-anchor="middle">'
    ]
    for i, lab in enumerate(xlabels):
        x = left + i * (right - left) / (n - 1)
        xlab.append(f'<text x="{x:.1f}" y="{bot+20}">{lab}</text>')
    xlab.append("</g>")
    if xlabels2:
        xlab.append(
            '<g fill="#71717a" font-size="9" font-family="Segoe UI, sans-serif" text-anchor="middle">'
        )
        for i, lab in enumerate(xlabels2):
            x = left + i * (right - left) / (n - 1)
            xlab.append(f'<text x="{x:.1f}" y="{bot+34}">{lab}</text>')
        xlab.append("</g>")
    return f"""<svg viewBox="0 0 900 {view_h}" role="img">
        <g>
        {"".join(grid)}
        </g>
        {"".join(ylab)}
        {"".join(drawn)}
        {"".join(xlab)}
        </svg>"""


def h_hand_m(p):
    if p.get("h_hand_m") is not None:
        return float(p["h_hand_m"])
    kc = p.get("km_corredor")
    if kc is None:
        kc = float(p["km"]) - float(km_ras or 0)
    if kc < 0:
        return 0.0
    if kc < 20:
        return 12.0
    if kc < 40:
        return 10.0
    if kc < 60:
        return 9.0
    if kc < 100:
        return 7.0
    return 5.0


rows = []
for c in comm:
    if c["id"] == "chilime":
        continue
    rows.append(
        f'<tr class="{row_class(c)}"><td>{c["nombre"]}</td>'
        f'<td>{c["km"]:.1f}</td><td>{c["z"]:.0f}</td>'
        f'<td>{c["hora_llegada"]}</td>'
        f'<td>{c.get("h_pico_m", "—")}</td>'
        f'<td>{c.get("h_hand_m", "—")}</td>'
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

tramos = man.get("tramos") or []
r_by_km = {
    round(float(t["km_ini"]), 2): float(t["R_m"])
    for t in tramos
    if t.get("R_m") is not None
}
r_last = float(tramos[-1]["R_m"]) if tramos else R1

def r_at(p):
    if p.get("R_m") is not None:
        return float(p["R_m"])
    k = round(float(p["km"]), 2)
    if k in r_by_km:
        return r_by_km[k]
    nearest = min(r_by_km, key=lambda x: abs(x - k)) if r_by_km else None
    if nearest is not None and abs(nearest - k) < 0.8:
        return r_by_km[nearest]
    return r_last

svg_vel = line_svg(
    [p["km"] for p in vel_u],
    [p["V_mps"] for p in vel_u],
    [f"{p['km']:.0f}" for p in vel_u],
    "m/s",
    "#175cd3",
    y_max=max(5, max(p["V_mps"] for p in vel_u) * 1.15),
    val_fmt="{:.1f}",
    xlabels2=[p["hora"] for p in vel_u],
)
pico_ys = [float(p.get("h_pico_m") or 0) for p in vel_u]
hand_ys = [h_hand_m(p) for p in vel_u]
svg_tirante = line_svg(
    [p["km"] for p in vel_u],
    None,
    [f"{p['km']:.0f}" for p in vel_u],
    "m",
    y_max=max(110, max(pico_ys) * 1.08 if pico_ys else 110),
    xlabels2=[p["hora"] for p in vel_u],
    series=[
        {
            "ys": pico_ys,
            "color": "#b42318",
            "fmt": "{:.0f}",
        },
        {
            "ys": hand_ys,
            "color": "#0f766e",
            "fmt": "{:.0f}",
        },
        {
            "ys": [r_at(p) for p in vel_u],
            "color": "#7c3aed",
            "fmt": "{:.1f}",
        },
    ],
)

dev = by_id.get("devghat") or {}
bha = by_id.get("bharatpur") or {}
hep = by_id.get("devighat") or {}
sya = by_id.get("syabrubesi") or {}
rasu = by_id.get("rasuwagadhi") or {}
betw = by_id.get("betrawati") or {}
galc = by_id.get("galchhi") or {}

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
    .sw-tirante::before {{ background: #7c3aed; }}
    .sw-hand::before {{ background: #0f766e; }}
    .sw-pico::before {{ background: #b42318; }}
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
        Manning cada 1 km desde la cicatriz Langtang (08:37) hasta Bharatpur.
        n = {n_g:.2f} / {n_m:.2f} / {n_v:.3f}. Reloj: frontera 08:54, Syabrubesi 09:09,
        Betrawati 09:40, Galchhi 11:02, Devghat ~15:20 DHM. Las caídas de estación
        08:50 y 09:20 son corte de radio, no el frente. SMS 09:16. Alerta automática
        hipotética 08:38.
      </p>
    </header>

    <div class="alert">
      <strong>A las 09:16 el frente iba entre Syabrubesi y Betrawati</strong>
      <p>
        Syabrubesi {sya.get('hora_llegada', '09:09')} (ya alcanzado). Betrawati
        {betw.get('hora_llegada', '09:40')} aún no. Rasuwagadhi, Timure y la
        cicatriz no tenían margen. Aguas abajo el SMS sí llega antes
        ({hep.get('aviso_real_min', 25):.0f}–{bha.get('aviso_real_min', 0):.0f} min
        en Devighat–Bharatpur), pero se perdieron 38 min fijos respecto a una
        alerta a las 08:38 en todo lo que el agua alcanza después de las 09:16.
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
      <div class="stat"><div class="v">{km_tot:.1f} km</div><div class="l">Cicatriz → Bharatpur (Rasuwagadhi km {km_ras:.0f})</div></div>
      <div class="stat"><div class="v">{desnivel:,.0f} m</div><div class="l">Desnivel corredor ({pend:.2f} % origen)</div></div>
      <div class="stat"><div class="v">{n_g:.2f}/{n_m:.2f}/{n_v:.3f}</div><div class="l">n garganta / medio / valle · R {R1:.1f}–{R4:.1f} m</div></div>
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
          <th>Pico (m)</th><th>HAND (m)</th>
          <th>SMS 09:16</th><th>Auto 08:38</th><th>Perdidos</th>
        </tr>
      </thead>
      <tbody>
        {"".join(rows)}
      </tbody>
    </table>

    <h2>Dónde estaba el frente a cada hora</h2>
    <p class="caption">
      Eje X: hora NPT. Eje Y: km desde la cicatriz (km 0). Rasuwagadhi ~km {km_ras:.0f}
      a las 08:54. Caídas 08:50 / 09:20 = radio. Anclas de frente: 08:54, 09:09,
      09:40, 11:02 y Devghat 15:20 (DHM).
    </p>
    <div class="chart">
      <div class="legend">
        <span class="sw-danger">Frente (km desde cicatriz)</span>
      </div>
      {svg_frente}
    </div>

    <h2>Velocidad Manning por tramo (cada 10 km)</h2>
    <p class="caption">
      V = (1/n) R<sup>2/3</sup> S<sup>1/2</sup> con n variable desde Rasuwagadhi.
      Lhende (cicatriz→frontera): detritos a {v_lhende:.1f} m/s, no Manning.
      R1 = {R1:.2f} m (n={n_g:.2f}) hasta Syabrubesi,
      R2 = {R2:.2f} m (n={n_m:.2f}) hasta Betrawati, R3 = {R3:.2f} m hasta Galchhi,
      R4 = {R4:.2f} m (n={n_v:.3f}) hasta Devghat/Bharatpur.
      Picos locales son ruido del DEM, no un segundo pulso.
      Segunda fila del eje X: hora NPT de llegada del frente a ese km.
    </p>
    <div class="chart">
      <div class="legend">
        <span class="sw-info">Velocidad (m/s)</span>
      </div>
      {svg_vel}
    </div>

    <h2>Tirante hidráulico en el cauce (mismos km / horas)</h2>
    <p class="caption">
      Tres magnitudes distintas. <b>Pico</b> (80–96 m en garganta, ~9 m en Galchhi):
      tirante de cresta alineado a Geopera/DHM, no es la mancha del mapa.
      <b>HAND</b> (12→5 m, solo desde Rasuwagadhi): ocupación de valle de la mancha naranja.
      <b>R Manning</b> es el radio calibrado a tiempos, constante por tramo.
      Eje X inferior: hora NPT en la que el frente llega a ese km.
    </p>
    <div class="chart">
      <div class="legend">
        <span class="sw-pico">Tirante de pico (m)</span>
        <span class="sw-hand">Ocupación HAND de valle (m)</span>
        <span class="sw-tirante">R Manning (m)</span>
      </div>
      {svg_tirante}
    </div>

    <div class="cards">
      <div class="card">
        <h3>Zona alta: casi sin margen</h3>
        <p>
          Rasuwagadhi {rasu.get('hora_llegada', '08:54')} NPT, {rasu.get('min_desde_sismo', 17):.0f} min
          tras el colapso. Syabrubesi {sya.get('hora_llegada', '09:09')}:
          {sya.get('aviso_potencial_min', 31):.0f} min si la alerta saliera a las 08:38;
          con el SMS de las 09:16, cero. Pico ~{sya.get('h_pico_m', 40)} m; HAND 12 m.
        </p>
      </div>
      <div class="card">
        <h3>Tramo bajo: Devghat y Bharatpur</h3>
        <p>
          Galchhi {galc.get('hora_llegada', '11:02')} (~9 m DHM).
          Devghat (Chitwan) {dev.get('hora_llegada', '15:20')} NPT (ancla DHM ~15:20).
          Bharatpur {bha.get('hora_llegada', '—')} NPT, km {bha.get('km', '—')}.
          Copernicus AOI04 sigue en espera. El retraso del SMS vs 08:38 permanece
          en 38 min en todo lo que el agua alcanza después de las 09:16.
        </p>
      </div>
    </div>

    <footer>
      {man.get('fuente_dem', '')}. {man.get('nota_devighat', '')}
      {man.get('calibracion', '')} {man.get('cita_geopera', '')}
      Delineacion satelital oficial: EMSR927 GRA AOI01–03; AOI04 Bharatpur pendiente
      (Legion 29 ago). ABC Geomática Agrícola SRL, 30 ago 2026.
    </footer>
  </article>
</body>
</html>
"""

dest = here / "tiempos.html"
dest.write_text(html, encoding="utf-8")
print("wrote", dest, dest.stat().st_size)
