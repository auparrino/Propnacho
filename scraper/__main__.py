"""Uso:  python -m scraper  [--config config.yml]"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timedelta

import yaml

from . import salida
from .common import detectar_apto_credito
from .fetch import Bloqueado, Fetcher
from .filtros import cotizacion_dolar, motivo_descarte, precio_en
from .sources import FUENTES

log = logging.getLogger("propnacho")


def recorrer(fuente, cfg, fetcher) -> list:
    av = cfg.get("avanzado") or {}
    pmax = (av.get("paginas_max") or {}).get(fuente.nombre, 5)
    encontrados: dict = {}
    for bq in fuente.busquedas(cfg) + fuente.busquedas_extra(cfg):
        actual, n = bq, 1
        while n <= pmax:
            url = actual.url_pagina(n)
            if not url:
                break
            log.info("[%s] %s", fuente.nombre, url)
            html = fetcher.get(url, fuente.dominio)
            props = fuente.parse_listado(html) if html else []
            if n == 1 and not props:
                fetcher.guardar_debug(f"{fuente.nombre}-sin-resultados-{len(encontrados)}", html)
                if actual.alternativa:
                    log.info("  0 resultados: pruebo URL sin filtro de precio")
                    actual = actual.alternativa
                    continue
                log.info("  0 resultados")
                break
            nuevos = 0
            for p in props:
                if p.clave in encontrados:
                    continue
                nuevos += 1
                p.zona, p.tipo = actual.zona, actual.tipo
                if actual.filtro_apto_en_url:
                    p.apto_credito, p.apto_credito_origen = True, "filtro del portal"
                encontrados[p.clave] = p
            log.info("  %d avisos (%d nuevos)", len(props), nuevos)
            if not nuevos:
                break
            n += 1
    return list(encontrados.values())


def chequear_apto(props, fuente, cfg, fetcher, presupuesto: list) -> list:
    b, av = cfg["busqueda"], cfg.get("avanzado") or {}
    solo = bool(b.get("solo_apto_credito"))
    verificar = av.get("verificar_en_ficha", True)
    out = []
    for p in props:
        if p.apto_credito is None:
            p.apto_credito = detectar_apto_credito(p.titulo + " " + p.texto)
            if p.apto_credito is not None:
                p.apto_credito_origen = "listado"
        if p.apto_credito is None and solo and verificar and presupuesto[0] > 0:
            presupuesto[0] -= 1
            try:
                html = fetcher.get(p.url, fuente.dominio)
                p.apto_credito = detectar_apto_credito(fuente.texto_ficha(html)) or False
                p.apto_credito_origen = "ficha"
            except Exception as e:
                log.info("  no pude abrir la ficha %s (%s)", p.url, e)
        if not solo or p.apto_credito:
            out.append(p)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yml")
    ap.add_argument("--sin-navegador", action="store_true", help="no usar Chromium como fallback")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")

    with open(args.config, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    b, av = cfg["busqueda"], cfg.get("avanzado") or {}
    dolar = cotizacion_dolar(av.get("cotizacion_dolar", "auto"))

    fetcher = Fetcher(espera=float(av.get("espera_segundos", 3)), usar_navegador=not args.sin_navegador)
    presupuesto = [int(av.get("max_fichas_a_verificar", 200))]
    resultados, resumen, fallas, activas = [], {}, 0, 0
    try:
        for nombre, fuente in FUENTES.items():
            if not (cfg.get("fuentes") or {}).get(nombre, True):
                continue
            activas += 1
            log.info("===== %s =====", nombre.upper())
            try:
                crudos = recorrer(fuente, cfg, fetcher)
            except Bloqueado as e:
                log.error("%s bloqueó el acceso (%s). Se reintenta en la próxima corrida.", nombre, e)
                resumen[nombre] = "⚠️ bloqueado"
                fallas += 1
                continue
            except Exception as e:
                log.exception("Error en %s: %s", nombre, e)
                resumen[nombre] = "⚠️ error"
                fallas += 1
                continue
            candidatos = []
            for p in crudos:
                m = motivo_descarte(p, b, dolar)
                if m is None:
                    candidatos.append(p)
            log.info("%s: %d avisos, %d cumplen filtros, verificando apto crédito...",
                     nombre, len(crudos), len(candidatos))
            finales = chequear_apto(candidatos, fuente, cfg, fetcher, presupuesto)
            log.info("%s: %d apto crédito", nombre, len(finales))
            resumen[nombre] = len(finales)
            resultados += finales
    finally:
        fetcher.cerrar()

    historial = salida.cargar_historial()
    salida.marcar_nuevas(resultados, historial)
    limite = (datetime.now() - timedelta(days=120)).strftime("%Y-%m-%d")
    historial = {k: v for k, v in historial.items() if v.get("ultima_vez", "9") >= limite}

    moneda = (b.get("moneda") or "USD").upper()
    resultados.sort(key=lambda p: (not p.nueva, precio_en(p, moneda, dolar) or 9e15))
    salida.escribir(resultados, cfg, resumen, dolar)
    salida.guardar_historial(historial)
    salida.telegram(resultados, cfg)
    log.info("LISTO: %d propiedades (%d nuevas). Ver resultados/index.html",
             len(resultados), sum(p.nueva for p in resultados))
    return 1 if activas and fallas == activas else 0


if __name__ == "__main__":
    sys.exit(main())
