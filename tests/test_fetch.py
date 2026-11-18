import pytest

from scraper import fetch
from scraper.fetch import Bloqueado, Fetcher


def test_chromium_que_no_arranca_no_rompe_lo_siguiente(monkeypatch):
    """Si Chromium no abre, se informa 'bloqueado' siempre (antes la 2da vez explotaba
    con 'Sync API inside the asyncio loop' porque Playwright quedaba a medio arrancar)."""
    paradas = []

    class PW:
        class chromium:
            @staticmethod
            def launch(**kw):
                raise RuntimeError("Executable doesn't exist\nmás detalle")

        def stop(self):
            paradas.append(1)

    class Arranque:
        def start(self):
            return PW()

    import playwright.sync_api as sa

    monkeypatch.setattr(sa, "sync_playwright", lambda: Arranque())
    f = Fetcher(espera=0)
    monkeypatch.setattr(f, "_http", lambda url: (_ for _ in ()).throw(Bloqueado("HTTP 403")))
    with pytest.raises(Bloqueado, match="Chromium"):
        f.get("https://a.example/1", "a.example")
    with pytest.raises(Bloqueado):
        f.get("https://a.example/2", "a.example")
    with pytest.raises(Bloqueado):
        f.get("https://b.example/1", "b.example")
    assert paradas == [1]
