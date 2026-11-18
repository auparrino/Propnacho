from __future__ import annotations

import re

from bs4 import BeautifulSoup

from ..common import Propiedad, primera_imagen, limpiar, parse_expensas, parse_features, parse_precio, slug
from .base import Busqueda, Fuente

BASE = "https://inmuebles.mercadolibre.com.ar"
TIPOS = {"departamento": "departamentos", "ph": "ph", "casa": "casas"}
POR_PAGINA = 48
TEXTO_BUSQUEDA = "apto credito"


def _zona(z) -> tuple[str, str]:
    """MercadoLibre usa provincia/barrio. Sin provincia asumimos CABA."""
    if isinstance(z, dict):
        nombre = z.get("nombre", "")
        ubic = z.get("mercadolibre") or nombre
    else:
        nombre = ubic = z
    ubic = slug(ubic)
    if ubic in ("capital-federal", "caba"):
        return nombre, "capital-federal"
    if "/" not in ubic:
        ubic = f"capital-federal/{ubic}"
    return nombre, ubic


def _pagina(base: str, filtros: str, n: int) -> str:
    desde = "" if n == 1 else f"_Desde_{(n - 1) * POR_PAGINA + 1}"
    return f"{base}{desde}{filtros}_NoIndex_True"


class MercadoLibre(Fuente):
    nombre = "mercadolibre"
    dominio = "mercadolibre.com.ar"

    def busquedas(self, cfg: dict) -> list[Busqueda]:
        b = cfg["busqueda"]
        op = "alquiler" if b.get("operacion") == "alquiler" else "venta"
        mon = "USD" if b.get("moneda", "USD").upper() == "USD" else "ARS"
        pmin, pmax = int(b.get("precio_min") or 0), int(b.get("precio_max") or 0)
        filtros = f"_PriceRange_{pmin}{mon}-{pmax or 999999999}{mon}" if (pmin or pmax) else ""
        texto = slug(TEXTO_BUSQUEDA) if b.get("solo_apto_credito") else ""
        out = []
        for tipo in b.get("tipos") or ["departamento"]:
            t = TIPOS.get(slug(tipo), slug(tipo))
            for z in b.get("zonas") or ["capital-federal"]:
                nombre, ubic = _zona(z)
                base = f"{BASE}/{t}/{op}/{ubic}/" + (texto or "")
                out.append(
                    Busqueda(
                        lambda n, b_=base, f=filtros: _pagina(b_, f, n),
                        nombre,
                        tipo,
                        alternativa=Busqueda(lambda n, b_=base: _pagina(b_, "", n), nombre, tipo)
                        if filtros
                        else None,
                    )
                )
        return out

    def paginar_url_extra(self, url):
        base = re.sub(r"_Desde_\d+", "", url.split("#")[0])
        def f(n):
            if n == 1:
                return url
            m = re.search(r"(_[A-Z][A-Za-z]+_|$)", base.rsplit("/", 1)[-1])
            head, tail = base.rsplit("/", 1)
            idx = m.start() if m else len(tail)
            return f"{head}/{tail[:idx]}_Desde_{(n - 1) * POR_PAGINA + 1}{tail[idx:]}"
        return f

    def parse_listado(self, html: str) -> list[Propiedad]:
        soup = BeautifulSoup(html, "lxml")
        cards = (
            soup.select("li.ui-search-layout__item")
            or soup.select("div.poly-card")
            or soup.select("div.ui-search-result__wrapper")
        )
        out, vistos = [], set()
        for c in cards:
            a = (
                c.select_one("a.poly-component__title")
                or c.select_one("h3 a[href]")
                or c.select_one('a[href*="MLA"]')
                or c.select_one("a[href]")
            )
            if not a:
                continue
            url = a["href"].split("#")[0]
            m = re.search(r"MLA-?(\d+)", url)
            pid = f"MLA{m.group(1)}" if m else url.split("?")[0]
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
            p = Propiedad(fuente=self.nombre, id=pid, url=url.split("?")[0])
            p.titulo = (
                q(".poly-component__title", ".ui-search-item__title", "h2", "h3")
                or limpiar(a.get_text(" "))
            )[:160]
            sym = q(".andes-money-amount__currency-symbol")
            frac = q(".andes-money-amount__fraction")
            if frac:
                p.precio, p.moneda = parse_precio(f"{'$' if sym.strip() == '$' else 'USD'} {frac}")
            else:
                p.precio, p.moneda = parse_precio(texto)
            p.expensas = parse_expensas(texto)
            p.direccion = q(".poly-component__location", ".ui-search-item__location")
            attrs = " ".join(
                limpiar(li.get_text(" "))
                for li in c.select(
                    ".poly-attributes_list__item, .poly-attributes-list__item, "
                    ".ui-search-card-attributes__attribute"
                )
            )
            for fuente_txt in (attrs, p.titulo, texto):  # de más a menos confiable
                parse_features(fuente_txt, p)
            p.texto = texto
            p.imagen = primera_imagen(c)
            out.append(p)
        return out
