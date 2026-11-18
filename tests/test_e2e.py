import os
from pathlib import Path

import scraper.__main__ as m
from scraper import filtros
from scraper.fetch import Fetcher

FIX = Path(__file__).parent / "fixtures"


def test_corrida_completa(tmp_path, monkeypatch):
    def fake_get(self, url, dominio=""):
        if "pagina" in url or "_Desde_" in url:
            return ""
        if "15559999" in url:
            return "<html><body>Departamento... Apto crédito: Sí</body></html>"
        for n in ("zonaprop", "argenprop", "mercadolibre"):
            if n in url and ("/propiedades/" not in url):
                return (FIX / f"{n}.html").read_text(encoding="utf-8")
        return "<html>nada</html>"

    monkeypatch.setattr(Fetcher, "get", fake_get)
    monkeypatch.setattr(filtros, "cotizacion_dolar", lambda v: 1400.0)
    monkeypatch.setattr(m, "cotizacion_dolar", lambda v: 1400.0)
    cfg = Path("config.yml").resolve()
    monkeypatch.chdir(tmp_path)
    assert m.main(["--config", str(cfg), "--sin-navegador"]) == 0
    md = (tmp_path / "resultados" / "README.md").read_text()
    html = (tmp_path / "resultados" / "index.html").read_text()
    assert "Xeneizes" in html and "MLA1500000001" in html
    csv = (tmp_path / "resultados" / "propiedades.csv").read_text(encoding="utf-8-sig")
    print(md)
    assert "51234567" in csv          # zonaprop apto (filtro portal)
    assert "51230000" not in csv      # zonaprop precio alto
    assert "15551234" not in csv      # argenprop NO apto
    assert "15559999" in csv          # argenprop apto verificado en ficha
    assert "MLA1500000001" in csv
    # segunda corrida: nada nuevo
    assert m.main(["--config", str(cfg), "--sin-navegador"]) == 0
    assert "**0 nuevas**" in (tmp_path / "resultados" / "README.md").read_text()
