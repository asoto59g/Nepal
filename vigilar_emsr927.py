# -*- coding: utf-8 -*-
"""Watch Copernicus EMSR927 Rapid Mapping for new/ready products."""
from __future__ import annotations

import json
import os
import smtplib
import ssl
import sys
import urllib.request
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

HERE = Path(__file__).resolve().parent
STATE = HERE / "emsr927_watch_state.json"
REPORT = HERE / "emsr927_watch_report.md"
API = "https://rapidmapping.emergency.copernicus.eu/backend/dashboard-api/public-activations/?code=EMSR927"
PORTAL = "https://mapping.emergency.copernicus.eu/activations/EMSR927/"
STATUS = {"F": "publicado", "I": "en curso", "W": "en espera", "N": "no factible"}


def fetch():
    req = urllib.request.Request(API, headers={"User-Agent": "ABC-Geomatica-EMSR927-watch/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def snapshot(payload: dict) -> dict:
    results = payload.get("results") or []
    if not results:
        raise SystemExit("API sin resultados EMSR927")
    act = results[0]
    aois = []
    keys = []
    for aoi in act.get("aois") or []:
        products = []
        for p in aoi.get("products") or []:
            ver = (p.get("version") or {}) or {}
            sensors = []
            times = []
            for im in p.get("images") or []:
                if im.get("sensorName"):
                    sensors.append(im["sensorName"])
                if im.get("acquisitionTime"):
                    times.append(im["acquisitionTime"])
            zip_ok = bool(p.get("downloadPath"))
            item = {
                "type": p.get("type"),
                "version": ver.get("number"),
                "status": ver.get("statusCode"),
                "deliveryTime": ver.get("deliveryTime"),
                "expectedDelivery": p.get("expectedDelivery"),
                "download": zip_ok,
                "downloadPath": p.get("downloadPath") or "",
                "sensors": sensors,
                "acquisition": times,
            }
            products.append(item)
            keys.append(
                f"{aoi.get('number')}:{item['type']}:v{item['version']}:{item['status']}:"
                f"{'zip' if zip_ok else 'noz'}:{','.join(sensors)}"
            )
        aois.append({"number": aoi.get("number"), "name": aoi.get("name"), "products": products})
    keys.sort()
    return {
        "code": act.get("code"),
        "closed": bool(act.get("closed")),
        "fingerprint": "|".join(keys),
        "aois": aois,
    }


def index(state: dict) -> dict:
    out = {}
    for aoi in state.get("aois") or []:
        for p in aoi.get("products") or []:
            out[(aoi.get("number"), p.get("type"))] = (aoi, p)
    return out


def diff(old: dict | None, new: dict) -> list[str]:
    if old is None:
        return []
    changes = []
    if bool(old.get("closed")) != bool(new.get("closed")):
        changes.append("La activacion se cerro." if new.get("closed") else "La activacion se reabrio.")
    prev = index(old)
    cur = index(new)
    for key, (aoi, p) in cur.items():
        label = f"AOI{int(aoi['number']):02d} {aoi['name']} {p.get('type')} v{p.get('version')}"
        st = STATUS.get(p.get("status") or "", p.get("status"))
        if key not in prev:
            changes.append(f"Producto nuevo: {label} ({st}).")
            continue
        old_p = prev[key][1]
        if old_p.get("status") != p.get("status"):
            changes.append(
                f"Estado: {label} paso de {STATUS.get(old_p.get('status') or '', old_p.get('status'))} a {st}."
            )
        if old_p.get("version") != p.get("version"):
            changes.append(f"Version nueva: {label} (antes v{old_p.get('version')}).")
        if (not old_p.get("download")) and p.get("download"):
            changes.append(f"Ya hay zip GRA: {label} — {p.get('downloadPath')}")
        if old_p.get("sensors") != p.get("sensors") or old_p.get("acquisition") != p.get("acquisition"):
            changes.append(f"Imagen/sensor actualizado: {label} ({', '.join(p.get('sensors') or [])}).")
    for key, (aoi, p) in prev.items():
        if key not in cur:
            changes.append(f"Desaparecio: AOI{int(aoi['number']):02d} {aoi['name']} {p.get('type')}")
    return changes


def table(state: dict) -> str:
    lines = ["| AOI | Sitio | Producto | Estado | Zip | Sensor |", "| --- | --- | --- | --- | --- | --- |"]
    for aoi in state.get("aois") or []:
        for p in aoi.get("products") or []:
            st = STATUS.get(p.get("status") or "", p.get("status") or "—")
            lines.append(
                f"| {int(aoi['number']):02d} | {aoi['name']} | {p.get('type')} v{p.get('version')} | "
                f"{st} | {'si' if p.get('download') else 'no'} | {', '.join(p.get('sensors') or ['—'])} |"
            )
    return "\n".join(lines)


def report_md(changes: list[str], new: dict) -> str:
    body = [
        "## EMSR927 — cambio detectado",
        "",
        f"Portal: {PORTAL}",
        f"API: {API}",
        "",
    ]
    if changes:
        body.append("**Que cambio**")
        body.extend(f"- {c}" for c in changes)
        body.append("")
    body.append("**Estado actual**")
    body.append("")
    body.append(table(new))
    body.extend(
        [
            "",
            "Cuando un AOI pase a **publicado** y tenga zip, bajar el GRA, copiar vectores y mapas, y regenerar:",
            "",
            "1. `python preparar_emsr927.py`",
            "2. `python escribir_mapa_html.py`",
            "",
            "Sitio: https://asoto59g.github.io/Nepal/",
        ]
    )
    return "\n".join(body) + "\n"


def send_mail(subject: str, body: str) -> bool:
    host = os.environ.get("SMTP_SERVER", "").strip()
    user = os.environ.get("SMTP_USER", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "").strip()
    to = os.environ.get("MAIL_TO", "").strip()
    mail_from = os.environ.get("MAIL_FROM", "").strip() or user
    if not (host and user and password and to):
        print("correo omitido: faltan SMTP_SERVER, SMTP_USER, SMTP_PASSWORD o MAIL_TO")
        return False
    port = int(os.environ.get("SMTP_PORT") or "465")
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = mail_from
    msg["To"] = to
    msg.attach(MIMEText(body, "plain", "utf-8"))
    ctx = ssl.create_default_context()
    if port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=30, context=ctx) as smtp:
            smtp.login(user, password)
            smtp.sendmail(mail_from, [to], msg.as_string())
    else:
        with smtplib.SMTP(host, port, timeout=30) as smtp:
            smtp.starttls(context=ctx)
            smtp.login(user, password)
            smtp.sendmail(mail_from, [to], msg.as_string())
    print("correo enviado a", to)
    return True


def write_output(changed: bool, title: str):
    dest = os.environ.get("GITHUB_OUTPUT")
    if not dest:
        return
    with open(dest, "a", encoding="utf-8") as f:
        f.write(f"changed={'true' if changed else 'false'}\n")
        f.write(f"title={title}\n")


def main():
    new = snapshot(fetch())
    old = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else None
    changes = diff(old, new)
    first = old is None
    changed = (not first) and bool(changes) and (old or {}).get("fingerprint") != new.get("fingerprint")
    title = "EMSR927: " + (changes[0] if changes else "sin cambios")
    if len(title) > 90:
        title = title[:87] + "..."
    md = report_md(changes, new)
    REPORT.write_text(md, encoding="utf-8")
    STATE.write_text(json.dumps(new, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("fingerprint", new["fingerprint"])
    print("changed", changed, "first", first)
    for c in changes:
        print("-", c)
    write_output(changed, title)
    if changed:
        try:
            send_mail(title, md)
        except Exception as exc:
            print("correo fallo:", exc)
    return 0


if __name__ == "__main__":
    sys.exit(main())
