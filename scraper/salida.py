from __future__ import annotations

import csv
import json
import logging
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

from .common import Propiedad

log = logging.getLogger(__name__)

DIR = Path("resultados")
HISTORIAL = DIR / "historial.json"
ART = timezone(timedelta(hours=-3))

COLUMNAS = [
    "nueva", "fuente", "id", "precio", "moneda", "ambientes", "dormitorios", "banos", "m2",
    "expensas", "zona", "tipo", "direccion", "titulo", "apto_credito_origen",
    "primera_vez", "url",
]


def ahora() -> str:
    return datetime.now(ART).strftime("%Y-%m-%d %H:%M")


def cargar_historial() -> dict:
    if HISTORIAL.exists():
        try:
            return json.loads(HISTORIAL.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def marcar_nuevas(props: list[Propiedad], historial: dict) -> None:
    hoy = ahora()
    for p in props:
        h = historial.get(p.clave)
        if h is None:
            p.nueva = True
            p.primera_vez = hoy
            historial[p.clave] = {"primera_vez": hoy, "precio": p.precio, "url": p.url}
        else:
            p.primera_vez = h.get("primera_vez", "")
            if h.get("precio") and p.precio and p.precio < h["precio"]:
                p.extra["bajo_precio_desde"] = h["precio"]
            h["precio"] = p.precio
        historial[p.clave]["ultima_vez"] = hoy


def _fmt_num(v, dec=0) -> str:
    if v is None:
        return "-"
    return f"{v:,.{dec}f}".replace(",", ".")


def _precio(p: Propiedad) -> str:
    if p.precio is None:
        return "Consultar"
    s = f"{'US$' if p.moneda == 'USD' else '$'} {_fmt_num(p.precio)}"
    if p.extra.get("bajo_precio_desde"):
        s += f" ⬇️ (antes {_fmt_num(p.extra['bajo_precio_desde'])})"
    return s


def escribir(props: list[Propiedad], cfg: dict, resumen: dict) -> None:
    DIR.mkdir(exist_ok=True)
    # CSV (se abre directo en Excel / Google Sheets)
    with open(DIR / "propiedades.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNAS, extrasaction="ignore")
        w.writeheader()
        for p in props:
            row = p.to_row()
            row["nueva"] = "SI" if p.nueva else ""
            w.writerow(row)

    # Markdown: GitHub lo muestra como tabla linda
    b = cfg["busqueda"]
    nuevas = sum(p.nueva for p in props)
    lineas = [
        "# 🏠 Propiedades apto crédito" if b.get("solo_apto_credito") else "# 🏠 Propiedades",
        "",
        f"**Última búsqueda:** {ahora()} (hora Argentina) · "
        f"**{len(props)} propiedades** · **{nuevas} nuevas** 🆕",
        "",
        f"Filtros: {', '.join(b.get('tipos') or [])} · "
        f"{', '.join(z if isinstance(z, str) else z.get('nombre', '') for z in b.get('zonas') or [])} · "
        f"{b.get('moneda', 'USD')} {_fmt_num(b.get('precio_min') or 0)} a {_fmt_num(b.get('precio_max') or 0)} · "
        f"{b.get('ambientes_min') or '-'} a {b.get('ambientes_max') or '-'} amb · "
        f"desde {b.get('m2_min') or 0} m²",
        "",
        "Por portal: " + " · ".join(f"{k}: {v}" for k, v in resumen.items()),
        "",
        "📥 [Descargar planilla CSV](propiedades.csv) (se abre con Excel / Google Sheets)",
        "",
        "| | Precio | Amb | m² | Expensas | Zona | Dirección / Título | Portal |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for p in props:
        desc = (p.direccion or p.titulo or "ver aviso").replace("|", "/")
        if p.direccion and p.titulo:
            desc += f"<br><sub>{p.titulo[:90].replace('|', '/')}</sub>"
        lineas.append(
            f"| {'🆕' if p.nueva else ''} | {_precio(p)} | {p.ambientes or '-'} | "
            f"{_fmt_num(p.m2)} | {('$ ' + _fmt_num(p.expensas)) if p.expensas else '-'} | "
            f"{p.zona} | [{desc}]({p.url}) | {p.fuente} |"
        )
    if not props:
        lineas.append("| | _Sin resultados con estos filtros_ | | | | | | |")
    (DIR / "README.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")


def guardar_historial(historial: dict) -> None:
    DIR.mkdir(exist_ok=True)
    HISTORIAL.write_text(json.dumps(historial, ensure_ascii=False, indent=1), encoding="utf-8")


# --- Telegram ------------------------------------------------------------
def telegram(props: list[Propiedad], cfg: dict) -> None:
    n = cfg.get("notificaciones") or {}
    if not n.get("telegram"):
        return
    token, chat = os.getenv("TELEGRAM_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat:
        log.warning("Telegram activado pero faltan los secrets TELEGRAM_TOKEN / TELEGRAM_CHAT_ID")
        return
    import requests

    lista = [p for p in props if p.nueva] if n.get("solo_nuevas", True) else props
    if not lista:
        return
    msgs, actual = [], f"🏠 {len(lista)} propiedades {'nuevas ' if n.get('solo_nuevas', True) else ''}apto crédito\n\n"
    for p in lista[:60]:
        item = (
            f"• {_precio(p)} · {p.ambientes or '?'} amb · {_fmt_num(p.m2)} m² · {p.zona}\n"
            f"  {(p.direccion or p.titulo)[:80]}\n  {p.url}\n\n"
        )
        if len(actual) + len(item) > 3800:
            msgs.append(actual)
            actual = ""
        actual += item
    if len(lista) > 60:
        actual += f"... y {len(lista) - 60} más (ver el repo)"
    msgs.append(actual)
    for m in msgs:
        try:
            requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                data={"chat_id": chat, "text": m, "disable_web_page_preview": "true"},
                timeout=20,
            )
        except Exception as e:
            log.warning("Error enviando Telegram: %s", e)
