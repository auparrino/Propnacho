"""Modelo de datos y utilidades de parseo compartidas por todos los portales."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class Propiedad:
    fuente: str
    id: str
    url: str
    titulo: str = ""
    precio: Optional[float] = None
    moneda: Optional[str] = None  # "USD" | "ARS"
    expensas: Optional[float] = None  # en ARS
    ambientes: Optional[int] = None
    dormitorios: Optional[int] = None
    banos: Optional[int] = None
    m2: Optional[float] = None
    direccion: str = ""
    zona: str = ""
    tipo: str = ""
    texto: str = ""  # texto libre de la tarjeta (para filtros), no se exporta
    apto_credito: Optional[bool] = None
    apto_credito_origen: str = ""  # "filtro del portal" | "listado" | "ficha"
    nueva: bool = False
    primera_vez: str = ""
    extra: dict = field(default_factory=dict)

    @property
    def clave(self) -> str:
        return f"{self.fuente}:{self.id}"

    def to_row(self) -> dict:
        d = asdict(self)
        d.pop("texto", None)
        d.pop("extra", None)
        return d


def limpiar(txt: str | None) -> str:
    return re.sub(r"\s+", " ", txt or "").strip()


def sin_tildes(txt: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", txt) if unicodedata.category(c) != "Mn")


def slug(txt: str) -> str:
    t = sin_tildes(txt.lower().strip())
    t = re.sub(r"[^a-z0-9/]+", "-", t)
    return t.strip("-")


def _num(s: str) -> Optional[float]:
    """'120.000' -> 120000 ; '1.250,5' -> 1250.5 ; '65,5' -> 65.5"""
    s = s.strip()
    if not s:
        return None
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        partes = s.split(",")
        s = s.replace(",", ".") if len(partes[-1]) != 3 else s.replace(",", "")
    elif "." in s:
        partes = s.split(".")
        if len(partes) > 2 or len(partes[-1]) == 3:
            s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return None


_RE_PRECIO = re.compile(r"(U\$S|US\$|USD|U\$D|u\$s|\$)\s*([\d.,]+)", re.I)


def parse_precio(txt: str | None) -> tuple[Optional[float], Optional[str]]:
    if not txt:
        return None, None
    m = _RE_PRECIO.search(txt)
    if not m:
        return None, None
    simbolo = m.group(1).upper()
    moneda = "ARS" if simbolo == "$" else "USD"
    return _num(m.group(2)), moneda


_RE_EXPENSAS = [
    re.compile(r"\$\s*([\d.,]+)\s*(?:de\s*)?expensas", re.I),
    re.compile(r"expensas?\s*:?\s*\$\s*([\d.,]+)", re.I),
]


def parse_expensas(txt: str | None) -> Optional[float]:
    if not txt:
        return None
    for r in _RE_EXPENSAS:
        m = r.search(txt)
        if m:
            return _num(m.group(1))
    return None


_RE_M2 = re.compile(r"([\d.,]+)\s*m(?:²|2|ts2?|etros cuadrados)\b\.?\s*(tot|cub)?", re.I)
_RE_AMB = re.compile(r"(\d+)\s*amb", re.I)
_RE_MONO = re.compile(r"monoambiente", re.I)
_RE_DORM = re.compile(r"(\d+)\s*(?:dorm|habitaci|recámara|recamara)", re.I)
_RE_BANO = re.compile(r"(\d+)\s*bañ", re.I)


def parse_features(txt: str, p: Propiedad) -> None:
    """Completa m2/ambientes/dormitorios/baños a partir de texto libre."""
    txt = txt or ""
    if p.m2 is None:
        valores = {}
        for m in _RE_M2.finditer(txt):
            v = _num(m.group(1))
            if v and 8 <= v <= 5000:
                valores.setdefault((m.group(2) or "x").lower(), v)
        p.m2 = valores.get("tot") or valores.get("x") or valores.get("cub")
    if p.ambientes is None:
        m = _RE_AMB.search(txt)
        if m:
            p.ambientes = int(m.group(1))
        elif _RE_MONO.search(txt):
            p.ambientes = 1
    if p.dormitorios is None:
        m = _RE_DORM.search(txt)
        if m:
            p.dormitorios = int(m.group(1))
    if p.banos is None:
        m = _RE_BANO.search(txt)
        if m:
            p.banos = int(m.group(1))
    if p.ambientes is None and p.dormitorios is not None:
        p.ambientes = p.dormitorios + 1


# --- Apto crédito -------------------------------------------------------
_RE_NO_APTO = re.compile(
    r"no\s+(?:es\s+)?apt[oa]s?\s*(?:a\s+|para\s+)?(?:cr[eé]dito|banco|hipotec)", re.I
)
_RE_APTO = re.compile(
    r"apt[oa]s?\s*(?:a\s+|para\s+|al\s+)?(?:cr[eé]dito|credito|banco|hipotec)"
    r"|acepta\s+cr[eé]dito|cr[eé]dito\s+hipotecario\s*:?\s*s[ií]"
    r"|apto[_\s-]*credito",
    re.I,
)


def detectar_apto_credito(txt: str | None) -> Optional[bool]:
    """True si el texto dice apto crédito, False si dice NO apto, None si no dice nada."""
    if not txt:
        return None
    if _RE_NO_APTO.search(txt):
        return False
    if _RE_APTO.search(txt):
        return True
    return None
