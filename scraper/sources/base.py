from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from bs4 import BeautifulSoup

from ..common import Propiedad, limpiar


@dataclass
class Busqueda:
    """Una búsqueda paginada en un portal."""

    url_pagina: Callable[[int], str]  # n de página (1..N) -> URL
    zona: str
    tipo: str
    filtro_apto_en_url: bool = False  # el portal ya filtró apto crédito
    alternativa: Optional["Busqueda"] = None  # si la 1a página no da nada, probar esta


class Fuente:
    nombre = "base"
    dominio = ""

    def busquedas(self, cfg: dict) -> list[Busqueda]:
        raise NotImplementedError

    def parse_listado(self, html: str) -> list[Propiedad]:
        raise NotImplementedError

    def texto_ficha(self, html: str) -> str:
        """Texto completo de la ficha del aviso, para buscar 'apto crédito'."""
        soup = BeautifulSoup(html, "lxml")
        for t in soup(["script", "style", "noscript", "svg"]):
            # dejamos JSON embebido: muchos portales ponen ahí las características
            if t.name == "script" and t.get("type") in ("application/ld+json", "application/json"):
                continue
            t.decompose()
        return limpiar(soup.get_text(" "))

    def busquedas_extra(self, cfg: dict) -> list[Busqueda]:
        urls = ((cfg.get("avanzado") or {}).get("urls_extra") or {}).get(self.nombre) or []
        return [
            Busqueda(url_pagina=self.paginar_url_extra(u), zona="(url extra)", tipo="")
            for u in urls
            if u
        ]

    def paginar_url_extra(self, url: str) -> Callable[[int], str]:
        return lambda n, u=url: u if n == 1 else None  # por defecto sólo 1 página
