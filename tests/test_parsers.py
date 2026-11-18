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


def test_argenprop_casos_reales():
    """Tarjetas reales de Argenprop (recorte del 2026-11-18) con casos que salían mal."""
    ps = {p.id: p for p in FUENTES["argenprop"].parse_listado(leer("argenprop_real"))}
    assert len(ps) == 5
    # "40 m² cubie. 8 m² Semicubierta": antes tomaba 8 m²
    p = ps["20852081"]
    assert (p.precio, p.moneda, p.m2, p.ambientes, p.expensas) == (123000, "USD", 48, 2, 196000)
    assert detectar_apto_credito(p.titulo + " " + p.texto) is True
    # emprendimiento "departamentos 1, 2 y 3 ambientes": es un monoambiente, no 3 amb
    assert (ps["19866143"].ambientes, ps["19866143"].m2) == (1, 30)
    # "Monoam." en las features; dice "No apto crédito" en la descripción
    p = ps["19798780"]
    assert (p.ambientes, p.m2, p.precio) == (1, 47, 69000)
    assert detectar_apto_credito(p.texto) is False
    # sin m² publicados: queda None (no se descarta)
    assert (ps["20785627"].ambientes, ps["20785627"].m2) == (1, None)
    # sin expensas publicadas
    assert (ps["18890955"].ambientes, ps["18890955"].m2, ps["18890955"].expensas) == (2, 42, None)
    assert all(p.imagen.startswith("https://") and p.direccion for p in ps.values())


def test_features_texto():
    from scraper.common import Propiedad, parse_features

    def feats(t):
        p = Propiedad("x", "1", "u")
        parse_features(t, p)
        return p.ambientes, p.m2

    assert feats("68 m² tot. 60 m² cub. 3 amb.") == (3, 68)
    assert feats("45 m² cub. 10 m² descub.") == (None, 45)
    assert feats("Gorriti 4500 - 3 amb") == (3, None)
    assert feats("unidades de 2 o 3 ambientes") == (None, None)
    assert feats("Monoam.") == (1, None)
