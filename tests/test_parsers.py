from pathlib import Path

from scraper.common import detectar_apto_credito, parse_precio
from scraper.sources import FUENTES

FIX = Path(__file__).parent / "fixtures"


def leer(n):
    return (FIX / f"{n}.html").read_text(encoding="utf-8")


def test_apto():
    assert detectar_apto_credito("Departamento APTO CRÉDITO hipotecario")
    assert detectar_apto_credito("apto credito") is True
    assert detectar_apto_credito("Apta crédito bancario") is True
    assert detectar_apto_credito("NO apto crédito") is False
    assert detectar_apto_credito("lindo depto") is None


def test_precio():
    assert parse_precio("USD 128.000") == (128000, "USD")
    assert parse_precio("U$S 99.500") == (99500, "USD")
    assert parse_precio("$ 95.000.000") == (95000000, "ARS")


def test_zonaprop():
    ps = FUENTES["zonaprop"].parse_listado(leer("zonaprop"))
    assert len(ps) == 2
    p = ps[0]
    assert (p.id, p.precio, p.moneda, p.m2, p.ambientes, p.expensas) == ("51234567", 128000, "USD", 68, 3, 95000)
    assert p.url.startswith("https://www.zonaprop.com.ar/propiedades/")


def test_argenprop():
    ps = FUENTES["argenprop"].parse_listado(leer("argenprop"))
    assert len(ps) == 2
    assert (ps[0].precio, ps[0].m2, ps[0].ambientes, ps[0].expensas) == (99500, 45, 2, 70000)
    assert detectar_apto_credito(ps[0].texto) is False
    assert ps[1].id == "15559999"


def test_mercadolibre():
    (p,) = FUENTES["mercadolibre"].parse_listado(leer("mercadolibre"))
    assert (p.id, p.precio, p.moneda, p.m2, p.ambientes) == ("MLA1500000001", 115000, "USD", 52, 2)
    assert detectar_apto_credito(p.titulo)


def test_urls():
    cfg = {"busqueda": {"operacion": "venta", "tipos": ["departamento"], "zonas": ["palermo",
           {"nombre": "vicente-lopez", "mercadolibre": "bs-as-gba-norte/vicente-lopez"}],
           "moneda": "USD", "precio_min": 60000, "precio_max": 150000, "solo_apto_credito": True}}
    z = FUENTES["zonaprop"].busquedas(cfg)
    assert z[0].url_pagina(1) == "https://www.zonaprop.com.ar/departamentos-venta-palermo-apto-credito-60000-150000-dolar.html"
    assert z[0].url_pagina(2).endswith("-dolar-pagina-2.html")
    m = FUENTES["mercadolibre"].busquedas(cfg)
    assert m[1].url_pagina(2) == ("https://inmuebles.mercadolibre.com.ar/departamentos/venta/bs-as-gba-norte/vicente-lopez/"
                                  "apto-credito_Desde_49_PriceRange_60000USD-150000USD_NoIndex_True")
    a = FUENTES["argenprop"].busquedas(cfg)
    assert a[0].url_pagina(3) == "https://www.argenprop.com/departamentos/venta/palermo/dolares-60000-150000?pagina-3"
