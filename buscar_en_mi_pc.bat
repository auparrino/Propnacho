@echo off
REM Doble click para correr la busqueda en tu PC (Windows). Requiere Python 3.10+ (python.org, tildar "Add to PATH").
cd /d "%~dp0"
if not exist .venv (
  python -m venv .venv
  call .venv\Scripts\activate.bat
  pip install -r requirements.txt
  python -m playwright install chromium
) else (
  call .venv\Scripts\activate.bat
)
python -m scraper
start "" "resultados\index.html"
pause
