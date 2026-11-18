from __future__ import annotations

import re

from bs4 import BeautifulSoup

from ..common import Propiedad, primera_imagen, limpiar, parse_expensas, parse_features, parse_precio, slug
from .base import Busqueda, Fuente

BASE = "https://www.zonaprop.com.ar"
TIPOS = {"departamento": "departamentos", "ph": "ph", "casa": "casas"}
OPERACIONES = {"venta": "venta", "alquiler": "alquiler"}


def _zona(z) -> tuple[str, str]:
    if isinstance(z, dict):
        nombre = z.get("nombre", "")
        return nombre, slug(z.get("zonaprop") or nombre)
    return z, slug(z)


class Zonaprop(Fuente):
    nombre = "zonaprop"
    dominio = "zonaprop.com.ar"

    def busquedas(self, cfg: dict) -> list[Busqueda]:
        b = cfg["busqueda"]
        op = OPERACIONES.get(b.get("operacion", "venta"), "venta")
        apto = bool(b.get("solo_apto_credito"))
        moneda = "dolar" if b.get("moneda", "USD").upper() == "USD" else "pesos"
        pmin, pmax = int(b.get("precio_min") or 0), int(b.get("precio_max") or 0)
        if pmin and pmax:
            precio = f"{pmin}-{pmax}-{moneda}"
        elif pmax:
            precio = f"menos-{pmax}-{moneda}"
        elif pmin:
            precio = f"mas-de-{pmin}-{moneda}"
        else:
            precio = ""

        out = []
        for tipo in b.get("tipos") or ["departamento"]:
            t = TIPOS.get(slug(tipo), slug(tipo))
            for z in b.get("zonas") or ["capital-federal"]:
                nombre, zs = _zona(z)
                partes = [t, op, zs] + (["con-apto-credito"] if apto else [])

                def mk(extra, partes=partes):
                    base = "-".join(partes + ([extra] if extra else []))
                    return lambda n: f"{BASE}/{base}{'' if n == 1 else f'-pagina-{n}'}.html"

                alt = Busqueda(mk(""), nombre, tipo, apto) if precio else None
                out.append(Busqueda(mk(precio), nombre, tipo, apto, alternativa=alt))
        return out

    def paginar_url_extra(self, url):
        base = re.sub(r"(-pagina-\d+)?\.html.*$", "", url)
        return lambda n: url if n == 1 else f"{base}-pagina-{n}.html"

    def parse_listado(self, html: str) -> list[Propiedad]:
        soup = BeautifulSoup(html, "lxml")
        cards = soup.select("[data-to-posting]") or soup.select('[data-qa^="posting"]')
        out, vistos = [], set()
        for c in cards:
            href = c.get("data-to-posting")
            if not href:
                a = c.select_one('a[href*="/propiedades/"]')
                href = a and a.get("href")
            if not href:
                continue
            url = href if href.startswith("http") else BASE + href
            m = re.search(r"-(\d{6,})\.html", url)
            pid = c.get("data-id") or (m.group(1) if m else url)
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
            p.precio, p.moneda = parse_precio(
                q('[data-qa="POSTING_CARD_PRICE"]', '[class*="price"]') or texto
            )
            p.expensas = parse_expensas(
                q('[data-qa="expensas"]', '[class*="expenses"]') or texto
            )
            p.direccion = ", ".join(
                x
                for x in (
                    q('[class*="location-address"]', '[class*="postingAddress"]'),
                    q('[data-qa="POSTING_CARD_LOCATION"]', '[class*="location-block"]'),
                )
                if x
            )
            p.titulo = q(
                '[data-qa="POSTING_CARD_DESCRIPTION"] a', 'h3', 'h2',
                '[data-qa="POSTING_CARD_DESCRIPTION"]',
            )[:160]
            feats = q('[data-qa="POSTING_CARD_FEATURES"]', '[class*="main-features"]')
            parse_features(feats or texto, p)
            p.texto = texto
            p.imagen = primera_imagen(c)
            out.append(p)
        return out
