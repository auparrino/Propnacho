"""Descarga de páginas con imitación de navegador y fallback a Chromium (Playwright)."""
from __future__ import annotations

import logging
import random
import re
import time
from pathlib import Path

log = logging.getLogger(__name__)

DEBUG_DIR = Path("debug")

_BLOQUEO = re.compile(
    r"Just a moment|cf-chl|challenge-platform|Attention Required|captcha|"
    r"account-verification|Access denied|px-captcha|are you a robot",
    re.I,
)

HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-AR,es;q=0.9,en;q=0.6",
}


class Bloqueado(Exception):
    pass


class Fetcher:
    def __init__(self, espera: float = 3.0, usar_navegador: bool = True):
        self.espera = espera
        self.usar_navegador = usar_navegador
        self._session = None
        self._pw = None
        self._browser = None
        self._ctx = None
        self._ultimo = 0.0
        self._forzar_navegador: set[str] = set()
        self.pedidos = 0

    # -- HTTP "rápido" -------------------------------------------------
    def _sesion(self):
        if self._session is None:
            try:
                from curl_cffi import requests as creq

                self._session = creq.Session(impersonate="chrome", headers=HEADERS, timeout=40)
            except ImportError:  # pragma: no cover
                import requests

                self._session = requests.Session()
                self._session.headers.update(HEADERS)
                self._session.headers["User-Agent"] = (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/131.0 Safari/537.36"
                )
        return self._session

    def _pausa(self):
        falta = self.espera - (time.time() - self._ultimo)
        if falta > 0:
            time.sleep(falta + random.uniform(0, self.espera / 2))
        self._ultimo = time.time()

    def _http(self, url: str) -> str:
        r = self._sesion().get(url, allow_redirects=True)
        if r.status_code == 404:
            return ""
        txt = r.text or ""
        if r.status_code in (403, 429, 503) or (len(txt) < 60000 and _BLOQUEO.search(txt)):
            raise Bloqueado(f"HTTP {r.status_code}")
        r.raise_for_status()
        return txt

    # -- Navegador real -----------------------------------------------
    def _navegador(self, url: str) -> str:
        if self._ctx is None:
            from playwright.sync_api import sync_playwright

            self._pw = sync_playwright().start()
            try:
                self._browser = self._pw.chromium.launch(
                    headless=True, args=["--disable-blink-features=AutomationControlled"]
                )
            except Exception as e:
                # Si no arranca Chromium hay que soltar Playwright; si no, el próximo
                # intento falla con "Sync API inside the asyncio loop".
                self._pw.stop()
                self._pw = None
                self.usar_navegador = False
                raise Bloqueado(f"no pude abrir Chromium: {str(e).splitlines()[0]}") from e
            self._ctx = self._browser.new_context(
                locale="es-AR",
                viewport={"width": 1366, "height": 900},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
                ),
            )
            self._ctx.add_init_script(
                "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"
            )
        page = self._ctx.new_page()
        try:
            resp = page.goto(url, wait_until="domcontentloaded", timeout=60000)
            for _ in range(6):  # esperar a que pase un challenge tipo Cloudflare
                page.wait_for_timeout(2500)
                html = page.content()
                if not _BLOQUEO.search(html[:60000]):
                    break
            else:
                raise Bloqueado("navegador: challenge no resuelto")
            if resp is not None and resp.status == 404:
                return ""
            # scroll para que carguen tarjetas perezosas
            page.mouse.wheel(0, 4000)
            page.wait_for_timeout(800)
            return page.content()
        finally:
            page.close()

    # -- API pública ---------------------------------------------------
    def get(self, url: str, dominio: str = "") -> str:
        self._pausa()
        self.pedidos += 1
        if dominio not in self._forzar_navegador:
            for intento in range(2):
                try:
                    return self._http(url)
                except Bloqueado as e:
                    log.info("  bloqueado (%s) en %s", e, url)
                    break
                except Exception as e:  # red, timeout
                    log.info("  error %s en %s (intento %d)", e, url, intento + 1)
                    time.sleep(5)
            if not self.usar_navegador:
                raise Bloqueado(url)
            log.info("  -> uso navegador real para %s", dominio or url)
            self._forzar_navegador.add(dominio)
        if not self.usar_navegador:
            raise Bloqueado(f"{dominio or url} (sin navegador)")
        try:
            return self._navegador(url)
        except ImportError:
            raise Bloqueado("Playwright no instalado")

    def guardar_debug(self, nombre: str, html: str) -> None:
        DEBUG_DIR.mkdir(exist_ok=True)
        (DEBUG_DIR / f"{nombre}.html").write_text(html or "", encoding="utf-8")

    def cerrar(self):
        try:
            if self._browser:
                self._browser.close()
            if self._pw:
                self._pw.stop()
        except Exception:
            pass
