from __future__ import annotations

import re

from bs4 import BeautifulSoup

from ..common import Propiedad, primera_imagen, limpiar, parse_expensas, parse_features, parse_precio, slug
from .base import Busqueda, Fuente

BASE = "https://www.argenprop.com"
TIPOS = {"departamento": "departamentos", "ph": "ph", "casa": "casas"}


def _zona(z) -> tuple[str, str]:
    if isinstance(z, dict):
        nombre = z.get("nombre", "")
        return nombre, slug(z.get("argenprop") or nombre)
    return z, slug(z)


def _pagina(url: str, n: int) -> str:
    if n == 1:
        return url
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}pagina-{n}"


class Argenprop(Fuente):
    nombre = "argenprop"
    dominio = "argenprop.com"

    def busquedas(self, cfg: dict) -> list[Busqueda]:
        b = cfg["busqueda"]
        op = "alquiler" if b.get("operacion") == "alquiler" else "venta"
        pmin, pmax = int(b.get("precio_min") or 0), int(b.get("precio_max") or 0)
        mon = "dolares" if b.get("moneda", "USD").upper() == "USD" else "pesos"
        if pmin or pmax:
            precio = f"{mon}-{pmin or 0}-{pmax or 999999999}"
        else:
            precio = ""
        out = []
        for tipo in b.get("tipos") or ["departamento"]:
            t = TIPOS.get(slug(tipo), slug(tipo))
            for z in b.get("zonas") or ["capital-federal"]:
                nombre, zs = _zona(z)
                base_sin = f"{BASE}/{t}/{op}/{zs}"
                base_con = f"{base_sin}/{precio}" if precio else base_sin
                alt = (
                    Busqueda(lambda n, u=base_sin: _pagina(u, n), nombre, tipo)
                    if precio
                    else None
                )
                out.append(
                    Busqueda(lambda n, u=base_con: _pagina(u, n), nombre, tipo, alternativa=alt)
                )
        return out

    def paginar_url_extra(self, url):
        base = re.sub(r"[?&]pagina-\d+", "", url)
        return lambda n: _pagina(base, n)

    def parse_listado(self, html: str) -> list[Propiedad]:
        soup = BeautifulSoup(html, "lxml")
        cards = soup.select(".listing__item") or soup.select("a.card")
        out, vistos = [], set()
        for c in cards:
            a = c if c.name == "a" else (c.select_one("a.card") or c.select_one("a[href]"))
            if not a or not a.get("href"):
                continue
            href = a["href"]
            url = href if href.startswith("http") else BASE + href
            m = re.search(r"--(\d{5,})", url)
            pid = (
                a.get("data-item-card")
                or c.get("data-item-card")
                or (m.group(1) if m else url.split("?")[0])
            )
            if pid in vistos:
                continue
            vistos.add(pid)

            def q(*sels):
                for s in sels:
                    el = c.select_one(s)
                    if el:
                        return limpiar(el.get_text(" "))
                return ""

            texto = limpiar(c.get_text(" "))
            p = Propiedad(fuente=self.nombre, id=str(pid), url=url.split("?")[0])
            precio_txt = q(".card__price", '[class*="price"]')
            p.precio, p.moneda = parse_precio(precio_txt or texto)
            p.expensas = parse_expensas(q(".card__expenses") or texto)
            p.direccion = q(".card__address", '[class*="address"]')
            p.titulo = q(".card__title--primary", ".card__title", "h2", "h3")[:160]
            feats = q(".card__main-features", '[class*="features"]')
            parse_features(feats + " " + texto, p)
            p.texto = texto
            p.imagen = primera_imagen(c)
            out.append(p)
        return out
