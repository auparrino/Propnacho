from __future__ import annotations

import logging
from typing import Optional

from .common import Propiedad, sin_tildes

log = logging.getLogger(__name__)


def cotizacion_dolar(valor) -> Optional[float]:
    if isinstance(valor, (int, float)) and valor > 0:
        return float(valor)
    try:
        import requests

        r = requests.get("https://dolarapi.com/v1/dolares/oficial", timeout=15)
        v = float(r.json()["venta"])
        log.info("Dólar oficial (dolarapi.com): %.2f", v)
        return v
    except Exception as e:
        log.warning("No pude obtener la cotización del dólar (%s)", e)
        return None


def precio_en(p: Propiedad, moneda: str, dolar: Optional[float]) -> Optional[float]:
    if p.precio is None:
        return None
    if p.moneda == moneda or p.moneda is None:
        return p.precio
    if not dolar:
        return None
    return p.precio / dolar if moneda == "USD" else p.precio * dolar


def motivo_descarte(p: Propiedad, b: dict, dolar: Optional[float]) -> Optional[str]:
    """Devuelve el motivo por el que NO cumple los parámetros (o None si cumple).
    Los datos que faltan en el aviso no descartan (mejor ver de más que perderse algo)."""
    moneda = (b.get("moneda") or "USD").upper()
    pr = precio_en(p, moneda, dolar)
    pmin, pmax = b.get("precio_min") or 0, b.get("precio_max") or 0
    if pr is not None:
        if pmin and pr < pmin:
            return "precio bajo"
        if pmax and pr > pmax:
            return "precio alto"
    elif p.precio is not None and p.moneda != moneda:
        return "moneda distinta sin cotización"

    amin, amax = b.get("ambientes_min") or 0, b.get("ambientes_max") or 0
    if p.ambientes is not None:
        if amin and p.ambientes < amin:
            return "pocos ambientes"
        if amax and p.ambientes > amax:
            return "muchos ambientes"

    mmin, mmax = b.get("m2_min") or 0, b.get("m2_max") or 0
    if p.m2 is not None:
        if mmin and p.m2 < mmin:
            return "pocos m2"
        if mmax and p.m2 > mmax:
            return "muchos m2"

    emax = b.get("expensas_max") or 0
    if emax and p.expensas is not None and p.expensas > emax:
        return "expensas altas"

    texto = sin_tildes((p.titulo + " " + p.texto).lower())
    for palabra in b.get("palabras_excluidas") or []:
        if palabra and sin_tildes(str(palabra).lower()) in texto:
            return f"contiene '{palabra}'"
    return None
