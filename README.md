# 🏠 Propnacho — Buscador de propiedades **apto crédito**

Busca en **Zonaprop**, **Argenprop** y **MercadoLibre** las propiedades que cumplen tus
filtros y que son **apto crédito hipotecario**. Corre solo en GitHub (gratis), dos veces
por día, y te deja una tabla con los resultados marcando las **🆕 nuevas**.
Si querés, también te avisa por **Telegram**.

💙💛 **El resultado es una página web azul y oro**: tarjetas con foto, precio,
US$/m², expensas, marca de 🆕 nuevas y ⬇ bajas de precio, filtros (portal, ambientes, precio,
búsqueda por calle), orden y ⭐ para marcar las que te gustan. Anda perfecto en el celular.

Se ve en **`https://TU-USUARIO.github.io/NOMBRE-DEL-REPO/`** (ver paso 6). También queda una
tabla rápida en [`resultados/README.md`](resultados/README.md) y la planilla
[`resultados/propiedades.csv`](resultados/propiedades.csv) por si la querés en Excel.

---

## 🚀 Puesta en marcha (5 minutos, una sola vez)

1. **Creá una cuenta en [GitHub](https://github.com/signup)** si no tenés (es gratis).
2. En esta página apretá el botón verde **`Use this template` → `Create a new repository`**.
   - Ponele un nombre (ej. `mi-casa`), elegí **Public** y **Create repository**.
     (Public hace falta para tener la página web gratis. Lo único que se ve es tu búsqueda y
     avisos públicos de los portales. Si preferís Private, el reporte te llega igual por
     Telegram o lo descargás desde Actions, ver más abajo.)
   - (Si no ves ese botón, usá **Fork** arriba a la derecha.)
3. En tu repo nuevo, andá a la pestaña **Actions**. Si aparece un botón verde
   *"I understand my workflows, go ahead and enable them"*, apretalo.
4. **Configurá tu búsqueda:** abrí el archivo **`config.yml`**, tocá el lápiz ✏️ (*Edit*),
   cambiá lo que quieras (barrios, precio, ambientes, m²…) y apretá **`Commit changes`**.
   Todo está explicado adentro del archivo.
5. Al guardar el config arranca una búsqueda sola. Tarda entre 5 y 20 minutos.
   La podés seguir en **Actions → Buscar propiedades**.
6. **Activá la página web (una sola vez):** **Settings → Pages → Build and deployment →
   Source: "GitHub Actions"**. Desde la próxima corrida tu reporte queda en
   **`https://TU-USUARIO.github.io/NOMBRE-DEL-REPO/`**. Guardalo en favoritos o agregalo a la
   pantalla de inicio del celular.

Desde ahí en adelante corre **todos los días a las 8:00 y a las 19:00**. Para correrla en el
momento: **Actions → Buscar propiedades → Run workflow → Run workflow**.

---

## ⚙️ Qué se puede configurar (`config.yml`)

| Parámetro | Ejemplo | Para qué |
|---|---|---|
| `operacion` | `venta` | venta o alquiler |
| `tipos` | `departamento`, `ph`, `casa` | tipo de propiedad |
| `zonas` | `palermo`, `belgrano`, `capital-federal` | barrios / localidades |
| `moneda`, `precio_min`, `precio_max` | `USD`, `60000`, `150000` | rango de precio |
| `ambientes_min` / `ambientes_max` | `2` / `4` | cantidad de ambientes |
| `m2_min` / `m2_max` | `40` / `0` | superficie (0 = sin límite) |
| `expensas_max` | `150000` | expensas máximas en pesos |
| `solo_apto_credito` | `true` | sólo apto crédito |
| `palabras_excluidas` | `reservado`, `en pozo` | descarta avisos con esas palabras |
| `fuentes` | `zonaprop: true` … | qué portales usar |
| `urls_extra` | (URL copiada del portal) | para usar filtros que no están acá |

**¿Cómo sabe si es apto crédito?**
- Zonaprop: usa el filtro "Apto crédito" del propio portal.
- Argenprop y MercadoLibre: busca "apto crédito / apto banco" en el aviso; si el listado no lo
  dice, entra a la ficha del aviso y lo chequea (descarta los que dicen "no apto crédito").

> Si un aviso no publica un dato (por ej. los m²), **no se descarta**: preferimos que veas de más.

---

## 📲 Avisos por Telegram (opcional)

1. En Telegram hablale a **[@BotFather](https://t.me/BotFather)** → `/newbot` → seguí los pasos.
   Te da un **token** (algo como `123456:ABC-xyz…`).
2. Abrí el chat con tu bot nuevo y mandale cualquier mensaje (ej. `/start`).
3. Hablale a **[@userinfobot](https://t.me/userinfobot)**: te dice tu **Id** (un número).
4. En tu repo de GitHub: **Settings → Secrets and variables → Actions → New repository secret**
   y creá dos:
   - `TELEGRAM_TOKEN` = el token del paso 1
   - `TELEGRAM_CHAT_ID` = el número del paso 3
5. En `config.yml` poné `telegram: true`.

Te va a llegar un mensaje con cada propiedad nueva que aparezca, el link a la página y el
reporte como archivo HTML (lo tocás y se abre en el navegador del celular).

### Otra forma de ver el reporte (repo privado, sin Telegram)
**Actions → la última corrida → Artifacts → `reporte`** → se baja un zip con
`index.html`. Lo abrís con doble click.

---

## 🛠️ Si algo no anda

- **Una corrida salió en rojo ❌ / un portal dice "⚠️ bloqueado":** los portales a veces
  bloquean a los servidores de GitHub. Se reintenta solo en la próxima corrida. Si un portal
  falla siempre, podés desactivarlo en `fuentes:` o correrlo en tu PC (ver abajo).
- **Un portal da 0 resultados siempre:** puede que haya cambiado su página o que el nombre del
  barrio no coincida. Probá buscar en la web del portal, copiá la URL y pegala en
  `urls_extra`. En cada corrida con problemas se guardan las páginas descargadas en
  *Actions → (la corrida) → Artifacts → debug*.
- **Zonas fuera de CABA en MercadoLibre:** usá el formato largo con la región, por ejemplo:
  ```yaml
  zonas:
    - nombre: vicente-lopez
      mercadolibre: bs-as-gba-norte/vicente-lopez
  ```
  (la parte de MercadoLibre es la que aparece en la URL cuando buscás en su web).
- **Cambiar horarios:** en `.github/workflows/buscar.yml`, las líneas `cron` (hora UTC = Argentina + 3).
- GitHub da 2.000 minutos/mes gratis en repos privados; cada corrida usa ~10–20, sobra.

### Correrlo en tu PC (Windows)
1. Instalá [Python](https://www.python.org/downloads/) (tildá **"Add Python to PATH"**).
2. Descargá el repo (**Code → Download ZIP**) y descomprimilo.
3. Doble click en **`buscar_en_mi_pc.bat`**. La primera vez instala lo necesario.
   Al terminar abre el reporte en el navegador.

En Mac/Linux: `pip install -r requirements.txt && python -m playwright install chromium && python -m scraper`

---
*Uso personal. Respetá los términos de uso de cada portal; el programa espera unos segundos
entre pedidos para no sobrecargarlos.*
