# Dashboard de Desvíos de Frío

Dashboard HTML autocontenido (sin servidor) para revisar desvíos FCST vs Solicitado vs Sell In/Out, quiebres, stock en riesgo de liquidación y precio promedio, con filtros en cascada (Categoría/Marca/SubCategoría/SKU/Cadena).

## Archivos

- **`dashboard_frio.html`** — el dashboard final, ya generado. Ábrelo directo en el navegador, no necesita nada más.
- **`dashboard_frio_template.html`** — el código fuente real (HTML/CSS/JS). **Edita este archivo**, no `dashboard_frio.html` directamente.
- **`dashboard_data.json`** — los datos ya procesados (semanas, SKUs, cadenas, stock, precios, liquidación) que se inyectan en el template.
- **`inject_frio.py`** — toma `dashboard_data.json` + `dashboard_frio_template.html`, comprime el JSON (gzip+base64) y genera `dashboard_frio.html`. Se corre después de cualquier cambio en el template o en los datos.
- **`build_data_frio.py`** — arma `dashboard_data.json` desde los Excel originales (pandas). Solo hace falta correrlo si vas a **actualizar los datos** con archivos nuevos.
- **`build_excel_frio.py`** — genera el archivo `Desvios_de_Frio.xlsx` (reporte Excel equivalente) desde los mismos Excel originales.
- **`Desvios_de_Frio.xlsx`** — el reporte Excel ya generado.
- **`tests/`** — scripts de Playwright para verificar que el dashboard funciona (sin romper nada) después de un cambio.

## Flujo de trabajo típico

**Cambiar algo visual o de lógica del dashboard** (sin tocar datos):
1. Edita `dashboard_frio_template.html`.
2. `python3 inject_frio.py` → regenera `dashboard_frio.html`.
3. Abre `dashboard_frio.html` en el navegador para revisar.

**Actualizar con datos nuevos** (nuevos Excel de desvíos/stock/precio):
1. Sube los Excel nuevos a esta carpeta.
2. En `build_data_frio.py`, actualiza las rutas `SRC`, `STOCK_SRC`, `LIQ_SRC` (líneas 3, 4 y 213) para que apunten a los archivos nuevos, y `snapshot_fecha` (línea 205) con la fecha del snapshot de stock.
3. En `build_excel_frio.py`, actualiza las mismas rutas.
4. `python3 build_data_frio.py` → regenera `dashboard_data.json`.
5. `python3 build_excel_frio.py` → regenera `Desvios_de_Frio.xlsx`.
6. `python3 inject_frio.py` → regenera `dashboard_frio.html` con los datos nuevos.

> Nota: las rutas `SRC`/`STOCK_SRC`/`LIQ_SRC` actuales apuntan a archivos temporales de la sesión anterior (`/root/.claude/uploads/...`) que ya no existen. Reemplázalas por la ruta de tus Excel nuevos antes de correr `build_data_frio.py`.

## Fuentes de datos esperadas

- **Base de desvíos** (`Hoja2`): FCST, Solicitado, Sell In, Sell Out, Quebrados, Bloqueados por SKU/semana/cadena.
- **Informe de Stock** (`DETALLE WMS`): snapshot de stock por SKU para el panel "Stock en Riesgo de Liquidación".
- **Precio Promedio SO** (`Server_CH237-213`): columna `Tipo de Venta` (`-` = Sell Out + precio; `VENTA NORMAL`/`VENTA INTERMEDIA`/`VENTA LIQUIDACION` = Sell In por tipo), usada para el precio promedio ponderado y el historial de venta en liquidación.

## Tests

```bash
npm install   # instala playwright-core
node tests/test_panelorder.js
node tests/test_price.js
node tests/test_liqhist.js
node tests/test_errorboxes.js
node tests/test_cadenareview.js
node tests/test_singleweek.js
```

Todos deben imprimir `errors: []`.
